#!/usr/bin/env python3
"""F-01：CODE_WIKI 机械标记同步工具。

从代码中生成三类「数字/签名」机械标记，写入 CODE_WIKI.md 的 HTML 注释标记内，
防止文档与代码漂移：

    lines:<module>        §4 各模块标题的（~N 行）——非空行计数
    tests:<test_file>     §7 测试表用例数——解析 ``pytest --collect-only -q``
    sig:<module>:<symbol> §4 方法表签名——AST 提取函数/方法签名

标记语法：``<!--AUTO:<kind>:<key>-->内容<!--/AUTO-->``（HTML 注释，渲染不可见）。
工具只维护标记内的机械文本，绝不生成叙述性说明（F-01 规模悖论边界）。

用法::

    python scripts/doc_sync.py              # 更新：就地刷新所有现有标记内容
    python scripts/doc_sync.py --check      # 校验：有漂移则 exit 1（pre-commit 钩子用）
    python scripts/doc_sync.py --check --verbose

--check 额外做结构完整性校验：
  - tests：每个 pytest 收集的测试文件必须有标记；每个标记必须对应真实收集文件
  - lines：每个 §4 模块标题必须有标记；每个标记必须对应一个 §4 标题
  - sig：每个标记引用的符号必须存在于模块（删除/改名会被拦截）
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from pathlib import Path

__all__ = [
    "MARKER_RE",
    "collect_test_counts",
    "compute_content",
    "count_nonblank_lines",
    "main",
    "render_signature",
    "resolve_signature",
    "scan_markers",
]

# ── 常量 ──────────────────────────────────────────────────

MARKER_RE = re.compile(
    r"<!--AUTO:(?P<kind>lines|tests|sig):(?P<key>[^>]+)-->"
    r"(?P<content>.*?)"
    r"<!--/AUTO-->",
    re.DOTALL,
)

# §4 模块标题，如 `### 4.1 `main.py` — 程序入口（~92 行）`
HEADING_RE = re.compile(
    r"^### 4\.\d+ .*?`([A-Za-z0-9_./-]+\.py)`", re.MULTILINE
)

# pytest --collect-only -q 输出的测试项：`tests/test_x.py::nodeid`
TEST_ITEM_RE = re.compile(r"^([A-Za-z0-9_./\\-]+\.py)::")


def project_root() -> Path:
    """项目根目录 = 本脚本父目录的父目录（scripts/ 的上一级）。"""
    return Path(__file__).resolve().parent.parent


# ── 数值提取 ──────────────────────────────────────────────


def collect_test_counts(root: Path) -> dict[str, int]:
    """运行 ``pytest --collect-only -q``，返回 {测试文件相对路径: 用例数}。

    以 pytest 实际收集为准（含参数化展开），与开发者跑 ``pytest`` 的口径一致；
    文件用正斜杠相对路径作 key，跨平台一致。
    """
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "pytest --collect-only 失败（rc=%d）:\n%s"
            % (proc.returncode, proc.stderr[-2000:])
        )
    counts: dict[str, int] = {}
    for line in proc.stdout.splitlines():
        m = TEST_ITEM_RE.match(line)
        if m:
            path = m.group(1).replace("\\", "/")
            counts[path] = counts.get(path, 0) + 1
    return counts


def count_nonblank_lines(path: Path) -> int:
    """统计非空行数（§4 标题的（~N 行）口径）。"""
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


# ── 签名提取（AST）────────────────────────────────────────


def _default_text(node: ast.expr | None) -> str | None:
    """把参数默认值渲染为短文本。

    只展示「字面量 / 简单符号」：数字、字符串、None/True/False、一元正负、
    Name（如 ``DATA_FILE``）、Attribute（如 ``Qt.PenStyle.SolidLine``）。
    Call 等复杂表达式省略默认值（避免方法表噪音）。
    """
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        v = node.value
        if v is None:
            return "None"
        if isinstance(v, bool):
            return "True" if v else "False"
        if isinstance(v, str):
            return repr(v)
        if isinstance(v, (int, float)):
            return repr(v)
        return None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        inner = node.operand
        if isinstance(inner, ast.Constant) and isinstance(inner.value, (int, float)):
            sign = "-" if isinstance(node.op, ast.USub) else ""
            return f"{sign}{inner.value!r}"
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return ast.unparse(node)
    return None


def render_signature(fn: ast.FunctionDef) -> str:
    """把函数 AST 渲染为 ``name(params)`` 签名文本（不含 self/cls，略复杂默认值）。

    示例::

        def save_today(self) -> None                          → save_today()
        def __init__(self, data_file: Path = DATA_FILE,
                     max_backups: int = 3) -> None             → __init__(data_file=DATA_FILE, max_backups=3)
        def format_compact(value, *, prefix="") -> str         → format_compact(value, *, prefix="")
    """
    a = fn.args
    posonly = list(a.posonlyargs)
    positional = list(a.args)
    all_pos = posonly + positional

    # 剥掉方法首参 self/cls（文档方法表约定不展示）
    if all_pos and all_pos[0].arg in ("self", "cls"):
        if posonly:
            posonly.pop(0)
        else:
            positional.pop(0)
        all_pos = posonly + positional

    defaults = list(a.defaults)
    offset = len(all_pos) - len(defaults)

    parts: list[str] = []
    for i, arg in enumerate(all_pos):
        txt = arg.arg
        if i >= offset:
            d = _default_text(defaults[i - offset])
            if d is not None:
                txt = f"{arg.arg}={d}"
        parts.append(txt)

    if posonly:
        # 位置参数段后补 "/" 分隔符
        parts.insert(len(posonly), "/")

    if a.vararg is not None:
        parts.append(f"*{a.vararg.arg}")
    elif a.kwonlyargs:
        parts.append("*")

    for i, arg in enumerate(a.kwonlyargs):
        txt = arg.arg
        d = _default_text(a.kw_defaults[i])
        if d is not None:
            txt = f"{arg.arg}={d}"
        parts.append(txt)

    if a.kwarg is not None:
        parts.append(f"**{a.kwarg.arg}")

    return f"{fn.name}({', '.join(parts)})"


def _is_property(fn: ast.FunctionDef) -> bool:
    return any(
        isinstance(d, ast.Name) and d.id in ("property", "cached_property")
        for d in fn.decorator_list
    )


def _render(fn: ast.FunctionDef) -> str:
    """按函数形态渲染：property 无括号，普通方法带签名。"""
    if _is_property(fn):
        return fn.name
    return render_signature(fn)


def resolve_signature(module: Path, symbol: str) -> str | None:
    """返回模块中符号的渲染签名；符号不存在返回 None。

    symbol 形如 ``main``（模块级函数）或 ``MainWindow.save_today``（类方法）。
    常量/枚举成员等非函数符号返回 None（会被判为 stale）。
    """
    try:
        tree = ast.parse(module.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None

    if "." not in symbol:
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == symbol:
                return _render(node)
        return None

    cls_name, _, meth = symbol.partition(".")
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == cls_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == meth:
                    return _render(item)
            return None
    return None


# ── 标记计算 ──────────────────────────────────────────────


def compute_content(
    kind: str, key: str, root: Path, test_counts: dict[str, int]
) -> str:
    """计算某标记当前的机械文本（不含 HTML 注释壳）。"""
    if kind == "lines":
        return f"~{count_nonblank_lines(root / key)} 行"
    if kind == "tests":
        count = test_counts.get(key)
        if count is None:
            raise KeyError(f"pytest 未收集该测试文件: {key}")
        return str(count)
    if kind == "sig":
        module, _, symbol = key.partition(":")
        sig = resolve_signature(root / module, symbol)
        if sig is None:
            raise KeyError(f"符号不存在: {key}")
        return f"`{sig}`"
    raise ValueError(f"未知标记类型: {kind!r}")


def scan_markers(text: str) -> list[tuple[str, str, str, int, int]]:
    """扫描文档中全部标记，返回 (kind, key, content, start, end)。"""
    return [
        (m.group("kind"), m.group("key"), m.group("content"), m.start(), m.end())
        for m in MARKER_RE.finditer(text)
    ]


def _sig_content_ok(content: str, symbol: str, rendered: str) -> bool:
    """判断 sig 标记内容是否可接受。

    - ``name(params)``（含反引号）→ 必须等于 AST 渲染签名（严格校验）；
    - 仅 ``name``（如 §4.7「方法|参数|返回」表的名称列）→ 只校验存在性。
    property 的渲染本就是 ``name``，两种写法等价。
    """
    stripped = content.strip().strip("`")
    if stripped == rendered:
        return True
    if stripped == symbol.split(".")[-1]:
        return True  # 名称列：仅存在性校验
    return False


# ── 校验 / 更新 ───────────────────────────────────────────


def _gather_issues(
    text: str, root: Path, test_counts: dict[str, int]
) -> list[str]:
    """汇总全部漂移项（内容不一致 + 结构覆盖 + 符号 stale）。"""
    issues: list[str] = []
    markers = scan_markers(text)

    for kind, key, content, _, _ in markers:
        if kind == "sig":
            module, _, symbol = key.partition(":")
            rendered = resolve_signature(root / module, symbol)
            if rendered is None:
                issues.append(f"[sig] 符号不存在（删除/改名？）: {key}")
            elif not _sig_content_ok(content, symbol, rendered):
                issues.append(
                    f"[sig] 签名不一致: {key}  文档={content!r}  实际=`{rendered}`"
                )
            continue
        try:
            expected = compute_content(kind, key, root, test_counts)
        except KeyError as e:
            issues.append(f"[{kind}] {key}: {e}")
            continue
        if content != expected:
            issues.append(
                f"[{kind}] {key}: 文档={content!r} 实际={expected!r}"
            )

    # tests：双向覆盖（新测试文件漏标 / 标记指向已删文件）
    tests_marked = {key for kind, key, *_ in markers if kind == "tests"}
    for path in sorted(test_counts):
        if path not in tests_marked:
            issues.append(
                f"[tests] 缺少标记: {path}（pytest 收集 {test_counts[path]} 个用例，文档无 tests: 标记）"
            )
    for key in sorted(tests_marked):
        if key not in test_counts:
            issues.append(f"[tests] 标记指向未收集的测试文件: {key}")

    # lines：双向覆盖（新 §4 标题漏标 / 标记无对应标题）
    lines_marked = {key for kind, key, *_ in markers if kind == "lines"}
    headings = {m.group(1) for m in HEADING_RE.finditer(text)}
    for path in sorted(headings):
        if path not in lines_marked:
            issues.append(f"[lines] §4 标题缺少行数标记: {path}")
    for key in sorted(lines_marked):
        if key not in headings:
            issues.append(f"[lines] 行数标记无对应 §4 标题: {key}")

    return issues


def _sig_update_text(key: str, content: str, root: Path) -> str | None:
    """返回 sig 标记的新内容（保持原样式）；符号不存在返回 None（无法修复）。"""
    module, _, symbol = key.partition(":")
    rendered = resolve_signature(root / module, symbol)
    if rendered is None:
        return None
    if "(" in content.strip().strip("`"):
        return f"`{rendered}`"
    return f"`{symbol.split('.')[-1]}`"


def run_update(
    doc: Path, root: Path, verbose: bool
) -> tuple[int, list[str]]:
    """就地刷新所有现有标记内容；返回 (变更数, 提示行)。"""
    text = doc.read_text(encoding="utf-8")
    test_counts = collect_test_counts(root)
    notes: list[str] = []
    changed = 0

    def repl(m: re.Match) -> str:
        nonlocal changed
        kind, key, content = m.group("kind"), m.group("key"), m.group("content")
        if kind == "sig":
            new_text = _sig_update_text(key, content, root)
            if new_text is None:
                notes.append(f"  ⚠ 跳过（符号不存在，无法刷新）: {key}")
                return m.group(0)
        else:
            try:
                new_text = compute_content(kind, key, root, test_counts)
            except KeyError as e:
                notes.append(f"  ⚠ 跳过（{e}）: {kind}:{key}")
                return m.group(0)
        if new_text == content:
            return m.group(0)
        changed += 1
        if verbose:
            notes.append(f"  {kind}:{key}: {content!r} → {new_text!r}")
        return m.group(0).replace(content, new_text, 1)

    new_text = MARKER_RE.sub(repl, text)
    if changed:
        doc.write_text(new_text, encoding="utf-8")

    # 更新后仍报告剩余结构缺口（供开发者手动补行/补标记）
    remaining = _gather_issues(new_text, root, test_counts)
    return changed, notes + [f"  {s}" for s in remaining]


def run_check(
    doc: Path, root: Path, verbose: bool
) -> tuple[bool, list[str]]:
    """校验全部标记与结构；返回 (是否通过, 输出行)。"""
    text = doc.read_text(encoding="utf-8")
    try:
        test_counts = collect_test_counts(root)
    except RuntimeError as e:
        return False, [str(e)]
    issues = _gather_issues(text, root, test_counts)
    if verbose or issues:
        n = len(scan_markers(text))
        header = f"doc_sync --check: CODE_WIKI.md（{n} 个标记）"
        if not issues:
            return True, [header + " 同步 ✅"]
        return False, [header + " 漂移 ❌"] + [f"  {s}" for s in issues]
    return True, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="校验模式：存在漂移则 exit 1（pre-commit 钩子用）；默认是更新模式",
    )
    parser.add_argument(
        "--doc",
        type=Path,
        default=None,
        help="目标文档路径（默认 <root>/CODE_WIKI.md）",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="项目根目录（默认由脚本位置推导）",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出每个标记的变更/校验明细",
    )
    args = parser.parse_args(argv)

    root = args.root or project_root()
    doc = args.doc or (root / "CODE_WIKI.md")

    if not doc.exists():
        print(f"doc_sync: 文档不存在: {doc}", file=sys.stderr)
        return 2

    if args.check:
        ok, lines = run_check(doc, root, args.verbose)
        print("\n".join(lines))
        return 0 if ok else 1

    changed, lines = run_update(doc, root, args.verbose)
    print("\n".join(lines))
    print(f"doc_sync --update: {changed} 个标记已刷新（现有标记就地更新，不新增）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

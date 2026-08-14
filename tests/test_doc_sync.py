"""
F-01 冒烟测试：`scripts/doc_sync.py --check` 通过即 CODE_WIKI 基线同步。

只加 1 个冒烟 + 1 个文件级校验纯函数测试（F-01 规模悖论边界）：工具脚本不堆
测试数量，用 --check 校验整条同步链路（pytest 收集 → AST 提取 → 文档比对）
跑通即可；文件级引用校验（files）是新增行为，用 tmp_path 构造失败路径单测。
tests_total 专项断言并入同一用例：头部横幅/属性表/依赖表的测试总数必须等于
pytest 收集总和——新增独立测试函数会改变收集总数，反噬本文件维护的基线。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

__all__ = ["test_doc_sync_check_passes", "test_file_ref_validation"]

ROOT = Path(__file__).resolve().parent.parent


def _load_doc_sync():
    """以模块方式加载 scripts/doc_sync.py（scripts/ 无 __init__.py 包）。"""
    spec = importlib.util.spec_from_file_location(
        "doc_sync", ROOT / "scripts" / "doc_sync.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_doc_sync_check_passes() -> None:
    """doc_sync --check 必须通过：CODE_WIKI 机械标记与代码/测试数同步。"""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "doc_sync.py"), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (
        "CODE_WIKI 机械标记漂移（测试数/模块行数/方法签名不同步）。"
        f"\n请运行: python scripts/doc_sync.py\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )

    # tests_total 专项回归（2026-08-08 漂移现场：头部横幅/属性表/依赖表
    # 手工叙述测试数曾写 300/292 而实际 293，不受 tests: 逐文件标记保护；
    # --check 已比对 tests_total 内容，此处再显式断言文档标记 = 收集总数）。
    doc_sync = _load_doc_sync()
    counts = doc_sync.collect_test_counts(ROOT)
    total = str(sum(counts.values()))
    text = (ROOT / "CODE_WIKI.md").read_text(encoding="utf-8")
    totals = {
        content
        for kind, key, content, _, _ in doc_sync.scan_markers(text)
        if kind == "tests_total"
    }
    assert totals, "CODE_WIKI 缺少 tests_total 标记（头部横幅/属性表/依赖表测试数）"
    assert all(c == total for c in totals), (
        f"tests_total 标记与 pytest 收集总数不一致: 标记={sorted(totals)} 实际={total}"
        f"\n请运行: python scripts/doc_sync.py"
    )


def test_file_ref_validation(tmp_path) -> None:
    """文件级引用校验（files）：不存在引用报漂移、退役名单豁免、仓库未引用文件报漂移。"""
    doc_sync = _load_doc_sync()
    root = tmp_path
    (root / "main.py").write_text("x = 1\n", encoding="utf-8")
    (root / "app").mkdir()
    (root / "app" / "view.py").write_text("y = 2\n", encoding="utf-8")
    (root / "tests").mkdir()
    (root / "tests" / "test_x.py").write_text("def test_x():\n    pass\n", encoding="utf-8")

    # 文档引用了不存在的文件 → [files] 漂移（存在引用不报）
    issues = doc_sync._gather_issues("引用 `main.py`、`app/view.py`、`app/ghost.py`", root, {})
    assert any("[files]" in s and "ghost.py" in s for s in issues)
    assert not any("[files]" in s and ("main.py" in s or "view.py" in s) for s in issues)

    # 退役名单内的引用豁免
    retired = sorted(doc_sync._KNOWN_RETIRED)[0]
    issues = doc_sync._gather_issues(f"历史 `{retired}` 已退役", root, {})
    assert not any("[files] 文档引用不存在" in s for s in issues)

    # 仓库文件未出现在文档引用中 → [files] 漂移（main.py 已引用不报）
    issues = doc_sync._gather_issues("只有 `main.py`", root, {})
    assert any("[files]" in s and "app/view.py" in s for s in issues)
    assert any("[files]" in s and "tests/test_x.py" in s for s in issues)
    assert not any("[files]" in s and "main.py" in s for s in issues)

"""
C6 守卫测试：Registry 插件系统（app/registry.py）删除后全库零残留引用。

规则来源（工单 05 / C6）：
- app/registry.py（AppWidget / WidgetRegistry）已物理删除，禁止重建；
- app/__init__.py 不再导出 AppWidget / WidgetRegistry；
- 防回归：app/ 全部 .py + 仓库根顶层模块的 AST 中不得出现这两个标识符
  （Name / Attribute / 导入别名 / 类函数定义名 / 参数名等），且 `__all__`
  列表的字符串字面量条目也不得出现——这类名字在 __all__ 中以字符串形式
  存在，纯标识符 grep 会漏（工单 05 明示）。

不误报侧写（Falsify）：注释 / docstring 正文中的历史叙述（如
app/dashboard_page.py 的「从 WidgetRegistry 间接层改为直构」）不是标识符
引用，AST 精确匹配不会命中；其他含 "registry" 字样的模块名 / 变量
（小写，如 registry_* 或 `from app import registry`）不属于禁名，同样不命中。
"""

from __future__ import annotations

import ast
from pathlib import Path

__all__ = [
    "test_registry_module_deleted",
    "test_no_registry_identifiers_anywhere",
]

ROOT = Path(__file__).resolve().parent.parent

#: C6 已删除的 registry 插件系统禁名（标识符 + __all__ 字符串字面量双查）。
_FORBIDDEN_NAMES = ("WidgetRegistry", "AppWidget")


def _scanned_py_files() -> list[Path]:
    """返回守卫扫描的 .py 文件：app/ 全部递归 + 仓库根顶层模块。"""
    return sorted((ROOT / "app").rglob("*.py")) + sorted(ROOT.glob("*.py"))


def _identifier_hits(tree: ast.AST) -> list[str]:
    """AST 遍历收集禁名标识符出现位置（精确匹配，不扫注释/字符串正文）。"""
    hits: list[str] = []
    for node in ast.walk(tree):
        for field in ("id", "attr", "name", "arg"):
            value = getattr(node, field, None)
            if value in _FORBIDDEN_NAMES:
                hits.append(f"L{node.lineno}: {type(node).__name__}.{field}={value}")
    return hits


def _all_entries_hits(tree: ast.AST) -> list[str]:
    """收集 __all__ 列表中的禁名字符串字面量（纯标识符检查会漏）。"""
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple)):
            continue
        for elt in value.elts:
            if (
                isinstance(elt, ast.Constant)
                and isinstance(elt.value, str)
                and elt.value in _FORBIDDEN_NAMES
            ):
                hits.append(f"L{node.lineno}: __all__ 含 {elt.value}")
    return hits


def test_registry_module_deleted() -> None:
    """app/registry.py 必须保持删除状态（物理删除守卫）。"""
    assert not (ROOT / "app" / "registry.py").exists(), (
        "app/registry.py 复活——C6 已物理删除 registry 插件系统，禁止重建"
    )


def test_no_registry_identifiers_anywhere() -> None:
    """app/ + 顶层模块 AST 零 WidgetRegistry / AppWidget 标识符与 __all__ 条目。"""
    offenders: list[str] = []
    for path in _scanned_py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders += [f"{path.relative_to(ROOT)}: {h}" for h in _identifier_hits(tree)]
        offenders += [f"{path.relative_to(ROOT)}: {h}" for h in _all_entries_hits(tree)]
    assert not offenders, "registry 禁名残留：\n" + "\n".join(offenders)

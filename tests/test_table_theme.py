"""
C1 回归测试：表格主题色必须实时解析，不得在 import 时冻结。

背景：T-01 将业务层的颜色耦合剥离后，信号→颜色的映射字典被定义在
table_widget 模块顶层，import 期调用 get_color() 即锁定为 light 主题色板。
暗色模式下收益率列与盈亏标签因此渲染出浅色主题的绿/红/灰。

本文件用动态 Qt 断言 + AST 静态检查双重防复发：
- 动态：set_theme("dark") 后 draw()，断言单元格前景色 == dark 主题色；
- 静态：table_widget 模块顶层（非函数体）不得存在 get_color() 调用。
"""

from __future__ import annotations

import ast
import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app import theme as theme_mod
from calculator import DayRecord

__all__ = []


# ── fixtures（qapp 见 tests/conftest.py）──────────────────


@pytest.fixture
def theme_guard():
    """隔离模块级主题状态：测试前复位为 light，测试后恢复原值。"""
    saved = theme_mod._current_theme
    theme_mod.set_theme("light")
    yield
    theme_mod._current_theme = saved


# ── 工具 ──────────────────────────────────────────────────


def _make_table():
    """构造一个 1 行 1 列渲染用的 _DaySubTable。"""
    from app.table_widget import _DaySubTable

    table = _DaySubTable()
    table.resize(400, 300)
    return table


def _render_one_row(table, theme: str):
    """在指定主题下渲染一条「较前日上涨」的记录，返回收益率单元格前景色。"""
    from app.table_widget import COL_RATE

    theme_mod.set_theme(theme)
    table.draw(
        records=[("2026-07-30", DayRecord(cash=50.0, warehouse=200.0, date="2026-07-30"))],
        today="2026-07-30",
        prev_warehouse=100.0,  # 100 → 200，收益率 +100% → POSITIVE
    )
    item = table.item(0, COL_RATE)
    assert item is not None, "收益率单元格未被绘制"
    return item.foreground().color().name()


def _find_import_time_get_color(node) -> list[str]:
    """递归找出非函数体/方法体内的 get_color() 调用（import 期冻结风险）。

    函数体内的调用是运行时解析，允许；模块/类顶层的是 import 期执行，禁止。
    """
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return []
    findings: list[str] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "get_color"
        ):
            findings.append(f"L{child.lineno}")
        findings.extend(_find_import_time_get_color(child))
    return findings


# ── 动态回归：颜色随主题实时解析 ─────────────────────────


def test_rate_column_uses_live_theme_color(qapp, theme_guard):
    """收益率列前景色必须等于当前主题的 FG_POS，而非 import 期冻结的 light 色。"""
    table = _make_table()
    rendered = _render_one_row(table, "dark")
    expected = theme_mod.get_color("FG_POS")  # dark 主题下读取
    assert rendered.lower() == expected.lower(), (
        f"收益率列应为 dark 主题色 {expected}，实际渲染 {rendered}"
        "——颜色在 import 时被冻结为 light 色板"
    )


def test_rate_column_differs_across_themes(qapp, theme_guard):
    """同一渲染路径下，切换主题后颜色必须变化——证明没有冻结。"""
    table = _make_table()
    light_color = _render_one_row(table, "light")
    dark_color = _render_one_row(table, "dark")
    assert light_color != dark_color, (
        f"light/dark 两种主题渲染出相同颜色 {light_color}——颜色被冻结在单一主题"
    )


def test_diff_cell_zero_delta_has_no_plus_prefix(qapp, theme_guard):
    """较前日为零时显示 ¥0.00（无 + 前缀，D-01），而非 +¥0.00。"""
    from app.table_widget import COL_DIFF

    table = _make_table()
    theme_mod.set_theme("light")
    table.draw(
        records=[("2026-07-30", DayRecord(cash=50.0, warehouse=200.0, date="2026-07-30"))],
        today="2026-07-30",
        prev_warehouse=200.0,  # 前后仓库相等 → 差值 0
    )
    item = table.item(0, COL_DIFF)
    assert item is not None, "较前日单元格未被绘制"
    assert item.text() == "¥0.00"


# ── 静态检查：防 import 期冻结复发 ───────────────────────


def test_table_module_has_no_import_time_get_color(qapp):
    """table_widget 顶层（模块/类作用域）不得存在 get_color() 调用。

    这是 C1 的防复发检查：冻结 bug 的根因就是在 import 期执行 get_color()。
    """
    import inspect

    import app.table_widget as tw

    source = inspect.getsource(tw)
    findings = _find_import_time_get_color(ast.parse(source))
    assert findings == [], (
        f"table_widget 存在 import 期 get_color() 调用（颜色冻结风险）：{findings}"
    )

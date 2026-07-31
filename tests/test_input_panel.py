"""
C4 回归测试：InputPanel 成为 MainWindow 的真 seam。

C4 将 MainWindow 对输入面板的访问收敛到公开 API：
- save_today 改走 get_cash_value()/get_warehouse_value()（+ get_cash_raw()/get_warehouse_raw() 供错误提示）；
- 编辑状态单方归属 InputPanel（is_editing()/get_editing_date()），MainWindow 不再持有 _editing_date。

本文件动态断言 getter 语义、编辑状态归属、save_today 行为等价，
并用静态检查防止 seam 回归：hasattr 防 MainWindow._editing_date 复发，
AST 源码守卫防直取输入框 / parse_money_input（C9）。
"""

from __future__ import annotations

import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.input_panel import InputPanel
from calculator import DayRecord
from data_store import DataStore

__all__ = []


# ── fixtures（qapp / settings_guard 见 tests/conftest.py）──


@pytest.fixture
def main_window(qapp, settings_guard, tmp_path):
    """带临时数据文件的 MainWindow（不触碰真实 data.json）。"""
    from app.main_window import MainWindow

    win = MainWindow(store=DataStore(tmp_path / "data.json"))
    yield win
    win.close()


# ── InputPanel getter 语义（C4 seam 契约）────────────────


def test_get_cash_value_semantics(qapp):
    ip = InputPanel()
    # 空输入 → None
    ip.cash_entry.setText("")
    assert ip.get_cash_value() is None
    # 有效输入 → 解析值
    ip.cash_entry.setText("1,000")
    assert ip.get_cash_value() == 1000.0
    # 带单位后缀
    ip.cash_entry.setText("1.5K")
    assert ip.get_cash_value() == 1500.0
    # 非法数字格式 → ValueError
    ip.cash_entry.setText("1.2.3")
    with pytest.raises(ValueError):
        ip.get_cash_value()
    # 纯垃圾文本被清洗为空 → None
    ip.cash_entry.setText("abc")
    assert ip.get_cash_value() is None


def test_get_warehouse_value_semantics(qapp):
    ip = InputPanel()
    ip.warehouse_entry.setText("")
    assert ip.get_warehouse_value() is None
    ip.warehouse_entry.setText("2M")
    assert ip.get_warehouse_value() == 2_000_000.0
    ip.warehouse_entry.setText("--1")
    with pytest.raises(ValueError):
        ip.get_warehouse_value()


def test_get_raw_getters(qapp):
    ip = InputPanel()
    ip.cash_entry.setText("¥1,000")
    ip.warehouse_entry.setText("2M")
    assert ip.get_cash_raw() == "¥1,000"
    assert ip.get_warehouse_raw() == "2M"


def test_refresh_validity(qapp):
    ip = InputPanel()
    ip.cash_entry.setText("100")
    ip.refresh_validity()
    assert ip.cash_entry.property("validity") == "valid"
    ip.cash_entry.setText("abc")
    ip.refresh_validity()
    assert ip.cash_entry.property("validity") == "invalid"


# ── 编辑状态单方归属 InputPanel ──────────────────────────


def test_editing_state_owned_by_input_panel(qapp):
    ip = InputPanel()
    assert not ip.is_editing()
    assert ip.get_editing_date() is None

    ip.set_edit_mode("2026-07-25", 100.0, 200.0)
    assert ip.is_editing()
    assert ip.get_editing_date() == "2026-07-25"

    ip.cancel_edit()
    assert not ip.is_editing()
    assert ip.get_editing_date() is None


def test_main_window_has_no_editing_date_attr(main_window):
    """MainWindow 不得再持有 _editing_date（C4 收敛，防复发）。"""
    assert not hasattr(main_window, "_editing_date")


def test_main_window_has_no_direct_entry_access(main_window):
    """main_window.py 不得直取输入框或调用 parse_money_input（C9 源码级守卫）。

    行为等价测试（如 test_save_today_uses_public_getters）即使回归到
    cash_entry.text() + parse_money_input 也会通过；本测试用 AST 扫描源码，
    拦截任何绕过 InputPanel 公开 getter 的访问路径。
    """
    import ast
    import inspect

    import app.main_window as mw

    tree = ast.parse(inspect.getsource(mw))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in {
            "cash_entry",
            "warehouse_entry",
        }:
            violations.append(
                f"L{node.lineno}: 直取输入框 {node.attr}（绕过公开 getter）"
            )
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "parse_money_input"
        ):
            violations.append(
                f"L{node.lineno}: 调用 parse_money_input（应走公开 getter）"
            )
    assert violations == [], (
        f"main_window.py 绕过 InputPanel 公开 API：{violations}"
    )


def test_main_window_delegates_edit_state(main_window):
    win = main_window
    win._start_edit(
        "2026-07-25", DayRecord(cash=100.0, warehouse=200.0, date="2026-07-25")
    )
    assert win.input_panel.is_editing()
    assert win.input_panel.get_editing_date() == "2026-07-25"

    win._cancel_edit()
    assert not win.input_panel.is_editing()
    assert win.input_panel.get_editing_date() is None


# ── save_today 走公开 API（行为等价回归）─────────────────


def test_save_today_uses_public_getters(main_window):
    win = main_window
    win.input_panel.fill_values(100, 200)
    win.save_today()
    rec = win.logic.get_record(win.today)
    assert rec is not None
    assert rec.cash == 100.0
    assert rec.warehouse == 200.0
    # 非编辑模式保存后清空输入框，便于连续录入
    assert win.input_panel.get_cash_raw() == ""


def test_save_today_edit_existing_record(main_window):
    win = main_window
    win.input_panel.fill_values(100, 200)
    win.save_today()
    today = win.today

    rec = win.logic.get_record(today)
    win._start_edit(today, rec)
    win.input_panel.fill_values(150, 250)
    win.save_today()

    updated = win.logic.get_record(today)
    assert updated is not None
    assert updated.cash == 150.0
    assert updated.warehouse == 250.0
    # 保存后自动退出编辑模式
    assert not win.input_panel.is_editing()
    assert win.input_panel.get_editing_date() is None

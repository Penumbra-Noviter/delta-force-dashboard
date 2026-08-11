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

from PySide6.QtWidgets import QMessageBox

from app.input_panel import InputPanel
from calculator import DayRecord
from data_store import DataStore

__all__ = []


# ── fixtures（qapp / settings_guard 见 tests/conftest.py）──


@pytest.fixture
def main_window(qapp, settings_guard, tmp_path):
    """带临时数据文件的 MainWindow（不触碰真实 data.json）。

    C2-03：构造注入 stub client——利润页预加载零真实网络。
    """
    from app.main_window import MainWindow
    from tests.conftest import make_stub_client

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        client=make_stub_client(),
    )
    yield win
    win.close()


@pytest.fixture
def shown_panel(qapp):
    """显示的 InputPanel（D-04 焦点事件链路）。

    offscreen 下 setFocus 的焦点事件只对可见窗口派发，聚焦反格式化 /
    失焦立即校验等用例需窗口处于可见状态。
    """
    from PySide6.QtTest import QTest

    ip = InputPanel()
    ip.show()
    QTest.qWait(30)
    yield ip
    ip.close()


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


def test_validation_via_real_event_chain(qapp, type_and_settle):
    """校验属性经真实事件链路更新：键入 → 去抖 → validity_changed（D-04）。

    原 test_refresh_validity 直调 refresh_validity() 同步后门；D-04 改为
    QTest 键入 + 等待去抖定时器，走 textChanged→去抖→signal 的真实路径。
    """
    ip = InputPanel()
    type_and_settle(ip.cash_entry, "100")
    assert ip.cash_entry.property("validity") == "valid"
    type_and_settle(ip.cash_entry, "abc")
    assert ip.cash_entry.property("validity") == "invalid"


def test_w02_shake_on_invalid_input(qapp, type_and_settle):
    """W-02：非法输入触发抖动动画（状态从 valid 变 invalid），防抖不重复。"""
    from PySide6.QtTest import QTest

    ip = InputPanel()
    ip.show()
    QTest.qWait(30)

    type_and_settle(ip.cash_entry, "100")  # valid
    type_and_settle(ip.cash_entry, "abc")  # valid → invalid：抖动触发
    assert ip.cash_entry._shake_anim is not None
    first = ip.cash_entry._shake_anim
    QTest.qWait(200)  # 动画结束，pos 恢复原位
    # 连续非法（已 invalid）→ 不重复抖动（防抖）
    type_and_settle(ip.cash_entry, "xyz")
    assert ip.cash_entry._shake_anim is first
    ip.close()


def test_invariant_warning_border_on_cash_over_warehouse(qapp, type_and_settle):
    """现金 > 仓库 → 两个输入框进入 warning 态（越界红边，O-08）。"""
    ip = InputPanel()
    type_and_settle(ip.cash_entry, "200")
    type_and_settle(ip.warehouse_entry, "100")
    assert ip.cash_entry.property("validity") == "warning"
    assert ip.warehouse_entry.property("validity") == "warning"


def test_invariant_warning_cleared_when_balanced(qapp, type_and_settle):
    """现金降到 ≤ 仓库后恢复各自自然校验态。"""
    ip = InputPanel()
    type_and_settle(ip.cash_entry, "200")
    type_and_settle(ip.warehouse_entry, "100")
    assert ip.cash_entry.property("validity") == "warning"

    type_and_settle(ip.warehouse_entry, "200")
    assert ip.cash_entry.property("validity") == "valid"
    assert ip.warehouse_entry.property("validity") == "valid"


def test_invariant_warning_boundary_equal_not_triggered(qapp, type_and_settle):
    """现金 == 仓库（边界）不触发警告。"""
    ip = InputPanel()
    type_and_settle(ip.cash_entry, "100")
    type_and_settle(ip.warehouse_entry, "100")
    assert ip.cash_entry.property("validity") == "valid"
    assert ip.warehouse_entry.property("validity") == "valid"


def test_invariant_warning_not_triggered_with_empty_field(qapp, type_and_settle):
    """仓库为空时现金值不触发警告（无可比较对象）。"""
    ip = InputPanel()
    type_and_settle(ip.cash_entry, "200")
    assert ip.cash_entry.property("validity") == "valid"


def test_money_line_edit_public_refresh_validity(qapp):
    """MoneyLineEdit.refresh_validity() 公开 seam：委托 _update_validity()。

    D-04：这是唯一保留的同步 seam 契约测试——seam 供主窗口 Esc 清空等
    程序化改动后同步重校验（main_window._clear_focused_input）；其余行为
    用例全部走真实事件链路（type_and_settle），不再把 seam 当测试后门。
    """
    from app.input_panel import MoneyLineEdit

    edit = MoneyLineEdit()
    edit.setText("100")
    edit.refresh_validity()
    assert edit.property("validity") == "valid"

    edit.setText("abc")
    edit.refresh_validity()
    assert edit.property("validity") == "invalid"

    edit.setText("")
    edit.refresh_validity()
    assert edit.property("validity") == "normal"


def test_focus_in_unformat_guardrail(shown_panel):
    """聚焦反格式化护栏：格式化文本在聚焦瞬间恢复为纯数字并全选。

    D-04 真实焦点链路：setFocus → Qt 派发 FocusIn → focusInEvent 反格式化，
    便于用户聚焦后直接改数字（含全选覆盖）。
    """
    ip = shown_panel
    cash = ip.cash_entry

    ip.warehouse_entry.setFocus()  # 让现金框先处于非聚焦态
    cash._formatting = False
    cash.setText("¥123,456.00")
    cash.setFocus()  # 真实 FocusIn → 反格式化 + 全选
    assert cash.text() == "123456"
    assert cash.selectedText() == "123456"


def test_focus_out_immediate_validation(shown_panel):
    """失焦立即校验：非法文本在失焦瞬间完成校验，不等 150ms 去抖。

    D-04 真实焦点链路：focusOutEvent 停掉去抖定时器并同步重校验，
    保证用户移开焦点时红边/按钮状态已就位（不残留等待窗口）。
    """
    from PySide6.QtTest import QTest

    ip = shown_panel
    cash = ip.cash_entry

    cash.setFocus()
    cash.clear()
    QTest.keyClicks(cash, "abc")
    assert cash.property("validity") == "normal"  # 去抖未到，属性未更新

    ip.warehouse_entry.setFocus()  # 焦点移出 → focusOutEvent 立即校验
    assert cash.property("validity") == "invalid"


def test_focus_out_formatting(shown_panel):
    """失焦格式化：纯数字在失焦瞬间格式化为 ¥ 千分位（真实焦点链路）。

    原 test_ui_smoke 的同名用例直派 focusOutEvent；D-04 收敛到真实
    焦点路径（焦点从现金框移出 → Qt 派发 FocusOut → focusOutEvent）。
    """
    ip = shown_panel
    cash = ip.cash_entry

    cash.setFocus()
    cash.setText("123456")
    assert cash.text() == "123456"

    ip.warehouse_entry.setFocus()  # 焦点移出 → focusOutEvent 格式化
    assert cash.text() == "¥123,456.00"


def test_input_panel_does_not_call_private_update_validity(qapp):
    """InputPanel.refresh_validity 不得直调 MoneyLineEdit._update_validity（C9 静态守卫）。

    行为等价测试即使回归到私有方法调用也会通过；本测试用 AST 扫描源码，
    拦截 InputPanel 跨类直取 _update_validity 的访问路径（O-02 防复发）。
    """
    import ast
    import inspect

    import app.input_panel as ip_mod

    tree = ast.parse(inspect.getsource(ip_mod))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "InputPanel":
            for child in node.body:
                if (
                    isinstance(child, ast.FunctionDef)
                    and child.name == "refresh_validity"
                ):
                    for sub in ast.walk(child):
                        if (
                            isinstance(sub, ast.Attribute)
                            and sub.attr == "_update_validity"
                        ):
                            violations.append(f"L{sub.lineno}")
    assert violations == [], (
        f"InputPanel.refresh_validity 直调 MoneyLineEdit._update_validity（私有方法）：{violations}"
    )


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

def test_save_today_blocks_cash_over_warehouse(main_window, monkeypatch):
    """现金 > 仓库：保存被拦截（弹警告 + 不落盘，O-08）。"""
    win = main_window
    warned: list[str] = []

    def fake_warning(parent, title, text):
        warned.append(text)

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(fake_warning))

    win.input_panel.fill_values(200, 100)
    win.save_today()

    assert win.logic.get_record(win.today) is None
    assert len(warned) == 1 and "现金不能大于仓库" in warned[0]


def test_save_today_allows_boundary_equal(main_window):
    """现金 == 仓库（边界相等）：允许保存。"""
    win = main_window
    win.input_panel.fill_values(100, 100)
    win.save_today()
    rec = win.logic.get_record(win.today)
    assert rec is not None
    assert rec.cash == 100.0
    assert rec.warehouse == 100.0

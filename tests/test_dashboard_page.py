"""C4 块 1：build_dashboard 直构装配的独立单测。

验证装配产物（bundle 8 成员类型）、页面布局层级（输入卡限宽 520 / KPI 卡 /
表格卡 stretch 1 / 图表卡 min/max 高 / 提示栏在底部）与信号显式连接
（注入 stub MainWindow + 信号 spy，构造零网络、零数据窗口）。
"""

from __future__ import annotations

import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import fields
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.chart_widget import ChartWidget
from app.dashboard_page import DashboardBundle, build_dashboard
from app.input_panel import InputPanel
from app.table_widget import TableWidget

__all__ = []


class StubMainWindow:
    """build_dashboard 依赖的最小替身：辅助方法 + 信号槽记录。

    _build_card 返回真实 QFrame（qapp 下可创建）；_chart_min_h / _chart_max_h /
    today 为固定值；7 个槽方法把调用追加到 calls（保序），供信号 spy 断言。
    """

    _chart_min_h = 160
    _chart_max_h = 240
    today = "2026-08-12"

    def __init__(self) -> None:
        self.calls: list = []

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("cardFrame")  # 与 MainWindow._build_card 契约一致
        return card

    def save_today(self) -> None:
        self.calls.append("save_today")

    def _cancel_edit(self) -> None:
        self.calls.append("_cancel_edit")

    def _reuse_last_record(self) -> None:
        self.calls.append("_reuse_last_record")

    def _cancel_reuse(self) -> None:
        self.calls.append("_cancel_reuse")

    def _start_edit(self, date_str: str, record: object) -> None:
        self.calls.append(("_start_edit", date_str, record))

    def _delete_record(self, date_str: str) -> None:
        self.calls.append(("_delete_record", date_str))

    def _on_view_changed(self, n: int) -> None:
        self.calls.append(("_on_view_changed", n))


@pytest.fixture
def stub_mw(qapp) -> StubMainWindow:
    """带 qapp 的 stub MainWindow（build_dashboard 装配出真实 Qt 控件）。"""
    return StubMainWindow()


def _widget_items(layout):
    """[(index, widget)]：布局内直接 widget 项（保持顺序，跳过间距/布局项）。"""
    return [
        (i, layout.itemAt(i).widget())
        for i in range(layout.count())
        if layout.itemAt(i).widget() is not None
    ]


def test_bundle_contract_and_types(stub_mw):
    """bundle 8 成员类型正确，dataclass 字段契约不漂移。"""
    bundle = build_dashboard(stub_mw)

    assert [f.name for f in fields(DashboardBundle)] == [
        "input_panel",
        "table",
        "chart",
        "summary_label",
        "summary_caption",
        "cash_summary_label",
        "cash_summary_caption",
        "hint_label",
    ]
    assert isinstance(bundle.input_panel, InputPanel)
    assert isinstance(bundle.table, TableWidget)
    assert isinstance(bundle.chart, ChartWidget)
    for label in (
        bundle.summary_label,
        bundle.summary_caption,
        bundle.cash_summary_label,
        bundle.cash_summary_caption,
        bundle.hint_label,
    ):
        assert isinstance(label, QLabel)

    # objectName 契约（theme.py QSS 选择器依赖）
    assert bundle.summary_label.objectName() == "summaryLabel"
    assert bundle.summary_caption.objectName() == "summaryCaption"
    assert bundle.cash_summary_label.objectName() == "cashSummaryLabel"
    assert bundle.cash_summary_caption.objectName() == "cashSummaryCaption"
    assert bundle.hint_label.objectName() == "hintLabel"
    assert "Enter 保存" in bundle.hint_label.text()


def test_layout_hierarchy(stub_mw):
    """布局层级：标题栏/日期/顶部条（输入卡 520 + KPI 卡）/表格卡 stretch1/
    图表卡 min-max 高/提示栏在底部。"""
    bundle = build_dashboard(stub_mw)
    page = stub_mw._dashboard_page
    assert page.objectName() == "dashboardPage"

    layout = page.layout()
    assert isinstance(layout, QVBoxLayout)
    m = layout.contentsMargins()
    assert (m.left(), m.top(), m.right(), m.bottom()) == (32, 24, 32, 16)
    assert layout.spacing() == 0

    # 顶层顺序：标题栏 → 日期 → 顶部条 → 表格卡 → 图表卡 → 提示栏（底部最后）
    items = _widget_items(layout)
    assert [w.objectName() for w in [it[1] for it in items]] == [
        "",
        "dateLabel",
        "",
        "cardFrame",
        "cardFrame",
        "hintLabel",
    ]
    assert items[-1][1] is bundle.hint_label
    assert items[-1][0] == layout.count() - 1  # 提示栏是最后一个布局项
    title_bar, date_label, top_bar, table_card, chart_card, _ = (
        it[1] for it in items
    )

    # 标题栏：标题 + 今日未录入提醒（页面标签引用与布局内标签同一）
    title_layout = title_bar.layout()
    assert isinstance(title_layout, QHBoxLayout)
    title_widgets = [w for _, w in _widget_items(title_layout)]
    assert [w.text() for w in title_widgets] == ["Delta Force Dashboard", "今日未录入"]
    assert page._title_label is title_widgets[0]
    assert page._today_status_label is title_widgets[1]
    # objectName 契约（theme.py QSS 选择器依赖）
    assert title_widgets[0].objectName() == "titleLabel"
    assert title_widgets[1].objectName() == "todayStatusLabel"

    # 日期标签：与标题同侧左对齐（U-07）
    assert date_label is page._date_label
    assert date_label.text() == stub_mw.today
    assert date_label.alignment() == (
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )

    # 顶部条：输入卡（限宽 520，stretch 0）+ KPI 卡（stretch 1）
    top_layout = top_bar.layout()
    assert isinstance(top_layout, QHBoxLayout)
    top_items = _widget_items(top_layout)
    assert len(top_items) == 2
    input_card = top_items[0][1]
    kpi_card = top_items[1][1]
    assert isinstance(input_card, QFrame)
    assert input_card.maximumWidth() == 520
    assert top_layout.stretch(top_items[0][0]) == 0
    assert top_layout.stretch(top_items[1][0]) == 1
    assert input_card.layout().itemAt(0).widget() is bundle.input_panel

    # KPI 卡：双磁贴（说明 + 大数字）逐对入列，尾部 stretch
    kcl = kpi_card.layout()
    assert isinstance(kcl, QVBoxLayout)
    tile1, tile2 = kcl.itemAt(0).layout(), kcl.itemAt(1).layout()
    assert isinstance(tile1, QVBoxLayout) and isinstance(tile2, QVBoxLayout)
    assert tile1.itemAt(0).widget() is bundle.summary_caption
    assert tile1.itemAt(1).widget() is bundle.summary_label
    assert tile2.itemAt(0).widget() is bundle.cash_summary_caption
    assert tile2.itemAt(1).widget() is bundle.cash_summary_label
    assert kcl.itemAt(kcl.count() - 1).spacerItem() is not None

    # 表格卡：stretch 1（吃窗口增长空间），图表卡：stretch 0 + min/max 高
    assert layout.stretch(items[3][0]) == 1
    assert table_card.layout().itemAt(0).widget() is bundle.table
    assert layout.stretch(items[4][0]) == 0
    assert chart_card.layout().itemAt(0).widget() is bundle.chart
    assert bundle.chart.minimumHeight() == stub_mw._chart_min_h
    assert bundle.chart.maximumHeight() == stub_mw._chart_max_h


def test_signals_connected_explicitly(stub_mw):
    """7 组信号→槽显式连接生效：逐一 emit，槽按序收到（一对一，非扇出）。"""
    bundle = build_dashboard(stub_mw)
    record = SimpleNamespace(cash=1.0, warehouse=2.0)

    bundle.input_panel.save_requested.emit()
    bundle.input_panel.cancel_requested.emit()
    bundle.input_panel.reuse_requested.emit()
    bundle.input_panel.reuse_cancel_requested.emit()
    bundle.table.edit_requested.emit("2026-08-01", record)
    bundle.table.delete_requested.emit("2026-08-01")
    bundle.table.view_changed.emit(30)

    assert stub_mw.calls == [
        "save_today",
        "_cancel_edit",
        "_reuse_last_record",
        "_cancel_reuse",
        ("_start_edit", "2026-08-01", record),
        ("_delete_record", "2026-08-01"),
        ("_on_view_changed", 30),
    ]


# ── Falsify：使 build_dashboard 崩溃的输入，错误信息须指明缺失成员 ──


def test_build_dashboard_none_mw_raises(qapp):
    """None 参数 → AttributeError 指明缺失槽（不静默、不模糊）。"""
    with pytest.raises(AttributeError, match="save_today"):
        build_dashboard(None)


def test_build_dashboard_missing_slots_raises(qapp):
    """mw 缺槽方法 → AttributeError 指明缺失成员。"""
    with pytest.raises(AttributeError, match="save_today"):
        build_dashboard(object())


def test_build_dashboard_missing_today_raises(qapp):
    """mw 缺 today 属性 → AttributeError 指明缺失成员。"""
    mw = SimpleNamespace(
        _chart_min_h=160,
        _chart_max_h=240,
        save_today=lambda: None,
        _cancel_edit=lambda: None,
        _reuse_last_record=lambda: None,
        _cancel_reuse=lambda: None,
        _start_edit=lambda *args: None,
        _delete_record=lambda *args: None,
        _on_view_changed=lambda *args: None,
    )
    with pytest.raises(AttributeError, match="today"):
        build_dashboard(mw)


def test_build_dashboard_missing_card_helper_raises(qapp):
    """mw 缺 _build_card 辅助 → AttributeError 指明辅助名。"""
    mw = SimpleNamespace(
        today="2026-08-12",
        _chart_min_h=160,
        _chart_max_h=240,
        save_today=lambda: None,
        _cancel_edit=lambda: None,
        _reuse_last_record=lambda: None,
        _cancel_reuse=lambda: None,
        _start_edit=lambda *args: None,
        _delete_record=lambda *args: None,
        _on_view_changed=lambda *args: None,
    )
    with pytest.raises(AttributeError, match="_build_card"):
        build_dashboard(mw)


def test_signals_single_connection_no_spurious(qapp):
    """Falsify（信号接线错误场景）：重复 emit 恰触发一次（无重复接线）。"""
    mw = StubMainWindow()
    bundle = build_dashboard(mw)

    bundle.input_panel.save_requested.emit()
    bundle.input_panel.save_requested.emit()
    assert mw.calls == ["save_today", "save_today"]  # 单次连接：一次 emit 一次触发

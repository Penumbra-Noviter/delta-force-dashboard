"""C5：`DashboardPage` 装配单测（页族同构后）。

验证装配产物（bundle 8 成员类型 / objectName 契约）、布局层级（输入卡限宽
520 / KPI 双磁贴卡 / 表格卡 stretch 1 / 图表卡 min-max 高 / 提示栏在底部）、
公开标签属性（`title_label` / `today_status_label` / `date_label`），以及
「装配不接线」——7 组信号接线归 `MainWindow._connect_signals`（C5 深化）。

信号接线用例在 `tests/test_ui_smoke.py`（MainWindow 级：`receivers` 计数）。
"""

from __future__ import annotations

import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import fields

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.chart_widget import ChartWidget
from app.dashboard_page import DashboardBundle, DashboardPage
from app.input_panel import InputPanel
from app.table_widget import TableWidget

__all__ = []

TODAY = "2026-08-12"
CHART_MIN_H = 160
CHART_MAX_H = 240


@pytest.fixture
def page(qapp) -> DashboardPage:
    """真实仪表盘页（构造参数 = 值接口：today + 图表高度区间）。"""
    return DashboardPage(TODAY, CHART_MIN_H, CHART_MAX_H)


def _widget_items(layout):
    """[(index, widget)]：布局内直接 widget 项（保持顺序，跳过间距/布局项）。"""
    return [
        (i, layout.itemAt(i).widget())
        for i in range(layout.count())
        if layout.itemAt(i).widget() is not None
    ]


def test_bundle_contract_and_types(page):
    """bundle 8 成员类型正确，dataclass 字段契约不漂移。"""
    bundle = page.bundle

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


def test_layout_hierarchy(page):
    """布局层级：标题栏/日期/顶部条（输入卡 520 + KPI 卡）/表格卡 stretch1/
    图表卡 min-max 高/提示栏在底部。"""
    bundle = page.bundle
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

    # 标题栏：标题 + 今日未录入提醒（公开属性与布局内标签同一）
    title_layout = title_bar.layout()
    assert isinstance(title_layout, QHBoxLayout)
    title_widgets = [w for _, w in _widget_items(title_layout)]
    assert [w.text() for w in title_widgets] == ["Delta Force Dashboard", "今日未录入"]
    assert page.title_label is title_widgets[0]
    assert page.today_status_label is title_widgets[1]
    # objectName 契约（theme.py QSS 选择器依赖）
    assert title_widgets[0].objectName() == "titleLabel"
    assert title_widgets[1].objectName() == "todayStatusLabel"

    # 日期标签：与标题同侧左对齐（U-07）
    assert date_label is page.date_label
    assert date_label.text() == TODAY
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
    assert bundle.chart.minimumHeight() == CHART_MIN_H
    assert bundle.chart.maximumHeight() == CHART_MAX_H


def test_public_label_attributes(page):
    """C5：三个页面标签是公开属性（MainWindow 不再私读 `_title_label` 等）。"""
    assert isinstance(page.title_label, QLabel)
    assert isinstance(page.today_status_label, QLabel)
    assert isinstance(page.date_label, QLabel)
    assert not hasattr(page, "_title_label")
    assert not hasattr(page, "_today_status_label")
    assert not hasattr(page, "_date_label")


def test_page_assembly_does_not_wire_signals(page):
    """C5：装配不接线——7 组信号零接收者（接线归 MainWindow._connect_signals）。

    签名串取 Qt 元对象格式（`2name(args)`）；参数less 信号 `()`，带参信号用
    实际类型名（QString/PyObject/int）。
    """
    ip, tw = page.bundle.input_panel, page.bundle.table
    for widget, sig in (
        (ip, "2save_requested()"),
        (ip, "2cancel_requested()"),
        (ip, "2reuse_requested()"),
        (ip, "2reuse_cancel_requested()"),
        (tw, "2edit_requested(QString,PyObject)"),
        (tw, "2delete_requested(QString)"),
        (tw, "2view_changed(int)"),
    ):
        assert widget.receivers(sig) == 0, f"{sig} 在装配期被接线了"

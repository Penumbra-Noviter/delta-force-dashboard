"""记账仪表盘页装配（C4 块 1）：从 WidgetRegistry 间接层改为直构。

`build_dashboard(mw)` 一次性完成仪表盘页（QStackedWidget Page 0）的组件创建、
布局与信号显式连接，返回 `DashboardBundle` 装配产物；页面本体经
`build_dashboard_page` 布局函数构建并挂到 `mw._dashboard_page`，由
MainWindow 入栈并解包标签引用。registry 仅剩引用被移除（registry.py 本体
由后续工单删除）。
"""

from __future__ import annotations

__all__ = ["DashboardBundle", "build_dashboard", "build_dashboard_page"]

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.chart_widget import ChartWidget
from app.input_panel import InputPanel
from app.table_widget import TableWidget

if TYPE_CHECKING:
    from app.main_window import MainWindow


@dataclass
class DashboardBundle:
    """仪表盘装配产物：8 个组件句柄（MainWindow 解包为既有属性名）。

    Attributes:
        input_panel: 输入面板（保存 / 取消 / 复用）。
        table: 双栏记录表格（编辑 / 删除 / 视图切换）。
        chart: 曲线图。
        summary_label: 总盈亏磁贴大数字行。
        summary_caption: 总盈亏磁贴说明行。
        cash_summary_label: 现金总变化磁贴大数字行。
        cash_summary_caption: 现金总变化磁贴说明行。
        hint_label: 底部提示栏。
    """

    input_panel: InputPanel
    table: TableWidget
    chart: ChartWidget
    summary_label: QLabel
    summary_caption: QLabel
    cash_summary_label: QLabel
    cash_summary_caption: QLabel
    hint_label: QLabel


def build_dashboard_page(
    mw: MainWindow, bundle: DashboardBundle, today: str
) -> QWidget:
    """构建仪表盘页面本体（标题栏 + 日期 + bundle 组件布局）。

    Args:
        mw: MainWindow 实例，复用其 `_build_card` / `_chart_min_h` /
            `_chart_max_h` 既有辅助。
        bundle: 已创建的组件句柄（build_dashboard 传入）。
        today: 日期标签文本（"YYYY-MM-DD"）。

    Returns:
        页面 QWidget（objectName "dashboardPage"），挂载 `_title_label` /
        `_today_status_label` / `_date_label` 三个标签引用，供 MainWindow
        解包保持既有属性名。布局层级自上而下：标题栏 → 日期 → 顶部条
        （输入卡限宽 520 + KPI 双磁贴卡）→ 表格卡（stretch 1）→ 图表卡
        （min/max 高）→ 底部提示栏。
    """
    page = QWidget()
    page.setObjectName("dashboardPage")

    layout = QVBoxLayout(page)
    layout.setContentsMargins(32, 24, 32, 16)
    layout.setSpacing(0)

    # 标题栏（简化版：只保留标题 + 今日未录入提醒）
    title_bar = QWidget()
    title_layout = QHBoxLayout(title_bar)
    title_layout.setContentsMargins(0, 0, 0, 0)

    page._title_label = QLabel("Delta Force Dashboard")
    page._title_label.setObjectName("titleLabel")
    title_layout.addWidget(page._title_label)

    page._today_status_label = QLabel("今日未录入")
    page._today_status_label.setObjectName("todayStatusLabel")
    title_layout.addWidget(page._today_status_label)

    title_layout.addStretch()
    layout.addWidget(title_bar)

    # 日期（U-07：与标题同侧左对齐，消除「标题左、日期居中」的轴线错位）
    page._date_label = QLabel(today)
    page._date_label.setObjectName("dateLabel")
    page._date_label.setAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    layout.addSpacing(4)
    layout.addWidget(page._date_label)
    layout.addSpacing(12)

    # 顶部区域（U-01）：输入卡（左，限宽 520）+ KPI 磁贴卡（右，吃剩余空间）
    top_bar = QWidget()
    top_bar_layout = QHBoxLayout(top_bar)
    top_bar_layout.setContentsMargins(0, 0, 0, 0)
    top_bar_layout.setSpacing(12)

    input_card = mw._build_card()
    input_card.setMaximumWidth(520)  # 限宽：宽窗口下输入框不再无限横向拉伸（U-01）
    input_card_layout = QVBoxLayout(input_card)
    input_card_layout.setContentsMargins(10, 8, 10, 8)
    input_card_layout.addWidget(bundle.input_panel)
    top_bar_layout.addWidget(input_card, 0)

    # KPI 磁贴卡（总盈亏 / 现金总变化）——大数字（summary_style 22px 信号色）
    # + 小字说明（caption），与输入卡并排，成为页面的读数锚点（U-01）。
    kpi_card = mw._build_card()
    kcl = QVBoxLayout(kpi_card)
    kcl.setContentsMargins(14, 10, 14, 10)
    kcl.setSpacing(6)
    for caption, value in (
        (bundle.summary_caption, bundle.summary_label),
        (bundle.cash_summary_caption, bundle.cash_summary_label),
    ):
        tile = QVBoxLayout()
        tile.setSpacing(2)
        tile.addWidget(caption)
        tile.addWidget(value)
        kcl.addLayout(tile)
    kcl.addStretch()
    top_bar_layout.addWidget(kpi_card, 1)

    layout.addWidget(top_bar)
    layout.addSpacing(8)

    # 表格全量展示优先（H-01 语义，U-02 弹性翻转后用户实测回退）：
    # 表格吃窗口增长空间，超高时 _DaySubTable 内部滚动仅作极端兜底
    table_card = mw._build_card()
    tcl = QVBoxLayout(table_card)
    tcl.setContentsMargins(10, 8, 10, 8)
    tcl.addWidget(bundle.table)
    layout.addWidget(table_card, 1)
    layout.addSpacing(8)

    # 折线图固定小卡片（H-01 语义）：不随窗口扩张，为表格全量展示让位；
    # 高度区间按屏幕可用空间自适应（_window_preset，U-09 方案 A）
    chart_card = mw._build_card()
    ccl = QVBoxLayout(chart_card)
    ccl.setContentsMargins(10, 8, 10, 8)
    ccl.addWidget(bundle.chart)
    bundle.chart.setMinimumHeight(mw._chart_min_h)
    bundle.chart.setMaximumHeight(mw._chart_max_h)
    layout.addWidget(chart_card, 0)
    layout.addSpacing(8)

    # 底部提示栏
    layout.addWidget(bundle.hint_label)

    return page


def build_dashboard(mw: MainWindow) -> DashboardBundle:
    """一次性完成仪表盘组件创建、布局与信号显式连接（C4 块 1 直构）。

    Args:
        mw: MainWindow 实例。复用其 `_build_card` / `_chart_min_h` /
            `_chart_max_h` / `today` 既有成员；信号连接到 mw 既有槽
            （save_today / _cancel_edit / _reuse_last_record / _cancel_reuse /
            _start_edit / _delete_record / _on_view_changed，语义与
            registry 时期一致）。

    Returns:
        DashboardBundle：8 个组件句柄。页面本体经 build_dashboard_page
        构建后挂到 `mw._dashboard_page`，MainWindow._build_ui 取之入栈。
    """
    summary_label = QLabel("")
    summary_label.setObjectName("summaryLabel")
    summary_label.setWordWrap(True)
    summary_caption = QLabel("")
    summary_caption.setObjectName("summaryCaption")

    cash_summary_label = QLabel("")
    cash_summary_label.setObjectName("cashSummaryLabel")
    cash_summary_label.setWordWrap(True)
    cash_summary_caption = QLabel("")
    cash_summary_caption.setObjectName("cashSummaryCaption")

    hint_label = QLabel(
        "Enter 保存 ｜ Ctrl+A 全选 ｜ Esc 清空 ｜ "
        "支持 K/M/B 后缀（如 1.5K = 1,500）"
    )
    hint_label.setObjectName("hintLabel")

    bundle = DashboardBundle(
        input_panel=InputPanel(),
        table=TableWidget(),
        chart=ChartWidget(),
        summary_label=summary_label,
        summary_caption=summary_caption,
        cash_summary_label=cash_summary_label,
        cash_summary_caption=cash_summary_caption,
        hint_label=hint_label,
    )

    # 信号显式连接（一对一，无 connect_all 间接层）
    bundle.input_panel.save_requested.connect(mw.save_today)
    bundle.input_panel.cancel_requested.connect(mw._cancel_edit)
    bundle.input_panel.reuse_requested.connect(mw._reuse_last_record)
    bundle.input_panel.reuse_cancel_requested.connect(mw._cancel_reuse)
    bundle.table.edit_requested.connect(mw._start_edit)
    bundle.table.delete_requested.connect(mw._delete_record)
    bundle.table.view_changed.connect(mw._on_view_changed)

    mw._dashboard_page = build_dashboard_page(mw, bundle, mw.today)
    return bundle

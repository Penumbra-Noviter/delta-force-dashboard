"""记账仪表盘页（C4 块 1 直构装配；C5 深化为页族同构的 `DashboardPage`）。

`DashboardPage(QWidget)` 一次性完成仪表盘页（QStackedWidget Page 0）的组件
创建与布局，对外只暴露值接口：构造参数 `today` / `chart_min_h` /
`chart_max_h`，公开属性 `bundle`（8 组件）与 `title_label` /
`today_status_label` / `date_label`。

C5 深化（原形态的摩擦与处置）：
- 原 `build_dashboard(mw)` 反向依赖 MainWindow——连 7 个私有槽、调
  `mw._build_card()`、读 `mw._chart_min_h/_chart_max_h/mw.today`，并经副作用
  把页面写回 `mw._dashboard_page`，MainWindow 再私读页面的三个私有标签。
  现在构造参数即接口（值而非宿主），页面属性公开；
- 信号接线归 `MainWindow._connect_signals`（与侧边栏按钮/快捷键同处），
  本模块不再接触任何回调；
- `_card_frame()`（原 `MainWindow._build_card`）内迁至此——卡片外观是仪表盘
  的装配细节，全仓只被本模块使用；
- 与页族一致：`ProfitPage` / `CraftingPage` / `ExchangePage` / `BonusDoorPage`
  都是 QWidget 子类，仪表盘此前是唯一「函数 + 挂宿主属性」的异类。
"""

from __future__ import annotations

__all__ = ["DashboardBundle", "DashboardPage"]

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.chart_widget import ChartWidget
from app.input_panel import InputPanel
from app.table_widget import TableWidget


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


def _card_frame() -> QFrame:
    """构建带阴影的卡片 QFrame（12px 圆角 + 微阴影）。

    QSS 不支持 box-shadow，故用 QGraphicsDropShadowEffect（C5 自
    `MainWindow._build_card` 内迁——卡片外观是仪表盘的装配细节）。
    """
    card = QFrame()
    card.setObjectName("cardFrame")
    card.setFrameShape(QFrame.Shape.StyledPanel)

    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(12)
    shadow.setOffset(0, 2)
    shadow.setColor(QColor(0, 0, 0, 20))
    card.setGraphicsEffect(shadow)

    return card


class DashboardPage(QWidget):
    """记账仪表盘页（QStackedWidget Page 0）。

    Args:
        today: 日期标签文本（"YYYY-MM-DD"）。
        chart_min_h: 图表卡最小高（窗口预设按屏幕可用空间算出）。
        chart_max_h: 图表卡最大高。

    公开属性：
        bundle: `DashboardBundle`（8 组件，MainWindow 解包为既有属性名）。
        title_label / today_status_label / date_label: 页面标签（C5 起公开，
            MainWindow 不再私读）。

    布局层级自上而下：标题栏 → 日期 → 顶部条（输入卡限宽 520 + KPI 双磁贴卡）
    → 表格卡（stretch 1）→ 图表卡（min/max 高）→ 底部提示栏。
    信号接线不在此处——归 `MainWindow._connect_signals`（C5）。
    """

    def __init__(
        self,
        today: str,
        chart_min_h: int,
        chart_max_h: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardPage")

        self.bundle = DashboardBundle(
            input_panel=InputPanel(),
            table=TableWidget(),
            chart=ChartWidget(),
            summary_label=QLabel(""),
            summary_caption=QLabel(""),
            cash_summary_label=QLabel(""),
            cash_summary_caption=QLabel(""),
            hint_label=QLabel(
                "Enter 保存 ｜ Ctrl+A 全选 ｜ Esc 清空 ｜ "
                "支持 K/M/B 后缀（如 1.5K = 1,500）"
            ),
        )
        self.bundle.summary_label.setObjectName("summaryLabel")
        self.bundle.summary_label.setWordWrap(True)
        self.bundle.summary_caption.setObjectName("summaryCaption")
        self.bundle.cash_summary_label.setObjectName("cashSummaryLabel")
        self.bundle.cash_summary_label.setWordWrap(True)
        self.bundle.cash_summary_caption.setObjectName("cashSummaryCaption")
        self.bundle.hint_label.setObjectName("hintLabel")

        self._build_layout(today, chart_min_h, chart_max_h)

    # ── 布局装配 ────────────────────────────────────────

    def _build_layout(self, today: str, chart_min_h: int, chart_max_h: int) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(0)

        # 标题栏（简化版：只保留标题 + 今日未录入提醒）
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel("Delta Force Dashboard")
        self.title_label.setObjectName("titleLabel")
        title_layout.addWidget(self.title_label)

        self.today_status_label = QLabel("今日未录入")
        self.today_status_label.setObjectName("todayStatusLabel")
        title_layout.addWidget(self.today_status_label)

        title_layout.addStretch()
        layout.addWidget(title_bar)

        # 日期（U-07：与标题同侧左对齐，消除「标题左、日期居中」的轴线错位）
        self.date_label = QLabel(today)
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addSpacing(4)
        layout.addWidget(self.date_label)
        layout.addSpacing(12)

        # 顶部区域（U-01）：输入卡（左，限宽 520）+ KPI 磁贴卡（右，吃剩余空间）
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(12)

        input_card = _card_frame()
        input_card.setMaximumWidth(520)  # 限宽：宽窗口下输入框不再无限横向拉伸（U-01）
        input_card_layout = QVBoxLayout(input_card)
        input_card_layout.setContentsMargins(10, 8, 10, 8)
        input_card_layout.addWidget(self.bundle.input_panel)
        top_bar_layout.addWidget(input_card, 0)

        # KPI 磁贴卡（总盈亏 / 现金总变化）——大数字（summary_style 22px 信号色）
        # + 小字说明（caption），与输入卡并排，成为页面的读数锚点（U-01）。
        kpi_card = _card_frame()
        kcl = QVBoxLayout(kpi_card)
        kcl.setContentsMargins(14, 10, 14, 10)
        kcl.setSpacing(6)
        for caption, value in (
            (self.bundle.summary_caption, self.bundle.summary_label),
            (self.bundle.cash_summary_caption, self.bundle.cash_summary_label),
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
        table_card = _card_frame()
        tcl = QVBoxLayout(table_card)
        tcl.setContentsMargins(10, 8, 10, 8)
        tcl.addWidget(self.bundle.table)
        layout.addWidget(table_card, 1)
        layout.addSpacing(8)

        # 折线图固定小卡片（H-01 语义）：不随窗口扩张，为表格全量展示让位；
        # 高度区间按屏幕可用空间自适应（_window_preset，U-09 方案 A）
        chart_card = _card_frame()
        ccl = QVBoxLayout(chart_card)
        ccl.setContentsMargins(10, 8, 10, 8)
        ccl.addWidget(self.bundle.chart)
        self.bundle.chart.setMinimumHeight(chart_min_h)
        self.bundle.chart.setMaximumHeight(chart_max_h)
        layout.addWidget(chart_card, 0)
        layout.addSpacing(8)

        # 底部提示栏
        layout.addWidget(self.bundle.hint_label)

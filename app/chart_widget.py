"""
图表渲染模块：pyqtgraph 双 Y 轴曲线图（单坐标系）。

- 仓库价值（总收益）— 左 Y 轴，琥珀色实线
- 现金（子项）— 右 Y 轴，青色虚线
- 双曲线共享同一 PlotWidget 与 X 轴（副 ViewBox 经 setXLink + linkToView 联动），
  各自独立 Y 轴量纲——避免现金量级远小于仓库时被压成直线
- hover 共享竖线 + 每系列一个彩色数值标签（按所属 ViewBox 顶部堆叠定位）
- 右键菜单 → 导出 PNG

设计决策：O-C2 原型（throwaway 分支 prototype/chart-merge）验证方案 B（双 Y 轴）
为唯一「两线清晰且不丢绝对值」的合并方案，落地见 ADR-0002。样式对齐原型评审
修正版（提交 0559537）：无填充区域、hover 标签按所属 ViewBox 定位（跨轴高度
不可比，标签叠放只显数值不比较线段）。
"""

from __future__ import annotations

__all__ = ["ChartWidget", "ChartSeries", "ChartState", "adaptive_range"]

from dataclasses import dataclass, field
from datetime import datetime

import pyqtgraph as pg
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QResizeEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from app.theme import get_color
from formatting import format_compact, format_short_date


class KMBAxisItem(pg.AxisItem):
    """自定义 Y 轴，将数值显示为 K/M/B 财务单位。"""

    def tickStrings(self, values, scale, spacing):
        return [format_compact(v) for v in values]


@dataclass(frozen=True)
class ChartSeries:
    """图表中一条序列的只读状态。"""
    name: str
    data_points: int
    y_range: tuple[float, float]


@dataclass(frozen=True)
class ChartState:
    """图表渲染层只读状态快照。

    测试断言 chart.state 而非私有字段，渲染层内部重构不影响测试。
    """
    series: list[ChartSeries] = field(default_factory=list)
    axis_count: int = 0


def adaptive_range(values: list[float]) -> tuple[float, float]:
    """计算自适应 Y 轴范围（纯函数，可直接单测）。

    返回 (ymin, ymax)，保证数据点在轴范围内有适当边距。
    空列表返回 (0.0, 1.0)。
    """
    if not values:
        return 0.0, 1.0
    lo, hi = min(values), max(values)
    rng = hi - lo
    if rng == 0:
        m = max(abs(lo) * 0.05, 1.0)
        return lo - m, hi + m
    return lo - rng * 0.10, hi + rng * 0.08


class ChartWidget(QWidget):
    """单坐标系双 Y 轴曲线图 + PNG 导出。

    仓库价值（左轴）与现金（右轴）合并进同一个 PlotWidget：主 ViewBox 承载
    仓库序列，副 ViewBox（右轴）承载现金序列；副 ViewBox 经 setXLink +
    linkToView 与主 ViewBox 共享 X 轴，两个 Y 轴各自按自身量纲自适应。
    """

    # 系列配置（轴归属决定各子元素挂在哪个 ViewBox）
    _LEFT_SERIES = dict(
        label="仓库价值 (¥)",
        color_key="CHART_WAREHOUSE",
        style=Qt.PenStyle.SolidLine,
        symbol="s",
        legend_name="仓库价值（总收益）",
        hover_name="仓库价值",
    )
    _RIGHT_SERIES = dict(
        label="现金 (¥)",
        color_key="CHART_CASH",
        style=Qt.PenStyle.DashLine,
        symbol="o",
        legend_name="现金（子项）",
        hover_name="现金",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # 占位文字（含稀疏提示 overlay，不进入 layout）
        self._placeholder_label: QLabel | None = None

        # 子元素（惰性创建）
        self._plot_widget: pg.PlotWidget | None = None
        self._plot_item: pg.PlotItem | None = None
        self._right_vb: pg.ViewBox | None = None
        self._warehouse_curve: pg.PlotCurveItem | None = None
        self._cash_curve: pg.PlotCurveItem | None = None
        self._warehouse_endpoint: pg.TextItem | None = None
        self._cash_endpoint: pg.TextItem | None = None
        self._vline: pg.InfiniteLine | None = None
        self._hover_labels: list[pg.TextItem] = []
        self._hover_views: list[pg.ViewBox] = []   # 每个 hover 标签所属 ViewBox（定位坐标系）
        self._hover_series: list[dict] = []        # 每个 hover 标签所属系列配置（短名/颜色键）
        self._proxy = None

        # 缓存数据
        self._dates: list[str] = []
        self._warehouse_vals: list[float] = []
        self._cash_vals: list[float] = []
        self._created = False

        # 右键菜单
        self._menu: QMenu | None = None

    # ─── 公共接口 ────────────────────────────────────────

    def draw(self, records: list) -> None:
        """渲染或更新图表。记录 ≥ 2 → 双 Y 轴曲线，< 2 → 提示文字。"""
        n = len(records)

        if n >= 2:
            dates = [format_short_date(r[0]) for r in records]
            cash_vals = [r[1].cash for r in records]
            warehouse_vals = [r[1].warehouse for r in records]
            x = list(range(len(dates)))

            self._clear_placeholder()

            # 首次：创建 PlotWidget 及全部子元素
            if not self._created:
                self._create(x, warehouse_vals, cash_vals, dates)
                self._created = True
            else:
                self._update_data(x, warehouse_vals, cash_vals, dates)

            # O-06：数据过少时叠加提示，避免误读为图表损坏
            if 2 <= n <= 3:
                self._show_sparse_hint()
        else:
            self._clear_all()
            self._show_placeholder(n)

    @property
    def state(self) -> ChartState:
        """图表当前渲染状态（只读）。"""
        series = []
        if self._warehouse_curve is not None:
            x, y = self._warehouse_curve.getData()
            series.append(ChartSeries(
                name="warehouse",
                data_points=len(x) if x is not None else 0,
                y_range=(min(y), max(y)) if y is not None and len(y) > 0 else (0, 0),
            ))
        if self._cash_curve is not None:
            x, y = self._cash_curve.getData()
            series.append(ChartSeries(
                name="cash",
                data_points=len(x) if x is not None else 0,
                y_range=(min(y), max(y)) if y is not None and len(y) > 0 else (0, 0),
            ))
        return ChartState(
            series=series,
            axis_count=2,  # 双 Y 轴，ADR-0002
        )

    def apply_theme(self) -> None:
        """主题切换后增量更新颜色；无需销毁重建。"""
        if not self._created or self._plot_widget is None:
            return

        w_color = get_color(self._LEFT_SERIES["color_key"])
        c_color = get_color(self._RIGHT_SERIES["color_key"])
        chart_bg = get_color("CHART_BG")
        label_color = get_color("CHART_AXIS")
        grid_color = get_color("CHART_GRID")

        # 背景
        self._plot_widget.setBackground(chart_bg)

        # 曲线颜色（setData 是 pyqtgraph 中更新 pen/symbol 的唯一方式）
        if self._warehouse_curve is not None and self._warehouse_vals:
            self._warehouse_curve.setData(
                list(range(len(self._warehouse_vals))), self._warehouse_vals,
                pen=pg.mkPen(color=w_color, width=2.5, style=self._LEFT_SERIES["style"]),
                symbol=self._LEFT_SERIES["symbol"], symbolSize=6,
                symbolBrush=w_color, symbolPen=w_color,
            )
        if self._cash_curve is not None and self._cash_vals:
            self._cash_curve.setData(
                list(range(len(self._cash_vals))), self._cash_vals,
                pen=pg.mkPen(color=c_color, width=2.5, style=self._RIGHT_SERIES["style"]),
                symbol=self._RIGHT_SERIES["symbol"], symbolSize=6,
                symbolBrush=c_color, symbolPen=c_color,
            )

        # 轴标签与颜色
        if self._plot_item is not None:
            self._plot_item.getAxis("left").setLabel(
                self._LEFT_SERIES["label"], color=w_color
            )
            self._plot_item.getAxis("left").setPen(pg.mkPen(color=w_color))
            self._plot_item.getAxis("right").setLabel(
                self._RIGHT_SERIES["label"], color=c_color
            )
            self._plot_item.getAxis("right").setPen(pg.mkPen(color=c_color))
            self._plot_item.getAxis("bottom").setPen(pg.mkPen(color=grid_color))

        # 端点标注颜色
        if self._warehouse_endpoint is not None and self._warehouse_vals:
            self._warehouse_endpoint.setText(
                self._format_value(self._warehouse_vals[-1]), color=w_color
            )
        if self._cash_endpoint is not None and self._cash_vals:
            self._cash_endpoint.setText(
                self._format_value(self._cash_vals[-1]), color=c_color
            )

        # hover 竖线与标签颜色
        if self._vline is not None:
            self._vline.setPen(
                pg.mkPen(color=label_color, width=1, style=Qt.PenStyle.DashLine)
            )
        for label, s in zip(self._hover_labels, self._hover_series):
            label.setColor(get_color(s["color_key"]))
            label.fill = pg.mkBrush(chart_bg)

        # 图例文字色
        if self._plot_item is not None and self._plot_item.legend is not None:
            self._plot_item.legend.setLabelTextColor(label_color)

        # 强制重绘
        self._plot_widget.update()

    # ─── 内部方法 ────────────────────────────────────────

    def _create(self, x, warehouse_vals, cash_vals, dates) -> None:
        """从零创建 PlotWidget + 双 ViewBox + 全部子元素。"""
        self._dates = dates
        self._warehouse_vals = warehouse_vals
        self._cash_vals = cash_vals

        w_color = get_color(self._LEFT_SERIES["color_key"])
        c_color = get_color(self._RIGHT_SERIES["color_key"])
        chart_bg = get_color("CHART_BG")
        label_color = get_color("CHART_AXIS")
        grid_color = get_color("CHART_GRID")

        self._create_axes_and_viewbox(w_color, c_color, chart_bg, grid_color)
        self._create_curves(x, warehouse_vals, cash_vals, w_color, c_color)
        self._apply_axis_ranges(warehouse_vals, cash_vals, dates)
        self._create_legend(label_color)
        self._create_hover_labels(w_color, c_color, chart_bg, label_color)
        self._setup_context_menu()
        self._bind_hover_signal()

    def _create_axes_and_viewbox(
        self, w_color: str, c_color: str, chart_bg: str, grid_color: str
    ) -> None:
        """创建左右轴 + PlotWidget + 双 ViewBox + 几何同步。"""
        # ── 左右轴 ──
        left_axis = KMBAxisItem(orientation="left")
        left_axis.setLabel(self._LEFT_SERIES["label"], color=w_color)
        left_axis.setPen(pg.mkPen(color=w_color))
        right_axis = KMBAxisItem(orientation="right")
        right_axis.setLabel(self._RIGHT_SERIES["label"], color=c_color)
        right_axis.setPen(pg.mkPen(color=c_color))

        # ── PlotWidget ──
        self._plot_widget = pg.PlotWidget(
            axisItems={"left": left_axis, "right": right_axis}
        )
        self._plot_widget.setBackground(chart_bg)
        self._layout.addWidget(self._plot_widget, 0)

        p1 = self._plot_widget.plotItem
        p1.showAxis("right")
        p1.getAxis("bottom").setPen(pg.mkPen(color=grid_color))
        self._plot_item = p1

        # 网格策略（G-02 修正）：双 Y 轴关闭全部网格，只靠标签承当读数参考
        p1.getAxis("left").setGrid(False)
        p1.getAxis("right").setGrid(False)
        p1.getAxis("bottom").setGrid(False)

        # ── 副 ViewBox（现金）：共享 X，独立 Y ──
        p2 = pg.ViewBox()
        p1.scene().addItem(p2)
        p1.getAxis("right").linkToView(p2)
        p2.setXLink(p1)

        def _sync() -> None:
            if p1.vb is None:
                return
            p2.setGeometry(p1.vb.sceneBoundingRect())
            p2.linkedViewChanged(p1.vb, p2.XAxis)

        p1.vb.sigResized.connect(_sync)
        _sync()
        self._right_vb = p2

    def _create_curves(
        self, x, warehouse_vals, cash_vals, w_color: str, c_color: str
    ) -> None:
        """创建仓库和现金曲线 + 末端端点标签。"""
        p1 = self._plot_item
        p2 = self._right_vb

        # ── 仓库序列（主 ViewBox / 左轴）──
        self._warehouse_curve = pg.PlotCurveItem(
            x, warehouse_vals,
            pen=pg.mkPen(color=w_color, width=2.5, style=self._LEFT_SERIES["style"]),
            symbol=self._LEFT_SERIES["symbol"], symbolSize=6,
            symbolBrush=w_color, symbolPen=w_color,
        )
        p1.addItem(self._warehouse_curve)

        self._warehouse_endpoint = pg.TextItem(
            text=self._format_value(warehouse_vals[-1]),
            color=w_color, anchor=(0, 0.5),
        )
        self._warehouse_endpoint.setPos(x[-1], warehouse_vals[-1])
        p1.addItem(self._warehouse_endpoint)

        # ── 现金序列（副 ViewBox / 右轴）──
        self._cash_curve = pg.PlotCurveItem(
            x, cash_vals,
            pen=pg.mkPen(color=c_color, width=2.5, style=self._RIGHT_SERIES["style"]),
            symbol=self._RIGHT_SERIES["symbol"], symbolSize=6,
            symbolBrush=c_color, symbolPen=c_color,
        )
        p2.addItem(self._cash_curve)

        self._cash_endpoint = pg.TextItem(
            text=self._format_value(cash_vals[-1]),
            color=c_color, anchor=(0, 0.5),
        )
        self._cash_endpoint.setPos(x[-1], cash_vals[-1])
        p2.addItem(self._cash_endpoint)

    def _apply_axis_ranges(
        self, warehouse_vals, cash_vals, dates
    ) -> None:
        """设置 Y 轴自适应范围 + X 轴日期刻度。"""
        self._plot_item.setYRange(*adaptive_range(warehouse_vals))
        self._right_vb.setYRange(*adaptive_range(cash_vals))
        self._plot_item.getAxis("bottom").setTicks([list(enumerate(dates))])

    def _create_legend(self, label_color: str) -> None:
        """创建图例（副 ViewBox 项目需显式 addItem）。"""
        p1 = self._plot_item
        legend = p1.addLegend(offset=(10, 10), labelTextColor=label_color)
        legend.addItem(self._warehouse_curve, self._LEFT_SERIES["legend_name"])
        legend.addItem(self._cash_curve, self._RIGHT_SERIES["legend_name"])

    def _create_hover_labels(
        self, w_color: str, c_color: str, chart_bg: str, label_color: str
    ) -> None:
        """创建 hover 竖线 + 双数值标签（各自坐标系，随各自曲线）。"""
        p1 = self._plot_item
        p2 = self._right_vb

        self._vline = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color=label_color, width=1, style=Qt.PenStyle.DashLine),
        )
        self._vline.setVisible(False)
        p1.addItem(self._vline)

        w_hover = pg.TextItem("", color=w_color, fill=chart_bg)
        w_hover.setVisible(False)
        p1.addItem(w_hover)
        c_hover = pg.TextItem("", color=c_color, fill=chart_bg)
        c_hover.setVisible(False)
        p2.addItem(c_hover)
        self._hover_labels = [w_hover, c_hover]
        self._hover_views = [p1.vb, p2]
        self._hover_series = [self._LEFT_SERIES, self._RIGHT_SERIES]

    def _bind_hover_signal(self) -> None:
        """绑定 hover 鼠标移动信号。"""
        self._proxy = pg.SignalProxy(
            self._plot_item.scene().sigMouseMoved,
            rateLimit=60, slot=self._on_mouse_moved,
        )

    def _update_data(self, x, warehouse_vals, cash_vals, dates) -> None:
        """原地更新曲线数据（不重建 PlotWidget / 双 ViewBox）。"""
        if self._plot_widget is None:
            return
        self._dates = dates
        self._warehouse_vals = warehouse_vals
        self._cash_vals = cash_vals

        # 更新曲线数据（FillBetweenItem 通过 sigPlotChanged 自动跟随）
        if self._warehouse_curve is not None:
            self._warehouse_curve.setData(x, warehouse_vals)
        if self._cash_curve is not None:
            self._cash_curve.setData(x, cash_vals)

        # 更新端点数值标注
        if self._warehouse_endpoint is not None and warehouse_vals:
            self._warehouse_endpoint.setText(self._format_value(warehouse_vals[-1]))
            self._warehouse_endpoint.setPos(x[-1], warehouse_vals[-1])
        if self._cash_endpoint is not None and cash_vals:
            self._cash_endpoint.setText(self._format_value(cash_vals[-1]))
            self._cash_endpoint.setPos(x[-1], cash_vals[-1])

        # 更新 Y 轴范围（各自量纲）与 X 轴标签
        if self._plot_item is not None:
            self._plot_item.setYRange(*adaptive_range(warehouse_vals))
            self._plot_item.getAxis("bottom").setTicks([list(enumerate(dates))])
        if self._right_vb is not None:
            self._right_vb.setYRange(*adaptive_range(cash_vals))

    def _on_mouse_moved(self, evt) -> None:
        """鼠标移动时显示竖线 + 每系列一个彩色数值标签。

        标签按所属 ViewBox 的 top 做堆叠定位（跨轴高度不可比，不贴数据点），
        文案为「系列短名 + 值」——对齐原型评审修正版（0559537）。
        """
        if not self._dates or self._plot_item is None:
            return

        pos = evt[0]
        vb = self._plot_item.vb
        if vb is None:
            return

        mouse_x = vb.mapSceneToView(pos).x()
        n = len(self._dates)

        # 鼠标离开数据范围时隐藏
        if mouse_x < -0.5 or mouse_x > n - 0.5:
            if self._vline is not None:
                self._vline.setVisible(False)
            for label in self._hover_labels:
                label.setVisible(False)
            return

        idx = max(0, min(n - 1, round(mouse_x)))
        idx = min(idx, len(self._warehouse_vals) - 1, len(self._cash_vals) - 1)

        if self._vline is not None:
            self._vline.setPos(idx)
            self._vline.setVisible(True)

        vals = (self._warehouse_vals[idx], self._cash_vals[idx])
        # 各自量纲 + 极端值下 scale 归零的兜底（与原型 _attach_crosshair 同款 span）
        for j, (label, series, view) in enumerate(
            zip(self._hover_labels, self._hover_series, self._hover_views)
        ):
            if view is None:
                label.setVisible(False)
                continue
            ymax = view.viewRange()[1][1]
            span = max(abs(ymax), 1.0)
            label.setText(
                f"{series['hover_name']} {self._format_value(vals[j])}",
                color=get_color(series["color_key"]),
            )
            label.setPos(idx, ymax - span * (0.06 + 0.10 * j))
            label.setVisible(True)

    @staticmethod
    def _format_value(v: float) -> str:
        """格式化图表数值为紧凑 K/M/B（与 Y 轴共用 format_compact，带 ¥ 前缀）。"""
        return format_compact(v, prefix="¥")

    def _show_sparse_hint(self) -> None:
        """n=2~3 时在图表区域叠加半透明提示文字（不触碰曲线与交互）。

        与 `_show_placeholder` 共用 `_placeholder_label` / `_clear_placeholder`
        生命周期；label 不进入 layout，作为顶层子控件覆盖图表，并标记
        WA_TransparentForMouseEvents 让鼠标事件透传给图表。
        """
        self._clear_placeholder()
        hint = QLabel("数据较少，需更多数据以显示趋势", self)
        hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet(
            "background-color: rgba(0, 0, 0, 35);"
            f"color: {get_color('FG_MUTED')};"
            "font-size: 12px;"
        )
        hint.setGeometry(self.rect())
        hint.raise_()
        self._placeholder_label = hint

    def resizeEvent(self, event: QResizeEvent) -> None:
        """overlay 提示不参与 layout，需手动跟随 widget 尺寸。"""
        super().resizeEvent(event)
        if (
            self._placeholder_label is not None
            and self._layout.indexOf(self._placeholder_label) == -1
        ):
            self._placeholder_label.setGeometry(self.rect())

    def _show_placeholder(self, n: int) -> None:
        self._clear_placeholder()
        msg = (
            "暂无数据\n请在上方输入并保存今日数据"
            if n == 0
            else "至少需要两天数据才能绘制曲线\n请继续录入数据"
        )
        self._placeholder_label = QLabel(msg)
        self._placeholder_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        self._placeholder_label.setStyleSheet(
            f"color: {get_color('FG_MUTED')}; font-size: 10px;"
        )
        self._layout.addWidget(self._placeholder_label)

    def _clear_placeholder(self) -> None:
        if self._placeholder_label is not None:
            self._layout.removeWidget(self._placeholder_label)
            self._placeholder_label.deleteLater()
            self._placeholder_label = None

    def _setup_context_menu(self) -> None:
        """为 PlotWidget 绑定右键菜单。"""
        if self._plot_widget is None:
            return
        self._menu = QMenu(self)

        export_action = QAction("💾 导出为 PNG", self)
        export_action.triggered.connect(self.export_png)
        self._menu.addAction(export_action)

        self._plot_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._plot_widget.customContextMenuRequested.connect(
            self._show_context_menu
        )

    def _show_context_menu(self, pos: QPoint) -> None:
        if self._menu is not None and self._plot_widget is not None:
            self._menu.exec(self._plot_widget.mapToGlobal(pos))

    def export_png(self) -> None:
        """导出当前图表为 PNG。"""
        if self._plot_widget is None:
            QMessageBox.information(self, "提示", "暂无图表可导出")
            return

        today = datetime.now().strftime("%Y-%m-%d")
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出图表为 PNG",
            f"收益曲线_{today}.png",
            "PNG 图片 (*.png);;所有文件 (*.*)",
        )
        if not file_path:
            return

        try:
            screenshot = self.grab()
            screenshot.save(file_path, "PNG")
            QMessageBox.information(
                self, "导出成功", f"图表已保存至:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "导出失败", f"无法保存图表:\n{e}"
            )

    def _clear_all(self) -> None:
        """销毁图表及占位。"""
        self._clear_placeholder()

        if self._plot_widget is not None:
            self._layout.removeWidget(self._plot_widget)
            self._plot_widget.deleteLater()
            self._plot_widget = None

        self._plot_item = None
        self._right_vb = None
        self._warehouse_curve = None
        self._cash_curve = None
        self._warehouse_endpoint = None
        self._cash_endpoint = None
        self._vline = None
        self._hover_labels = []
        self._hover_views = []
        self._hover_series = []
        self._proxy = None
        self._created = False
        self._dates = []
        self._warehouse_vals = []
        self._cash_vals = []
        self._menu = None

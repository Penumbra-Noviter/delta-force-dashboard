"""
图表渲染模块：pyqtgraph 双曲线图。

- 上图：仓库价值（总收益）— 琥珀色实线
- 下图：现金（子项）— 蓝色虚线
- 两图共享 X 轴，各自独立 Y 轴
- 右键菜单 → 导出 PNG
"""

from __future__ import annotations

__all__ = ["ChartWidget"]

import os
from datetime import datetime

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.theme import get_color, get_theme
from formatting import format_compact, format_short_date


class KMBAxisItem(pg.AxisItem):
    """自定义 Y 轴，将数值显示为 K/M/B 财务单位。"""

    def tickStrings(self, values, scale, spacing):
        return [format_compact(v) for v in values]


# ═══════════════════════════════════════════════════════════
# 内部辅助：单个图表面板
# ═══════════════════════════════════════════════════════════

class _ChartPanel(QWidget):
    """管理单个图表面板（一条曲线 + 填充区域 + hover 交互 + 端点标注）。

    封装一个 PlotWidget 及其全部子元素，消除 ChartWidget 中
    top/bottom 对称实例变量带来的代码重复。
    """

    def __init__(
        self,
        label: str,                 # Y 轴标签，如 "仓库价值 (¥)"
        color_key: str,             # 主题色板键，如 "CHART_WAREHOUSE"
        line_style: Qt.PenStyle = Qt.PenStyle.SolidLine,
        symbol: str = "s",          # 标记样式："s"=方块, "o"=圆点
        series_name: str = "",      # 图例名称
        show_x_axis: bool = False,  # 是否显示 X 轴标签（底部面板才显示日期）
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._color_key = color_key
        self._line_style = line_style
        self._symbol = symbol
        self._series_name = series_name
        self._show_x_axis = show_x_axis

        # 子元素（惰性创建）
        self._plot_widget: pg.PlotWidget | None = None
        self._curve: pg.PlotCurveItem | None = None
        self._fill_curve: pg.PlotCurveItem | None = None
        self._fill_item: pg.FillBetweenItem | None = None
        self._endpoint_label: pg.TextItem | None = None
        self._vline: pg.InfiniteLine | None = None
        self._hover_label: pg.TextItem | None = None
        self._proxy = None

        # 缓存数据
        self._dates: list[str] = []
        self._values: list[float] = []
        self._created = False

        # 布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    # ─── 公共接口 ────────────────────────────────────────

    def draw(self, x: list[int], values: list[float], dates: list[str]) -> None:
        """首次渲染或更新数据。

        首次调用时创建 PlotWidget 及其子元素；
        后续调用仅更新数据（不重建）。
        """
        self._dates = dates
        self._values = values

        if not self._created:
            self._create(x, values)
            self._created = True
        else:
            self._update_data(x, values)

    def update_theme(self) -> None:
        """主题切换后增量更新颜色，不重建。"""
        if not self._created or self._plot_widget is None:
            return

        color = get_color(self._color_key)
        chart_bg = get_color("CHART_BG")
        label_color = get_color("CHART_AXIS")

        # 背景
        self._plot_widget.setBackground(chart_bg)

        # 曲线颜色（setData 是 pyqtgraph 中更新 pen/symbol 的唯一方式）
        if self._curve is not None and self._values:
            _x = list(range(len(self._values)))
            self._curve.setData(
                _x, self._values,
                pen=pg.mkPen(color=color, width=2.5, style=self._line_style),
                symbol=self._symbol, symbolSize=6,
                symbolBrush=color, symbolPen=color,
            )

        # 填充区域颜色
        if self._fill_item is not None:
            self._fill_item.setBrush(pg.mkBrush(color=color, alpha=50))

        # 左轴标签与颜色
        left_axis = self._plot_widget.getAxis("left")
        left_axis.setLabel(self._label, color=color)
        left_axis.setPen(pg.mkPen(color=color))

        # 网格颜色
        grid_color = get_color("CHART_GRID")
        self._plot_widget.getAxis("bottom").setPen(pg.mkPen(color=grid_color))
        self._plot_widget.getAxis("left").setPen(pg.mkPen(color=grid_color))

        # 端点标注颜色
        if self._endpoint_label is not None and self._values:
            self._endpoint_label.setText(
                self._format_value(self._values[-1]), color=color
            )

        # hover 竖线与标签颜色
        if self._vline is not None:
            self._vline.setPen(
                pg.mkPen(color=label_color, width=1, style=Qt.PenStyle.DashLine)
            )
        if self._hover_label is not None:
            self._hover_label.setColor(label_color)
            self._hover_label.fill = pg.mkBrush(chart_bg)

        # 强制重绘
        self._plot_widget.update()

    def clear_panel(self) -> None:
        """销毁内部组件并重置状态。"""
        if self._plot_widget is not None:
            self._layout.removeWidget(self._plot_widget)
            self._plot_widget.deleteLater()
            self._plot_widget = None

        self._curve = None
        self._fill_curve = None
        self._fill_item = None
        self._endpoint_label = None
        self._vline = None
        self._hover_label = None
        self._proxy = None
        self._created = False
        self._dates = []
        self._values = []

    @property
    def plot_widget(self) -> pg.PlotWidget | None:
        return self._plot_widget

    @property
    def values(self) -> list[float]:
        return self._values

    # ─── 内部方法 ────────────────────────────────────────

    def _create(self, x: list[int], values: list[float]) -> None:
        """从零创建 PlotWidget 及其子元素。"""
        color = get_color(self._color_key)
        chart_bg = get_color("CHART_BG")
        label_color = get_color("CHART_AXIS")

        # ── 左轴 ──
        left_axis = KMBAxisItem(orientation="left")
        left_axis.setLabel(self._label, color=color)
        left_axis.setPen(pg.mkPen(color=color))

        # ── PlotWidget ──
        self._plot_widget = pg.PlotWidget(axisItems={"left": left_axis})
        self._plot_widget.setBackground(chart_bg)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.5)

        if not self._show_x_axis:
            self._plot_widget.getAxis("bottom").setStyle(showValues=False)

        self._layout.addWidget(self._plot_widget)

        # ── 曲线 ──
        self._curve = pg.PlotCurveItem(
            x, values,
            pen=pg.mkPen(color=color, width=2.5, style=self._line_style),
            symbol=self._symbol,
            symbolSize=6,
            symbolBrush=color,
            symbolPen=color,
            name=self._series_name if self._series_name else None,
        )
        self._plot_widget.addItem(self._curve)

        # ── 填充区域 ──
        self._fill_curve = pg.PlotCurveItem(x, values)
        self._fill_item = pg.FillBetweenItem(
            self._curve, self._fill_curve,
            brush=pg.mkBrush(color=color, alpha=50),
        )
        self._plot_widget.addItem(self._fill_item)

        # ── 端点数值标注 ──
        self._endpoint_label = pg.TextItem(
            text=self._format_value(values[-1]),
            color=color,
            anchor=(0, 0.5),
        )
        self._endpoint_label.setPos(x[-1], values[-1])
        self._plot_widget.addItem(self._endpoint_label)

        # ── hover 竖线 + 数值标签 ──
        self._vline = pg.InfiniteLine(
            angle=90, movable=False,
            pen=pg.mkPen(color=label_color, width=1, style=Qt.PenStyle.DashLine),
        )
        self._vline.setVisible(False)
        self._plot_widget.addItem(self._vline)

        self._hover_label = pg.TextItem(
            text="", color=label_color, fill=chart_bg,
        )
        self._hover_label.setVisible(False)
        self._plot_widget.addItem(self._hover_label)

        # ── Y 轴自适应 ──
        self._set_adaptive_ylim(self._plot_widget, values)

        # ── 图例 ──
        if self._series_name:
            self._plot_widget.addLegend(
                offset=(10, 10), labelTextColor=label_color,
            )

        # ── hover 信号绑定 ──
        self._proxy = pg.SignalProxy(
            self._plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )

    def _update_data(self, x: list[int], values: list[float]) -> None:
        """原地更新曲线数据（不重建 PlotWidget / FillBetweenItem）。"""
        if self._plot_widget is None:
            return

        # 更新曲线数据（FillBetweenItem 通过 sigPlotChanged 自动跟随）
        if self._curve is not None:
            self._curve.setData(x, values)
        if self._fill_curve is not None:
            self._fill_curve.setData(x, values)

        # 更新端点数值标注
        if self._endpoint_label is not None and values:
            self._endpoint_label.setText(self._format_value(values[-1]))
            self._endpoint_label.setPos(x[-1], values[-1])

        # 更新 Y 轴范围
        self._set_adaptive_ylim(self._plot_widget, values)

        # 更新 X 轴标签（仅底部面板）
        if self._show_x_axis:
            axis = self._plot_widget.getAxis("bottom")
            axis.setTicks([list(enumerate(self._dates))])

    def _on_mouse_moved(self, evt) -> None:
        """鼠标移动时显示最近数据点的竖线 + 数值标签。"""
        if not self._dates or self._plot_widget is None:
            return

        pos = evt[0]
        vb = self._plot_widget.plotItem.vb
        if vb is None:
            return

        mouse_point = vb.mapSceneToView(pos)
        mouse_x = mouse_point.x()
        n = len(self._dates)

        # 鼠标离开数据范围时隐藏
        if mouse_x < -0.5 or mouse_x > n - 0.5:
            if self._vline is not None:
                self._vline.setVisible(False)
            if self._hover_label is not None:
                self._hover_label.setVisible(False)
            return

        idx = max(0, min(n - 1, round(mouse_x)))
        color = get_color(self._color_key)

        if self._vline is not None:
            self._vline.setPos(idx)
            self._vline.setVisible(True)
        if self._hover_label is not None:
            self._hover_label.setText(
                f"{self._dates[idx]}  {self._format_value(self._values[idx])}",
                color=color,
            )
            self._hover_label.setPos(idx, self._values[idx])
            self._hover_label.setVisible(True)

    @staticmethod
    def _format_value(v: float) -> str:
        """格式化图表数值为紧凑 K/M/B（与 Y 轴共用 format_compact，带 ¥ 前缀）。"""
        return format_compact(v, prefix="¥")

    @staticmethod
    def _set_adaptive_ylim(plot_widget: pg.PlotWidget, values: list) -> None:
        """自适应 Y 轴范围（底部留 10%，顶部留 8%）。"""
        lo, hi = min(values), max(values)
        rng = hi - lo
        if rng == 0:
            m = max(abs(lo) * 0.05, 1.0)
            plot_widget.setYRange(lo - m, hi + m)
        else:
            plot_widget.setYRange(lo - rng * 0.10, hi + rng * 0.08)


# ═══════════════════════════════════════════════════════════
# 双曲线图容器
# ═══════════════════════════════════════════════════════════

class ChartWidget(QWidget):
    """pyqtgraph 双曲线图 + PNG 导出。

    内部委托给两个 _ChartPanel 实例：
    - 上图：仓库价值
    - 下图：现金
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # 占位文字
        self._placeholder_label: QLabel | None = None

        # 两个图表面板（惰性创建）
        self._top: _ChartPanel | None = None
        self._bottom: _ChartPanel | None = None

        # 右键菜单
        self._menu: QMenu | None = None

    def draw(self, records: list) -> None:
        """渲染或更新图表。记录 ≥ 2 → 双图模式，< 2 → 提示文字。"""
        n = len(records)

        if n >= 2:
            dates = [format_short_date(r[0]) for r in records]
            cash_vals = [r[1].cash for r in records]
            warehouse_vals = [r[1].warehouse for r in records]
            x = list(range(len(dates)))

            self._clear_placeholder()

            # 首次：创建两个面板
            if self._top is None:
                self._top = _ChartPanel(
                    label="仓库价值 (¥)",
                    color_key="CHART_WAREHOUSE",
                    line_style=Qt.PenStyle.SolidLine,
                    symbol="s",
                    series_name="仓库价值（总收益）",
                    show_x_axis=False,
                )
                self._bottom = _ChartPanel(
                    label="现金 (¥)",
                    color_key="CHART_CASH",
                    line_style=Qt.PenStyle.DashLine,
                    symbol="o",
                    series_name="现金（子项）",
                    show_x_axis=True,
                )

                self._layout.addWidget(self._top, 1)
                self._layout.addWidget(self._bottom, 1)

                # 右键菜单
                self._setup_context_menu()

            # 委托绘制
            self._top.draw(x, warehouse_vals, dates)
            self._bottom.draw(x, cash_vals, dates)
        else:
            self._clear_all()
            self._show_placeholder(n)

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
        """为两个 PlotWidget 绑定右键菜单。"""
        self._menu = QMenu(self)

        export_action = QAction("💾 导出为 PNG", self)
        export_action.triggered.connect(self.export_png)
        self._menu.addAction(export_action)

        for panel in (self._top, self._bottom):
            if panel is None or panel.plot_widget is None:
                continue
            pw = panel.plot_widget
            pw.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            pw.customContextMenuRequested.connect(
                lambda pos, src=pw: self._show_context_menu(pos, src)
            )

    def _show_context_menu(self, pos: QPoint, source: QWidget) -> None:
        if self._menu is not None:
            self._menu.exec(source.mapToGlobal(pos))

    def export_png(self) -> None:
        """导出当前图表为 PNG。"""
        if self._top is None or self._top.plot_widget is None:
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

        if self._top is not None:
            self._layout.removeWidget(self._top)
            self._top.clear_panel()
            self._top.deleteLater()
            self._top = None

        if self._bottom is not None:
            self._layout.removeWidget(self._bottom)
            self._bottom.clear_panel()
            self._bottom.deleteLater()
            self._bottom = None

        self._menu = None

    def apply_theme(self) -> None:
        """主题切换后增量更新颜色；无需销毁重建。"""
        if self._top is not None:
            self._top.update_theme()
        if self._bottom is not None:
            self._bottom.update_theme()

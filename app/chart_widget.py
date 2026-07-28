"""
图表渲染模块：pyqtgraph 双曲线图。

- 上图：仓库价值（总收益）— 琥珀色实线
- 下图：现金（子项）— 蓝色虚线
- 两图共享 X 轴，各自独立 Y 轴
- 右键菜单 → 导出 PNG
"""

from __future__ import annotations

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


class KMBAxisItem(pg.AxisItem):
    """自定义 Y 轴，将数值显示为 K/M/B 财务单位。"""

    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            if v >= 1e9:
                strings.append(f"{v / 1e9:.1f}B")
            elif v >= 1e6:
                strings.append(f"{v / 1e6:.1f}M")
            elif v >= 1e3:
                strings.append(f"{v / 1e3:.1f}K")
            else:
                strings.append(f"{v:.0f}")
        return strings


class ChartWidget(QWidget):
    """pyqtgraph 双曲线图 + PNG 导出。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._theme = "light"
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # 状态
        self._chart_created = False
        self._placeholder_label: QLabel | None = None
        self._top_container: QWidget | None = None
        self._bottom_container: QWidget | None = None
        self._plot_widget_top: pg.PlotWidget | None = None
        self._plot_widget_bottom: pg.PlotWidget | None = None
        self._line_warehouse: pg.PlotDataItem | None = None
        self._line_cash: pg.PlotDataItem | None = None
        self._fill_warehouse: pg.FillBetweenItem | None = None
        self._fill_cash: pg.FillBetweenItem | None = None
        self._curve_top: pg.PlotCurveItem | None = None
        self._curve_bottom: pg.PlotCurveItem | None = None
        # 填充边界曲线（持久化避免重建 FillBetweenItem）
        self._fill_curve_top: pg.PlotCurveItem | None = None
        self._fill_curve_bottom: pg.PlotCurveItem | None = None

    def draw(self, records: list) -> None:
        """渲染或更新图表。记录 ≥ 2 → 双图模式，< 2 → 提示文字。"""
        n = len(records)

        if n >= 2:
            if not self._chart_created:
                self._clear_all()
                self._create_chart(records)
                self._chart_created = True
            else:
                self._update_chart(records)
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

    def _create_chart(self, records: list) -> None:
        """从零创建上下双图 PlotWidget。"""
        self._clear_placeholder()

        dates = [r[0][-5:] for r in records]
        cash_vals = [r[1].cash for r in records]
        warehouse_vals = [r[1].warehouse for r in records]
        x = list(range(len(dates)))

        cw_color = get_color("CHART_WAREHOUSE")
        cc_color = get_color("CHART_CASH")
        chart_bg = get_color("CHART_BG")
        label_color = get_color("CHART_AXIS")

        # ── 上图：仓库价值 ──
        self._top_container = QWidget()
        w_layout = QVBoxLayout(self._top_container)
        w_layout.setContentsMargins(0, 0, 0, 0)
        w_layout.setSpacing(0)

        left_axis_top = KMBAxisItem(orientation="left")
        left_axis_top.setLabel("仓库价值 (¥)", color=cw_color)
        left_axis_top.setPen(pg.mkPen(color=cw_color))

        self._plot_widget_top = pg.PlotWidget(axisItems={"left": left_axis_top})
        self._plot_widget_top.setBackground(chart_bg)
        self._plot_widget_top.showGrid(x=True, y=True, alpha=0.5)
        self._plot_widget_top.getAxis("bottom").setStyle(showValues=False)

        # 仓库曲线
        self._curve_top = pg.PlotCurveItem(
            x, warehouse_vals,
            pen=pg.mkPen(color=cw_color, width=2.5),
            symbol="s",
            symbolSize=6,
            symbolBrush=cw_color,
            symbolPen=cw_color,
            name="仓库价值（总收益）",
        )
        self._plot_widget_top.addItem(self._curve_top)

        # 填充区域
        self._fill_curve_top = pg.PlotCurveItem(x, warehouse_vals)
        self._fill_warehouse = pg.FillBetweenItem(
            self._curve_top, self._fill_curve_top,
            brush=pg.mkBrush(color=cw_color, alpha=50),
        )
        self._plot_widget_top.addItem(self._fill_warehouse)

        # Y 轴自适应
        self._set_adaptive_ylim(self._plot_widget_top, warehouse_vals)

        # 图例
        self._plot_widget_top.addLegend(
            offset=(10, 10), labelTextColor=label_color,
        )

        w_layout.addWidget(self._plot_widget_top)
        self._layout.addWidget(self._top_container, 1)

        # ── 下图：现金 ──
        self._bottom_container = QWidget()
        c_layout = QVBoxLayout(self._bottom_container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(0)

        left_axis_bottom = KMBAxisItem(orientation="left")
        left_axis_bottom.setLabel("现金 (¥)", color=cc_color)
        left_axis_bottom.setPen(pg.mkPen(color=cc_color))

        self._plot_widget_bottom = pg.PlotWidget(axisItems={"left": left_axis_bottom})
        self._plot_widget_bottom.setBackground(chart_bg)
        self._plot_widget_bottom.showGrid(x=True, y=True, alpha=0.5)

        # 现金曲线
        self._curve_bottom = pg.PlotCurveItem(
            x, cash_vals,
            pen=pg.mkPen(color=cc_color, width=2.5, style=Qt.PenStyle.DashLine),
            symbol="o",
            symbolSize=6,
            symbolBrush=cc_color,
            symbolPen=cc_color,
            name="现金（子项）",
        )
        self._plot_widget_bottom.addItem(self._curve_bottom)

        # 填充区域
        self._fill_curve_bottom = pg.PlotCurveItem(x, cash_vals)
        self._fill_cash = pg.FillBetweenItem(
            self._curve_bottom, self._fill_curve_bottom,
            brush=pg.mkBrush(color=cc_color, alpha=50),
        )
        self._plot_widget_bottom.addItem(self._fill_cash)

        # Y 轴自适应
        self._set_adaptive_ylim(self._plot_widget_bottom, cash_vals)

        # X 轴日期
        axis_bottom = self._plot_widget_bottom.getAxis("bottom")
        axis_bottom.setTicks([list(enumerate(dates))])

        # 图例
        self._plot_widget_bottom.addLegend(
            offset=(10, 10), labelTextColor=label_color,
        )

        c_layout.addWidget(self._plot_widget_bottom)
        self._layout.addWidget(self._bottom_container, 1)

        # ── 右键菜单 ──
        self._setup_context_menu()

    def _update_chart(self, records: list) -> None:
        """原地更新数据（不重建 PlotWidget / FillBetweenItem）。"""
        if self._plot_widget_top is None or self._plot_widget_bottom is None:
            self._clear_all()
            self._create_chart(records)
            return

        dates = [r[0][-5:] for r in records]
        cash_vals = [r[1].cash for r in records]
        warehouse_vals = [r[1].warehouse for r in records]
        x = list(range(len(dates)))

        # 更新曲线数据（FillBetweenItem 通过 sigPlotChanged 自动跟随）
        if self._curve_top is not None:
            self._curve_top.setData(x, warehouse_vals)
        if self._fill_curve_top is not None:
            self._fill_curve_top.setData(x, warehouse_vals)
        if self._curve_bottom is not None:
            self._curve_bottom.setData(x, cash_vals)
        if self._fill_curve_bottom is not None:
            self._fill_curve_bottom.setData(x, cash_vals)

        # 更新 Y 轴范围
        self._set_adaptive_ylim(self._plot_widget_top, warehouse_vals)
        self._set_adaptive_ylim(self._plot_widget_bottom, cash_vals)

        # 更新 X 轴标签
        if self._plot_widget_bottom is not None:
            axis_bottom = self._plot_widget_bottom.getAxis("bottom")
            axis_bottom.setTicks([list(enumerate(dates))])

    def _set_adaptive_ylim(self, plot_widget: pg.PlotWidget, values: list) -> None:
        """自适应 Y 轴范围（底部留 10%，顶部留 8%）。"""
        lo, hi = min(values), max(values)
        rng = hi - lo
        if rng == 0:
            m = max(abs(lo) * 0.05, 1.0)
            plot_widget.setYRange(lo - m, hi + m)
        else:
            plot_widget.setYRange(lo - rng * 0.10, hi + rng * 0.08)

    def _setup_context_menu(self) -> None:
        """为两个 PlotWidget 绑定右键菜单。"""
        self._menu = QMenu(self)

        export_action = QAction("💾 导出为 PNG", self)
        export_action.triggered.connect(self.export_png)
        self._menu.addAction(export_action)

        if self._plot_widget_top is not None:
            self._plot_widget_top.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            self._plot_widget_top.customContextMenuRequested.connect(
                lambda pos: self._show_context_menu(pos, self._plot_widget_top)
            )

        if self._plot_widget_bottom is not None:
            self._plot_widget_bottom.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            self._plot_widget_bottom.customContextMenuRequested.connect(
                lambda pos: self._show_context_menu(pos, self._plot_widget_bottom)
            )

    def _show_context_menu(self, pos: QPoint, source: QWidget) -> None:
        self._menu.exec(source.mapToGlobal(pos))

    def export_png(self) -> None:
        """导出当前图表为 PNG。"""
        if self._plot_widget_top is None:
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
            # 用 exportImage 导出完整布局
            from PySide6.QtWidgets import QApplication

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

        if self._top_container is not None:
            self._layout.removeWidget(self._top_container)
            self._top_container.deleteLater()
            self._top_container = None

        if self._bottom_container is not None:
            self._layout.removeWidget(self._bottom_container)
            self._bottom_container.deleteLater()
            self._bottom_container = None

        self._chart_created = False
        self._plot_widget_top = None
        self._plot_widget_bottom = None
        self._curve_top = None
        self._curve_bottom = None
        self._fill_warehouse = None
        self._fill_cash = None

    def apply_theme(self) -> None:
        """主题切换后增量更新颜色；无需销毁重建图表。"""
        if not self._chart_created or self._plot_widget_top is None:
            # 图表尚未创建，标记需要在下次 draw() 时重建
            self._clear_all()
            return

        self._update_theme_colors()

    def _update_theme_colors(self) -> None:
        """增量更新图表颜色（曲线、填充、背景、轴）。"""
        cw_color = get_color("CHART_WAREHOUSE")
        cc_color = get_color("CHART_CASH")
        chart_bg = get_color("CHART_BG")
        label_color = get_color("CHART_AXIS")

        # ── 上图：仓库价值 ──
        if self._plot_widget_top is not None:
            self._plot_widget_top.setBackground(chart_bg)

            # 曲线颜色
            if self._curve_top is not None:
                self._curve_top.setPen(pg.mkPen(color=cw_color, width=2.5))
                self._curve_top.setSymbolPen(cw_color)
                self._curve_top.setSymbolBrush(cw_color)

            # 填充颜色
            if self._fill_warehouse is not None:
                self._fill_warehouse.setBrush(pg.mkBrush(color=cw_color, alpha=50))

            # 左轴颜色
            left_axis_top = self._plot_widget_top.getAxis("left")
            left_axis_top.setLabel("仓库价值 (¥)", color=cw_color)
            left_axis_top.setPen(pg.mkPen(color=cw_color))

            # 网格颜色
            grid_color = get_color("CHART_GRID")
            self._plot_widget_top.getAxis("bottom").setPen(pg.mkPen(color=grid_color))
            self._plot_widget_top.getAxis("left").setPen(pg.mkPen(color=grid_color))

        # ── 下图：现金 ──
        if self._plot_widget_bottom is not None:
            self._plot_widget_bottom.setBackground(chart_bg)

            # 曲线颜色
            if self._curve_bottom is not None:
                self._curve_bottom.setPen(pg.mkPen(color=cc_color, width=2.5, style=Qt.PenStyle.DashLine))
                self._curve_bottom.setSymbolPen(cc_color)
                self._curve_bottom.setSymbolBrush(cc_color)

            # 填充颜色
            if self._fill_cash is not None:
                self._fill_cash.setBrush(pg.mkBrush(color=cc_color, alpha=50))

            # 左轴颜色
            left_axis_bottom = self._plot_widget_bottom.getAxis("left")
            left_axis_bottom.setLabel("现金 (¥)", color=cc_color)
            left_axis_bottom.setPen(pg.mkPen(color=cc_color))

            # 网格颜色
            grid_color = get_color("CHART_GRID")
            self._plot_widget_bottom.getAxis("bottom").setPen(pg.mkPen(color=grid_color))
            self._plot_widget_bottom.getAxis("left").setPen(pg.mkPen(color=grid_color))

        # 强制重绘
        if self._plot_widget_top is not None:
            self._plot_widget_top.update()
        if self._plot_widget_bottom is not None:
            self._plot_widget_bottom.update()

"""
七日数据表格：PySide6 双栏布局。

左栏显示前4天数据，右栏显示后3天数据，减少滚动操作。
7 列：日期、现金、仓库（总收益）、较前日、收益率、盈亏标签、操作。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import get_color
from formatting import format_money
from calculator import DayRecord, ProfitCalculatorLogic

COLUMNS = ["日期", "现金", "仓库（总收益）", "较前日", "收益率", "盈亏", "操作"]
COL_WIDTHS = [80, 100, 110, 100, 80, 55, 120]
# Column indices
COL_DATE = 0
COL_CASH = 1
COL_WAREHOUSE = 2
COL_DIFF = 3
COL_RATE = 4
COL_PNL = 5
COL_ACTIONS = 6


class PnLBadge(QWidget):
    """盈亏标签 Badge：绿底"盈"/红底"亏"/灰底"—"。"""

    def __init__(
        self, label: str, bg_color: str, fg_color: str = "#ffffff", parent=None
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            f"""
            background-color: {bg_color};
            color: {fg_color};
            border-radius: 8px;
            padding: 2px 8px;
            font-size: 10px;
            font-weight: bold;
        """
        )
        layout.addWidget(self._label)


class _DaySubTable(QTableWidget):
    """双栏布局中的单栏表格。"""

    edit_requested = Signal(str, object)  # date_str, DayRecord
    delete_requested = Signal(str)  # date_str

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setColumnCount(len(COLUMNS))
        self.setHorizontalHeaderLabels(COLUMNS)
        self.horizontalHeader().setStretchLastSection(False)
        self.verticalHeader().hide()
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setMouseTracking(True)

        # Font
        cell_font = QFont("Microsoft YaHei", 9)
        self.setFont(cell_font)

    def draw(self, records: list, today: str, prev_warehouse: float | None = None) -> None:
        """根据 records 绘制单栏表格。

        Args:
            records: [(date_str, DayRecord), ...]
            today: 今日日期字符串 YYYY-MM-DD
            prev_warehouse: 前一条记录的仓库值（用于跨栏计算较前日）
        """
        self.setRowCount(len(records))

        for ri, (date_str, record) in enumerate(records):
            is_today = date_str == today
            bg_color = QColor(
                get_color("TABLE_ROW_EVEN_BG" if ri % 2 == 0 else "TABLE_ROW_ODD_BG")
            )

            # 0: 日期
            date_display = f"{date_str[-5:]} 今天" if is_today else date_str[-5:]
            date_color = get_color("FG_TODAY") if is_today else get_color("TABLE_TEXT")
            item = QTableWidgetItem(date_display)
            item.setForeground(QColor(date_color))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(ri, COL_DATE, item)

            # 1: 现金
            item = QTableWidgetItem(format_money(record.cash))
            item.setForeground(QColor(get_color("TABLE_TEXT")))
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(ri, COL_CASH, item)

            # 2: 仓库（总收益）
            item = QTableWidgetItem(format_money(record.warehouse))
            item.setForeground(QColor(get_color("TABLE_TEXT_BOLD")))
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bold_font = QFont("Microsoft YaHei", 9, QFont.Weight.Bold)
            item.setFont(bold_font)
            self.setItem(ri, COL_WAREHOUSE, item)

            # 3: 较前日
            if prev_warehouse is not None:
                delta = record.warehouse - prev_warehouse
                diff = (
                    f"+{format_money(delta)}"
                    if delta >= 0
                    else format_money(delta)
                )
                delta_color = (
                    get_color("FG_POS") if delta > 0
                    else (get_color("FG_NEG") if delta < 0 else get_color("FG_MUTED"))
                )
            else:
                diff = "—"
                delta_color = get_color("FG_MUTED")

            item = QTableWidgetItem(diff)
            item.setForeground(QColor(delta_color))
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(ri, COL_DIFF, item)

            # 4: 收益率
            rate_str, rate_color = ProfitCalculatorLogic.format_rate(
                ProfitCalculatorLogic.calculate_rate(prev_warehouse, record.warehouse)
            )
            item = QTableWidgetItem(rate_str)
            item.setForeground(QColor(rate_color))
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(ri, COL_RATE, item)

            # 5: 盈亏标签
            pnl_text, pnl_bg = ProfitCalculatorLogic.get_pnl_label(
                prev_warehouse, record.warehouse
            )
            badge = PnLBadge(pnl_text, pnl_bg)
            self.setCellWidget(ri, COL_PNL, badge)

            # 6: 操作按钮
            action_widget = self._create_action_buttons(date_str, record)
            self.setCellWidget(ri, COL_ACTIONS, action_widget)

            prev_warehouse = record.warehouse

        # 列宽
        for ci, w in enumerate(COL_WIDTHS):
            self.setColumnWidth(ci, w)

        # 纵向自适应行高
        self.resizeRowsToContents()

    def _create_action_buttons(
        self, date_str: str, record: DayRecord
    ) -> QWidget:
        """创建操作列：编辑 + 删除按钮（明显可见的样式）。"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_fg = get_color("BTN_BG")
        btn_hover = get_color("BTN_BG_HOVER")
        neg_color = get_color("FG_NEG")
        muted_bg = get_color("MUTED_BG")

        edit_btn = QPushButton("编辑")
        edit_btn.setFixedHeight(22)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {muted_bg};
                color: {btn_fg};
                border: 1px solid {get_color("BORDER_DEFAULT")};
                border-radius: 4px;
                padding: 1px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_fg};
                color: #ffffff;
                border-color: {btn_hover};
            }}
        """)
        edit_btn.clicked.connect(
            lambda checked, d=date_str, r=record: self.edit_requested.emit(d, r)
        )
        layout.addWidget(edit_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setFixedHeight(22)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #fee2e2;
                color: {neg_color};
                border: 1px solid #fecaca;
                border-radius: 4px;
                padding: 1px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {neg_color};
                color: #ffffff;
                border-color: {neg_color};
            }}
        """)
        delete_btn.clicked.connect(
            lambda checked, d=date_str: self.delete_requested.emit(d)
        )
        layout.addWidget(delete_btn)

        return widget

    def apply_theme(self) -> None:
        """下次 draw() 时应用新主题色。"""
        pass


class TableWidget(QWidget):
    """双栏布局表格：左栏前4天 + 右栏后3天数据。"""

    edit_requested = Signal(str, object)  # date_str, DayRecord
    delete_requested = Signal(str)  # date_str

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(12)

        # 左栏
        self._left_column = QWidget()
        left_layout = QVBoxLayout(self._left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._left_title = QLabel()
        self._left_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._left_title.setStyleSheet(
            f"font-weight: bold; font-size: 11px; color: {get_color('FG_MUTED')};"
        )
        left_layout.addWidget(self._left_title)

        self._left_table = _DaySubTable()
        self._left_table.edit_requested.connect(self.edit_requested.emit)
        self._left_table.delete_requested.connect(self.delete_requested.emit)
        left_layout.addWidget(self._left_table)

        self._layout.addWidget(self._left_column, 1)

        # 右栏
        self._right_column = QWidget()
        right_layout = QVBoxLayout(self._right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self._right_title = QLabel()
        self._right_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._right_title.setStyleSheet(
            f"font-weight: bold; font-size: 11px; color: {get_color('FG_MUTED')};"
        )
        right_layout.addWidget(self._right_title)

        self._right_table = _DaySubTable()
        self._right_table.edit_requested.connect(self.edit_requested.emit)
        self._right_table.delete_requested.connect(self.delete_requested.emit)
        right_layout.addWidget(self._right_table)

        self._layout.addWidget(self._right_column, 1)

    def draw(self, records: list, today: str) -> None:
        """根据 records 绘制双栏表格。

        Args:
            records: [(date_str, DayRecord), ...] 有数据的日期列表
            today: 今日日期字符串 YYYY-MM-DD
        """
        n = len(records)
        mid = min(4, n)
        left_records = records[:mid]
        right_records = records[mid:]

        # 更新标题
        if left_records:
            left_range = f"{left_records[0][0][-5:]} ~ {left_records[-1][0][-5:]}"
            self._left_title.setText(f"前{len(left_records)}天数据 ({left_range})")
        else:
            self._left_title.setText("暂无数据")

        if right_records:
            right_range = f"{right_records[0][0][-5:]} ~ {right_records[-1][0][-5:]}"
            self._right_title.setText(f"后{len(right_records)}天数据 ({right_range})")
        else:
            self._right_title.setText("")

        # 绘制左表
        self._left_table.draw(left_records, today)

        # 绘制右表：传入左表最后一条记录的仓库值作为 prev_warehouse
        prev = left_records[-1][1].warehouse if left_records else None
        self._right_table.draw(right_records, today, prev_warehouse=prev)

    def apply_theme(self) -> None:
        """主题切换后标记清除；下次 draw() 重建。"""
        self._left_table.apply_theme()
        self._right_table.apply_theme()

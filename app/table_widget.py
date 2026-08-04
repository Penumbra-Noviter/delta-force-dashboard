"""
可切换视图数据表格：PySide6 双栏布局。

视图窗口 7/30 可切换（J 系列，Consensus §7）：按钮组 7天/30天，
默认 7 天。存储与视图解耦——30 是「隐藏累积」的全量存储，控制在
calculator.rotate_weekly 的 RETENTION_LIMIT；本表只是从存量里筛出
当前视图条数来展示，切回 7 不丢数据。

双栏按 mid=ceil(n/2) 均分（7→4+3、30→15+15），减少滚动操作。
7 列：日期、现金、仓库（总收益）、较前日、收益率、盈亏标签、操作。
"""

from __future__ import annotations

from math import ceil

__all__ = ["PnLBadge", "TableWidget"]

from PySide6.QtCore import Qt, Signal, QModelIndex
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.theme import get_color, signal_color
from formatting import format_money, format_short_date
from calculator import DayRecord, ProfitCalculatorLogic


# 标题基础样式：颜色随主题实时解析，不在此冻结
_TITLE_STYLE = "font-weight: bold; font-size: 11px; color: {};"

COLUMNS = ["日期", "现金", "仓库（总收益）", "较前日", "收益率", "盈亏", "操作"]
# 最小列宽（Stretch 模式下的保底宽度，保证内容不被硬截断）
# 总最小宽 ≈ 515px，远小于常见窗口宽度
COL_MIN_WIDTHS = [60, 80, 90, 85, 70, 100, 120]
# Column indices
COL_DATE = 0
COL_CASH = 1
COL_WAREHOUSE = 2
COL_DIFF = 3
COL_RATE = 4
COL_PNL = 5
COL_ACTIONS = 6

# 可切换的视图窗口（J 系列）：与存储保留上限 RETENTION_LIMIT 解耦的展示口径。
VIEW_DAYS = (7, 30)


class PnLBadge(QWidget):
    """盈亏标签 Badge：绿底"盈 +2.4%"/红底"亏 -1.3%"/灰底"—"。"""

    def __init__(
        self, label: str, bg_color: str, fg_color: str = "#ffffff", parent=None
    ) -> None:
        super().__init__(parent)
        self.setMinimumWidth(80)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            f"""
            background-color: {bg_color};
            color: {fg_color};
            border-radius: 9px;
            padding: 2px 10px;
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

        # ── 自适应列宽策略：Interactive + 手动比例分配 ──
        # Stretch 模式下 Qt 会均分列宽，对初始宽度不敏感
        # 改用 Interactive 模式，在 resizeEvent 中按 COL_MIN_WIDTHS 比例分配
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        # 横向滚动条：空间不足时自动出现（兜底，永不截断）
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.verticalHeader().hide()
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.setMouseTracking(True)

        # Font（基础字号，实际由 QSS 覆盖）
        cell_font = QFont("Microsoft YaHei", 10)
        self.setFont(cell_font)

    def mousePressEvent(self, event) -> None:
        """点击空白区（非单元格、非按钮）时清除选中高亮。"""
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            self.clearSelection()
            self.setCurrentIndex(QModelIndex())
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:
        """窗口大小变化时按比例重分列宽，保证盈亏列不被压缩。"""
        super().resizeEvent(event)
        self._apply_proportional_widths()

    def _apply_proportional_widths(self) -> None:
        """根据视口宽度按 COL_MIN_WIDTHS 比例分配各列宽度。"""
        viewport_w = self.viewport().width()
        total_min = sum(COL_MIN_WIDTHS)

        if viewport_w <= 0:
            return

        if viewport_w >= total_min:
            # 空间充足：按比例缩放，所有列等比放大
            scale = viewport_w / total_min
            allocated = 0
            for ci, min_w in enumerate(COL_MIN_WIDTHS):
                w = int(min_w * scale)
                allocated += w
                self.setColumnWidth(ci, w)
            # 取整误差补偿：从最宽的操作列扣除 1-2px，防止滚动条闪烁
            if allocated > viewport_w:
                diff = allocated - viewport_w
                ci_act = COL_ACTIONS
                self.setColumnWidth(
                    ci_act, max(COL_MIN_WIDTHS[ci_act], self.columnWidth(ci_act) - diff)
                )
        else:
            # 空间不足：保持最小宽度，启用横向滚动条
            for ci, min_w in enumerate(COL_MIN_WIDTHS):
                self.setColumnWidth(ci, min_w)

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
            # 今日行用浅青底，其他行用交替底
            if is_today:
                row_bg = QColor(get_color("TABLE_ROW_TODAY_BG"))
            else:
                row_bg = QColor(
                    get_color("TABLE_ROW_EVEN_BG" if ri % 2 == 0 else "TABLE_ROW_ODD_BG")
                )

            # 0: 日期
            date_display = f"{format_short_date(date_str)} 今天" if is_today else format_short_date(date_str)
            date_color = get_color("FG_TODAY") if is_today else get_color("TABLE_TEXT")
            item = QTableWidgetItem(date_display)
            item.setForeground(QColor(date_color))
            item.setBackground(row_bg)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setItem(ri, COL_DATE, item)

            # 1: 现金
            item = QTableWidgetItem(format_money(record.cash))
            item.setForeground(QColor(get_color("TABLE_TEXT")))
            item.setBackground(row_bg)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(ri, COL_CASH, item)

            # 2: 仓库（总收益）
            item = QTableWidgetItem(format_money(record.warehouse))
            item.setForeground(QColor(get_color("TABLE_TEXT_BOLD")))
            item.setBackground(row_bg)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            bold_font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)
            item.setFont(bold_font)
            self.setItem(ri, COL_WAREHOUSE, item)

            # 3: 较前日
            if prev_warehouse is not None:
                diff, delta_signal = ProfitCalculatorLogic.format_signed_money(
                    record.warehouse - prev_warehouse
                )
                delta_color = signal_color(delta_signal)
            else:
                diff = "—"
                delta_color = get_color("FG_MUTED")

            item = QTableWidgetItem(diff)
            item.setForeground(QColor(delta_color))
            item.setBackground(row_bg)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(ri, COL_DIFF, item)

            # 4: 收益率
            rate = ProfitCalculatorLogic.calculate_rate(prev_warehouse, record.warehouse)
            rate_str, rate_signal = ProfitCalculatorLogic.format_rate(rate)
            rate_color = signal_color(rate_signal)
            item = QTableWidgetItem(rate_str)
            item.setForeground(QColor(rate_color))
            item.setBackground(row_bg)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.setItem(ri, COL_RATE, item)

            # 5: 盈亏标签（合并收益率：盈 +2.4% / 亏 -1.3% / —）
            pnl_text, pnl_signal = ProfitCalculatorLogic.get_pnl_label(
                prev_warehouse, record.warehouse
            )
            pnl_bg = signal_color(pnl_signal)
            if pnl_text == "—":
                badge_text = "—"
            else:
                badge_text = f"{pnl_text} {rate_str}"
            badge = PnLBadge(badge_text, pnl_bg)
            self.setCellWidget(ri, COL_PNL, badge)

            # 6: 操作按钮
            action_widget = self._create_action_buttons(date_str, record)
            self.setCellWidget(ri, COL_ACTIONS, action_widget)

            prev_warehouse = record.warehouse

        # 纵向自适应行高
        self.resizeRowsToContents()
        # 按比例分配列宽（窗口首次显示时 resizeEvent 可能还未触发）
        self._apply_proportional_widths()

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
        danger_bg = get_color("DANGER_BG")
        danger_fg = get_color("DANGER_FG")
        danger_border = get_color("DANGER_BORDER")
        danger_hover = get_color("DANGER_HOVER_BG")

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
                background-color: {danger_bg};
                color: {danger_fg};
                border: 1px solid {danger_border};
                border-radius: 4px;
                padding: 1px 8px;
                font-size: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {danger_hover};
                color: #ffffff;
                border-color: {danger_hover};
            }}
        """)
        delete_btn.clicked.connect(
            lambda checked, d=date_str: self.delete_requested.emit(d)
        )
        layout.addWidget(delete_btn)

        return widget


class TableWidget(QWidget):
    """双栏布局表格：视图 7/30 可切换（按钮组），按 mid=ceil(n/2) 均分栏位。

    表格是「视图窗口」的主人（Consensus §7 Q8）：持有当前视图条数
    self._view_days 与按钮组，切换时 emit view_changed(int)；MainWindow
    只订阅、据此改 _view_n 重新拉取 records —— 深模块，分割逻辑留在表内。
    """

    edit_requested = Signal(str, object)  # date_str, DayRecord
    delete_requested = Signal(str)  # date_str
    view_changed = Signal(int)  # 当前视图条数（7 / 30）

    def columnCount(self) -> int:
        """返回左栏子表的列数（双栏列数相同）。"""
        return self._left_table.columnCount()

    def current_view(self) -> int:
        """返回当前视图条数（7 / 30）。"""
        return self._view_days

    def __init__(
        self,
        parent: QWidget | None = None,
        default_view: int = VIEW_DAYS[0],
    ) -> None:
        super().__init__(parent)
        self._view_days = default_view

        # 视图切换栏（按钮组 7/30，Q8：进表内、emit 信号）
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)

        self._view_bar = QWidget()
        view_layout = QHBoxLayout(self._view_bar)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(8)
        view_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_group = QButtonGroup(self)
        self._view_buttons: list[QRadioButton] = []
        for days in VIEW_DAYS:
            btn = QRadioButton(f"{days} 天")
            btn.setProperty("days", days)
            btn.setChecked(days == default_view)
            self._btn_group.addButton(btn)
            self._view_buttons.append(btn)
            btn.toggled.connect(self._on_view_toggled)
            view_layout.addWidget(btn)
        self._layout.addWidget(self._view_bar)

        # 双栏主体
        self._body = QWidget()
        self._body_layout = QHBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(12)
        self._layout.addWidget(self._body)

        # 左栏
        self._left_column = QWidget()
        left_layout = QVBoxLayout(self._left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self._left_title = QLabel()
        self._left_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self._left_title)

        self._left_table = _DaySubTable()
        self._left_table.edit_requested.connect(self.edit_requested.emit)
        self._left_table.delete_requested.connect(self.delete_requested.emit)
        left_layout.addWidget(self._left_table)

        self._body_layout.addWidget(self._left_column, 1)

        # 右栏
        self._right_column = QWidget()
        right_layout = QVBoxLayout(self._right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)

        self._right_title = QLabel()
        self._right_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(self._right_title)

        self._right_table = _DaySubTable()
        self._right_table.edit_requested.connect(self.edit_requested.emit)
        self._right_table.delete_requested.connect(self.delete_requested.emit)
        right_layout.addWidget(self._right_table)

        self._body_layout.addWidget(self._right_column, 1)

    def draw(self, records: list, today: str) -> None:
        """根据 records 绘制双栏表格。

        Args:
            records: [(date_str, DayRecord), ...] 有数据的日期列表
            today: 今日日期字符串 YYYY-MM-DD
        """
        n = len(records)
        # 均分：mid=ceil(n/2)（Q7：7→4+3、30→15+15，双栏均衡）
        mid = ceil(n / 2)
        left_records = records[:mid]
        right_records = records[mid:]

        # 更新标题（配色在渲染时解析，随主题切换即时生效）
        self._left_title.setStyleSheet(_TITLE_STYLE.format(get_color("FG_MUTED")))
        if left_records:
            left_range = f"{format_short_date(left_records[0][0])} ~ {format_short_date(left_records[-1][0])}"
            self._left_title.setText(f"前{len(left_records)}天数据 ({left_range})")
        else:
            self._left_title.setText("暂无数据")

        self._right_title.setStyleSheet(_TITLE_STYLE.format(get_color("FG_MUTED")))
        if right_records:
            right_range = f"{format_short_date(right_records[0][0])} ~ {format_short_date(right_records[-1][0])}"
            self._right_title.setText(f"后{len(right_records)}天数据 ({right_range})")
        else:
            self._right_title.setText("")

        # 绘制左表
        self._left_table.draw(left_records, today)

        # 绘制右表：传入左表最后一条记录的仓库值作为 prev_warehouse
        prev = left_records[-1][1].warehouse if left_records else None
        self._right_table.draw(right_records, today, prev_warehouse=prev)

    def _on_view_toggled(self) -> None:
        """按钮组切换：更新当前视图条数并 emit view_changed(int)。

        QRadioButton 互斥保证同一时刻仅一个 checked；取选中按钮的 days 属性，
        非选中（关）状态的红利 toggle 忽略。
        """
        checked = self._btn_group.checkedButton()
        if checked is None:
            return
        current_days = int(checked.property("days"))
        if current_days != self._view_days:
            self._view_days = current_days
            self.view_changed.emit(current_days)

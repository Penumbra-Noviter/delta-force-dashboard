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
from config import VIEW_DAYS
from formatting import format_money, format_short_date
from calculator import DayRecord, ProfitCalculatorLogic
from presentation import format_rate, format_signed_money, get_pnl_label


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
        layout.addWidget(self._label)
        self._apply_style(bg_color, fg_color)

    def update_content(self, label: str, bg_color: str, fg_color: str = "#ffffff") -> None:
        """复用：更新文本与配色，不重建 widget。"""
        self._label.setText(label)
        self._apply_style(bg_color, fg_color)

    def _apply_style(self, bg_color: str, fg_color: str) -> None:
        self._label.setStyleSheet(
            f"""
            background-color: {bg_color};
            color: {fg_color};
            border-radius: 12px;
            padding: 3px 12px;
            font-size: 10px;
            font-weight: 600;
        """
        )


class _ActionButtons(QWidget):
    """操作列按钮：编辑 + 删除。复用 widget，仅更新数据与主题样式。"""

    edit_requested = Signal(str, object)  # date_str, DayRecord
    delete_requested = Signal(str)  # date_str

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._edit_btn = QPushButton("编辑")
        self._edit_btn.setFixedHeight(24)
        self._edit_btn.clicked.connect(self._on_edit_clicked)
        layout.addWidget(self._edit_btn)

        self._delete_btn = QPushButton("删除")
        self._delete_btn.setFixedHeight(24)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        layout.addWidget(self._delete_btn)

        self._date_str = ""
        self._record: DayRecord | None = None
        self.apply_theme()

    def update_data(self, date_str: str, record: DayRecord) -> None:
        """更新当前行数据（复用时不重建按钮，只换数据）。"""
        self._date_str = date_str
        self._record = record

    def apply_theme(self) -> None:
        """根据当前主题色更新按钮内联样式。"""
        btn_fg = get_color("BTN_BG")
        btn_hover = get_color("BTN_BG_HOVER")
        muted_bg = get_color("MUTED_BG")
        border_def = get_color("BORDER_DEFAULT")
        danger_bg = get_color("DANGER_BG")
        danger_fg = get_color("DANGER_FG")
        danger_border = get_color("DANGER_BORDER")
        danger_hover = get_color("DANGER_HOVER_BG")

        self._edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {muted_bg};
                color: {btn_fg};
                border: 1px solid {border_def};
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {btn_fg};
                color: #ffffff;
                border-color: {btn_hover};
            }}
        """)
        self._delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {danger_bg};
                color: {danger_fg};
                border: 1px solid {danger_border};
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {danger_hover};
                color: #ffffff;
                border-color: {danger_hover};
            }}
        """)

    def _on_edit_clicked(self) -> None:
        if self._record is not None:
            self.edit_requested.emit(self._date_str, self._record)

    def _on_delete_clicked(self) -> None:
        self.delete_requested.emit(self._date_str)


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
        """根据 records 绘制单栏表格（复用已有 widget，仅更新内容）。

        Args:
            records: [(date_str, DayRecord), ...]
            today: 今日日期字符串 YYYY-MM-DD
            prev_warehouse: 前一条记录的仓库值（用于跨栏计算较前日）
        """
        n = len(records)
        # 行数变化时才调 setRowCount（避免不必要的重排）
        if self.rowCount() != n:
            self.setRowCount(n)

        _align_right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        _bold_font = QFont("Microsoft YaHei", 10, QFont.Weight.Bold)

        for ri, (date_str, record) in enumerate(records):
            is_today = date_str == today
            if is_today:
                row_bg = QColor(get_color("TABLE_ROW_TODAY_BG"))
            else:
                row_bg = QColor(
                    get_color("TABLE_ROW_EVEN_BG" if ri % 2 == 0 else "TABLE_ROW_ODD_BG")
                )

            # 0: 日期
            date_display = f"{format_short_date(date_str)} 今天" if is_today else format_short_date(date_str)
            date_color = get_color("FG_TODAY") if is_today else get_color("TABLE_TEXT")
            item = self.item(ri, COL_DATE)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.setItem(ri, COL_DATE, item)
            item.setText(date_display)
            item.setForeground(QColor(date_color))
            item.setBackground(row_bg)

            # 1: 现金
            item = self.item(ri, COL_CASH)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(_align_right)
                self.setItem(ri, COL_CASH, item)
            item.setText(format_money(record.cash))
            item.setForeground(QColor(get_color("TABLE_TEXT")))
            item.setBackground(row_bg)

            # 2: 仓库（总收益）
            item = self.item(ri, COL_WAREHOUSE)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(_align_right)
                item.setFont(_bold_font)
                self.setItem(ri, COL_WAREHOUSE, item)
            item.setText(format_money(record.warehouse))
            item.setForeground(QColor(get_color("TABLE_TEXT_BOLD")))
            item.setBackground(row_bg)

            # 3: 较前日
            if prev_warehouse is not None:
                diff, delta_signal = format_signed_money(
                    record.warehouse - prev_warehouse
                )
                delta_color = signal_color(delta_signal)
            else:
                diff = "—"
                delta_color = get_color("FG_MUTED")

            item = self.item(ri, COL_DIFF)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(_align_right)
                self.setItem(ri, COL_DIFF, item)
            item.setText(diff)
            item.setForeground(QColor(delta_color))
            item.setBackground(row_bg)

            # 4: 收益率
            rate = ProfitCalculatorLogic.calculate_rate(prev_warehouse, record.warehouse)
            rate_str, rate_signal = format_rate(rate)
            rate_color = signal_color(rate_signal)
            item = self.item(ri, COL_RATE)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(_align_right)
                self.setItem(ri, COL_RATE, item)
            item.setText(rate_str)
            item.setForeground(QColor(rate_color))
            item.setBackground(row_bg)

            # 5: 盈亏标签（合并收益率：盈 +2.4% / 亏 -1.3% / —）
            pnl_text, pnl_signal = get_pnl_label(
                prev_warehouse, record.warehouse
            )
            pnl_bg = signal_color(pnl_signal)
            if pnl_text == "—":
                badge_text = "—"
            else:
                badge_text = f"{pnl_text} {rate_str}"
            badge = self.cellWidget(ri, COL_PNL)
            if badge is None:
                badge = PnLBadge(badge_text, pnl_bg)
                self.setCellWidget(ri, COL_PNL, badge)
            else:
                badge.update_content(badge_text, pnl_bg)

            # 6: 操作按钮
            actions = self.cellWidget(ri, COL_ACTIONS)
            if actions is None:
                actions = _ActionButtons()
                actions.edit_requested.connect(self.edit_requested.emit)
                actions.delete_requested.connect(self.delete_requested.emit)
                self.setCellWidget(ri, COL_ACTIONS, actions)
            else:
                actions.apply_theme()
            actions.update_data(date_str, record)

            prev_warehouse = record.warehouse

        # 纵向自适应行高
        self.resizeRowsToContents()
        # 按比例分配列宽（窗口首次显示时 resizeEvent 可能还未触发）
        self._apply_proportional_widths()


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
        view_layout.setSpacing(6)
        view_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._btn_group = QButtonGroup(self)
        self._view_buttons: list[QPushButton] = []
        for days in VIEW_DAYS:
            btn = QPushButton(f"{days} 天")
            btn.setProperty("days", days)
            btn.setCheckable(True)
            btn.setChecked(days == default_view)
            btn.setFixedHeight(28)
            self._btn_group.addButton(btn)
            self._view_buttons.append(btn)
            btn.toggled.connect(self._on_view_toggled)
            view_layout.addWidget(btn)
        self._layout.addWidget(self._view_bar)
        self._update_view_btn_styles()

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
        # 主题切换后刷新视图按钮样式
        self._update_view_btn_styles()
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

        QPushButton checkable 互斥保证同一时刻仅一个 checked；取选中按钮的 days 属性，
        非选中状态的红利 toggle 忽略。
        """
        checked = self._btn_group.checkedButton()
        if checked is None:
            return
        current_days = int(checked.property("days"))
        if current_days != self._view_days:
            self._view_days = current_days
            self._update_view_btn_styles()
            self.view_changed.emit(current_days)

    def _update_view_btn_styles(self) -> None:
        """更新视图切换按钮的 pill 选中/未选中样式。"""
        btn_bg = get_color("BTN_BG")
        btn_fg = get_color("BTN_FG")
        muted_bg = get_color("MUTED_BG")
        fg_muted = get_color("FG_MUTED")
        border_def = get_color("BORDER_DEFAULT")
        for btn in self._view_buttons:
            if btn.isChecked():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {btn_bg};
                        color: {btn_fg};
                        border: none;
                        border-radius: 14px;
                        padding: 4px 16px;
                        font-size: 11px;
                        font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {muted_bg};
                        color: {fg_muted};
                        border: 1px solid {border_def};
                        border-radius: 14px;
                        padding: 4px 16px;
                        font-size: 11px;
                        font-weight: 500;
                    }}
                    QPushButton:hover {{
                        background-color: {get_color("SEPARATOR")};
                        color: {get_color("TABLE_TEXT_BOLD")};
                    }}
                """)

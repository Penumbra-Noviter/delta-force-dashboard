"""
输入面板：PySide6 QWidget 版。

提供两个金额输入框（现金 + 仓库），实时校验边框变色，
焦点进出格式化，保存/编辑模式切换。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.theme import get_color, get_theme
from formatting import (
    format_input_value,
    format_money,
    is_valid_money_input,
    parse_money_input,
    unformat_input_value,
)

# Font sizes (same as original Tkinter config)
FONT_INPUT = 13
FONT_LABEL = 11
FONT_BUTTON = 12
FONT_META = 9


class MoneyLineEdit(QLineEdit):
    """金额输入框：聚焦时反格式化，失焦时格式化，实时校验（带 150ms 去抖）。"""

    validity_changed = Signal(bool)  # True=合法, False=非法

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._formatting = False

        self.setPlaceholderText("输入金额（支持 K/M/B 后缀）")
        self.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.setMinimumWidth(200)

        # 去抖 QTimer：快速输入时避免每次按键都触发校验
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(150)
        self._debounce_timer.timeout.connect(self._update_validity)

        self.textChanged.connect(self._on_text_changed)
        self.setProperty("validity", "normal")

    def _on_text_changed(self, text: str) -> None:
        if self._formatting:
            return
        # 重启去抖计时器，连续输入时只在停顿后校验一次
        self._debounce_timer.start()

    def _update_validity(self) -> None:
        text = self.text().strip()
        if text == "":
            self._set_validity_state("normal")
            self.validity_changed.emit(True)  # 空文本不阻止保存
            return
        valid = is_valid_money_input(text)
        if valid:
            self._set_validity_state("valid")
        else:
            self._set_validity_state("invalid")
        self.validity_changed.emit(valid and text != "")

    def _set_validity_state(self, state: str) -> None:
        self.setProperty("validity", state)
        self.style().unpolish(self)
        self.style().polish(self)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        if self._formatting:
            return
        raw = self.text().strip()
        if raw:
            try:
                value = parse_money_input(raw)
                if value is not None:
                    self._formatting = True
                    self.setText(unformat_input_value(raw))
                    self._formatting = False
                    self.selectAll()
            except ValueError:
                pass

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        if self._formatting:
            return
        # 失焦时立即校验，不等去抖
        self._debounce_timer.stop()
        self._update_validity()
        raw = self.text().strip()
        if raw:
            try:
                value = parse_money_input(raw)
                if value is not None:
                    self._formatting = True
                    self.setText(format_input_value(value))
                    self._formatting = False
            except ValueError:
                pass


class InputPanel(QWidget):
    """管理现金/仓库输入框、保存按钮、编辑模式的 UI 组件。"""

    save_requested = Signal()  # 由按钮或 Enter 触发，主窗口处理
    cancel_requested = Signal()
    reuse_requested = Signal()  # 复用最近一条记录
    reuse_cancel_requested = Signal()  # 取消复用

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._editing = False
        self._editing_date: str | None = None
        self._reusing = False  # 是否处于复用状态

        self._build()

    def _build(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)

        # ── 输入区 ──
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(6)

        # 现金行
        cash_row = QHBoxLayout()
        cash_row.setSpacing(10)
        self._cash_label = QLabel("当前现金")
        self._cash_label.setFixedWidth(120)
        self._cash_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.cash_entry = MoneyLineEdit()
        cash_row.addWidget(self._cash_label)
        cash_row.addWidget(self.cash_entry, 1)
        form_layout.addLayout(cash_row)

        # 仓库行
        warehouse_row = QHBoxLayout()
        warehouse_row.setSpacing(10)
        self._warehouse_label = QLabel("仓库价值（含现金）")
        self._warehouse_label.setFixedWidth(120)
        self._warehouse_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.warehouse_entry = MoneyLineEdit()
        warehouse_row.addWidget(self._warehouse_label)
        warehouse_row.addWidget(self.warehouse_entry, 1)
        form_layout.addLayout(warehouse_row)

        main_layout.addWidget(form_widget)

        # ── 按钮栏 ──
        btn_widget = QWidget()
        btn_layout = QHBoxLayout(btn_widget)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        self.reuse_btn = QPushButton("复用昨日")
        self.reuse_btn.setObjectName("reuseBtn")
        self.reuse_btn.setToolTip("填入最近一条记录的数据，便于微调")
        self.reuse_btn.clicked.connect(self._on_reuse_btn_clicked)
        btn_layout.addWidget(self.reuse_btn)

        self.save_btn = QPushButton("保存今日数据")
        self.save_btn.setObjectName("saveBtn")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_requested.emit)
        btn_layout.addWidget(self.save_btn)

        self.cancel_edit_btn = QPushButton("取消编辑")
        self.cancel_edit_btn.setObjectName("cancelEditBtn")
        self.cancel_edit_btn.clicked.connect(self.cancel_requested.emit)
        self.cancel_edit_btn.hide()
        btn_layout.addWidget(self.cancel_edit_btn)

        self.saved_indicator = QLabel("")
        self.saved_indicator.setObjectName("savedIndicator")
        btn_layout.addWidget(self.saved_indicator)

        btn_layout.addStretch()
        main_layout.addWidget(btn_widget)

        # ── Tab 顺序：现金 → 仓库 → 复用 → 保存 → 取消 ──
        self.setTabOrder(self.cash_entry, self.warehouse_entry)
        self.setTabOrder(self.warehouse_entry, self.reuse_btn)
        self.setTabOrder(self.reuse_btn, self.save_btn)
        self.setTabOrder(self.save_btn, self.cancel_edit_btn)

        # ── 输入校验联动 ──
        self.cash_entry.validity_changed.connect(self._update_save_btn_state)
        self.warehouse_entry.validity_changed.connect(self._update_save_btn_state)

    def _update_save_btn_state(self) -> None:
        cash_ok = (
            is_valid_money_input(self.cash_entry.text())
            and self.cash_entry.text().strip() != ""
        )
        warehouse_ok = (
            is_valid_money_input(self.warehouse_entry.text())
            and self.warehouse_entry.text().strip() != ""
        )
        self.save_btn.setEnabled(cash_ok and warehouse_ok)

    # ── 编辑模式 ──

    def set_edit_mode(self, date_str: str, cash: float, warehouse: float) -> None:
        """将输入框切换为编辑模式，填充指定日期的数据。"""
        self._editing = True
        self._editing_date = date_str

        # 直接填数字，不触发格式化
        self.cash_entry._formatting = True
        self.cash_entry.setText(f"{cash:.2f}")
        self.cash_entry._formatting = False

        self.warehouse_entry._formatting = True
        self.warehouse_entry.setText(f"{warehouse:.2f}")
        self.warehouse_entry._formatting = False

        self.save_btn.setText(f"更新数据（{date_str[-5:]}）")
        edit_color = get_color("CHART_WAREHOUSE")
        self.save_btn.setStyleSheet(f"""
            QPushButton#saveBtn {{
                background-color: {edit_color};
                color: #ffffff;
                padding: 8px 28px;
                font-weight: bold;
            }}
            QPushButton#saveBtn:hover {{
                background-color: {edit_color}dd;
            }}
        """)
        self.cancel_edit_btn.show()
        self.reuse_btn.hide()
        self.saved_indicator.setText("")
        self._update_save_btn_state()
        self.cash_entry.setFocus()

    def cancel_edit(self) -> None:
        """退出编辑模式，恢复默认状态。"""
        self._editing = False
        self._editing_date = None
        self.cash_entry.setText("")
        self.warehouse_entry.setText("")

        self.save_btn.setText("保存今日数据")
        # 清除内联样式以恢复 QSS
        self.save_btn.setStyleSheet("")
        self.cancel_edit_btn.hide()
        self.reuse_btn.show()
        self.saved_indicator.setText("")
        self._update_save_btn_state()
        self.cash_entry.setFocus()

    def is_editing(self) -> bool:
        return self._editing

    def get_editing_date(self) -> str | None:
        return self._editing_date

    # ── 复用模式 ──

    def _on_reuse_btn_clicked(self) -> None:
        """复用按钮点击：非复用状态→发起复用；复用状态→取消复用。"""
        if self._reusing:
            self.reuse_cancel_requested.emit()
        else:
            self.reuse_requested.emit()

    def set_reuse_mode(self) -> None:
        """进入复用模式：按钮变为「取消复用」红色样式。"""
        self._reusing = True
        self.reuse_btn.setText("取消复用")
        self.reuse_btn.setToolTip("清除已复用的数据")
        self.reuse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {get_color('DANGER_BG')};
                color: {get_color('DANGER_FG')};
                border: 1px solid {get_color('DANGER_BORDER')};
                border-radius: 5px;
                padding: 6px 14px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {get_color('DANGER_HOVER_BG')};
                color: #ffffff;
            }}
        """)

    def cancel_reuse(self) -> None:
        """退出复用模式，恢复按钮为「复用昨日」。"""
        self._reusing = False
        self.reuse_btn.setText("复用昨日")
        self.reuse_btn.setToolTip("填入最近一条记录的数据，便于微调")
        self.reuse_btn.setStyleSheet("")

    def is_reusing(self) -> bool:
        return self._reusing

    # ── 指示器 ──

    def set_saved_indicator(self, text: str) -> None:
        self.saved_indicator.setText(text)

    def focus_cash(self) -> None:
        self.cash_entry.setFocus()

    # ── 批量填值 / 清空（供主窗口调用）──

    def fill_values(self, cash: float, warehouse: float) -> None:
        """填入指定金额并选中现金框，便于微调。不触发焦点格式化。"""
        self.cash_entry._formatting = True
        self.cash_entry.setText(format_input_value(cash))
        self.cash_entry._formatting = False

        self.warehouse_entry._formatting = True
        self.warehouse_entry.setText(format_input_value(warehouse))
        self.warehouse_entry._formatting = False

        self._update_save_btn_state()
        self.cash_entry.setFocus()
        self.cash_entry.selectAll()

    def clear_fields(self) -> None:
        """清空输入框但保留已保存指示器，用于保存后快速录入下一条。"""
        self.cash_entry.clear()
        self.warehouse_entry.clear()
        self.cash_entry.setFocus()

    # ── 获取输入值 ──

    def get_cash_value(self) -> float | None:
        try:
            return parse_money_input(self.cash_entry.text())
        except ValueError:
            return None

    def get_warehouse_value(self) -> float | None:
        try:
            return parse_money_input(self.warehouse_entry.text())
        except ValueError:
            return None

    # ── 主题 ──

    def apply_theme(self) -> None:
        """更新主题相关的内联样式。"""
        c = get_color
        self._cash_label.setStyleSheet(f"color: {c('FG_LABEL')};")
        self._warehouse_label.setStyleSheet(f"color: {c('FG_LABEL')};")
        self.saved_indicator.setStyleSheet(f"color: {c('CHART_TOTAL')};")

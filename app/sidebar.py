"""
侧边栏导航组件：顶部账号区 + 左侧导航项 + 底部操作按钮。

- 账号区（Y-04）：当前账号下拉框 +「新建账号」按钮；下拉选择发
  ``account_selected`` 信号（切换逻辑在 MainWindow，Y-05），新建发
  ``create_account_requested``（命名对话框也在 MainWindow）。
- 导航项（记账 / 利润）点击切换 QStackedWidget 页面
- 底部放置主题切换、置顶、导出 CSV 按钮

本模块只做控件与信号，不接触文件系统：账号列表通过
``set_accounts(names, current)`` 由 MainWindow 注入（业务层数据）。
"""

from __future__ import annotations

__all__ = ["Sidebar"]

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui_text import EMOJI


class Sidebar(QWidget):
    """左侧导航栏：顶部账号区 + 导航项列表 + 底部操作按钮。"""

    nav_changed = Signal(int)
    # Y-04：下拉选择账号（切换由 MainWindow 处理，Y-05 接线）
    account_selected = Signal(str)
    # Y-04：点「新建账号」按钮（命名对话框由 MainWindow 弹出）
    create_account_requested = Signal()
    NAV_ITEMS = [f"{EMOJI['nav_ledger']} 记账", f"{EMOJI['nav_profit']} 利润"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        # U-04：100→130px，容纳「图标+文字」导航项与底部按钮；
        # Y-04 账号区纵向排布（标题/下拉/按钮），130px 内可容纳，不需加宽。
        self.setFixedWidth(130)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(0)

        # ── 顶部账号区（Y-04）──
        self.account_title = QLabel(f"{EMOJI['account']} 账号")
        self.account_title.setObjectName("accountAreaTitle")
        self.account_title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(self.account_title)
        layout.addSpacing(4)

        self.account_combo = QComboBox()
        self.account_combo.setObjectName("accountCombo")
        self.account_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # activated（用户动作）→ 账号选择信号；程序 setCurrentIndex 不触发
        self.account_combo.activated.connect(
            lambda index: self.account_selected.emit(
                self.account_combo.itemText(index)
            )
        )
        layout.addWidget(self.account_combo)
        layout.addSpacing(4)

        self.new_account_btn = QPushButton(f"{EMOJI['new_account']} 新建账号")
        self.new_account_btn.setObjectName("newAccountBtn")
        self.new_account_btn.setToolTip("新建一个空数据账号（不会自动切换）")
        self.new_account_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_account_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.new_account_btn.clicked.connect(self.create_account_requested.emit)
        layout.addWidget(self.new_account_btn)
        layout.addSpacing(12)

        self._nav_list = QListWidget()
        self._nav_list.setObjectName("sidebarNavList")
        self._nav_list.setCursor(Qt.CursorShape.PointingHandCursor)
        self._nav_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for text in self.NAV_ITEMS:
            item = QListWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._nav_list.addItem(item)
        self._nav_list.setCurrentRow(0)
        self._nav_list.currentRowChanged.connect(self.nav_changed.emit)
        layout.addWidget(self._nav_list)

        layout.addStretch()

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.theme_btn)

        self.pin_btn = QPushButton(f"{EMOJI['pin']} 置顶")
        self.pin_btn.setObjectName("pinBtn")
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.pin_btn)

        self.export_btn = QPushButton("导出 CSV")
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.setToolTip("将数据导出为 CSV 文件（Excel 可直接打开）")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.export_btn)

    # ── 账号区（Y-04）───────────────────────────────────

    def set_accounts(self, names: list[str], current: str) -> None:
        """刷新下拉列表并设置当前选中项。

        ``names`` 为业务层 list_accounts() 结果（含 current）；blockSignals
        防止程序刷新误触发 account_selected（选择信号只由用户动作产生）。
        """
        self.account_combo.blockSignals(True)
        self.account_combo.clear()
        self.account_combo.addItems(names)
        self.account_combo.setCurrentIndex(
            names.index(current) if current in names else 0
        )
        self.account_combo.blockSignals(False)

    def set_account_area_visible(self, visible: bool) -> None:
        """显示/隐藏整个账号区（注入 store 模式无账号概念时隐藏，Y-04）。"""
        self.account_title.setVisible(visible)
        self.account_combo.setVisible(visible)
        self.new_account_btn.setVisible(visible)

    @property
    def current_index(self) -> int:
        return self._nav_list.currentRow()

    def set_current_index(self, index: int) -> None:
        self._nav_list.blockSignals(True)
        self._nav_list.setCurrentRow(index)
        self._nav_list.blockSignals(False)
        self.nav_changed.emit(index)

    def apply_theme(self) -> None:
        """根据当前主题色更新侧边栏样式。"""
        from app.theme import get_color  # noqa: PLC0415

        bg = get_color("MUTED_BG")
        fg = get_color("FG_LABEL")
        sel_pill = get_color("NAV_SELECT_BG")
        sel_fg = get_color("BTN_BG")  # 选中文字用 accent 色（U-04 浅底 pill）
        accent = get_color("BTN_BG")
        nav_hover_bg = get_color("NAV_HOVER_BG")

        # U-04：选中态从「整条实心色块」改「浅底 pill + 3px accent 指示条」——
        # border-left 选中/未选中同宽（transparent vs accent），文字零位移。
        self.setStyleSheet(f"""
        #sidebar {{
            background-color: {bg};
        }}
        QListWidget#sidebarNavList {{
            background: transparent; border: none; font-size: 13px; outline: none;
        }}
        QListWidget#sidebarNavList::item {{
            padding: 12px 4px; color: {fg}; border: none;
            border-left: 3px solid transparent;
        }}
        QListWidget#sidebarNavList::item:selected {{
            background-color: {sel_pill}; color: {sel_fg}; font-weight: bold;
            border-left: 3px solid {accent};
        }}
        QListWidget#sidebarNavList::item:hover:!selected {{
            background-color: {nav_hover_bg};
        }}
        """)
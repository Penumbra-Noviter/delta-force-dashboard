"""
侧边栏导航组件：左侧导航项 + 底部操作按钮。

- 导航项（记账 / 制造 / 战备）点击切换 QStackedWidget 页面
- 底部放置主题切换、置顶、导出 CSV 按钮
"""

from __future__ import annotations

__all__ = ["Sidebar"]

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget


class Sidebar(QWidget):
    """左侧导航栏：导航项列表 + 底部操作按钮。"""

    nav_changed = Signal(int)
    NAV_ITEMS = ["📒 记账", "🔧 利润"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(0)

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

        self.pin_btn = QPushButton("📌 置顶")
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
        sel_bg = get_color("BTN_BG")
        sel_fg = get_color("BTN_FG")

        self.setStyleSheet(f"""
        #sidebar {{
            background-color: {bg};
        }}
        QListWidget#sidebarNavList {{
            background: transparent; border: none; font-size: 13px; outline: none;
        }}
        QListWidget#sidebarNavList::item {{
            padding: 16px 4px; color: {fg}; border: none;
        }}
        QListWidget#sidebarNavList::item:selected {{
            background-color: {sel_bg}; color: {sel_fg}; font-weight: bold;
        }}
        QListWidget#sidebarNavList::item:hover:!selected {{
            background-color: rgba(128, 128, 128, 0.1);
        }}
        """)
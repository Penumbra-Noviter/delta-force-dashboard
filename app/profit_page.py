"""
利润页面：制造产物推荐和兑换利润合并为单页纵向展示。

两个子模块（CraftingPage / ExchangePage）在同一可滚动页面内纵向堆叠，
无需在标签页之间切换。各自保留标题栏与刷新按钮，可独立刷新。
"""

from __future__ import annotations

__all__ = ["ProfitPage"]

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.crafting_page import CraftingPage
from app.exchange_page import ExchangePage

logger = logging.getLogger(__name__)


class ProfitPage(QWidget):
    """利润页面（QStackedWidget Page 1）。

    制造产物推荐与兑换利润纵向堆叠于同一滚动页面，避免标签页切换。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("profitPage")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 滚动容器：内容超出视口时纵向滚动，隐藏横向滚动条
        self._scroll = QScrollArea()
        self._scroll.setObjectName("profitScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # U 系列修复：QScrollArea viewport 默认绘制 palette.window 背景
        # （不随主题，用户系统深色 palette 时亮色主题下背景纯黑）——
        # QSS 选择器匹配不到 viewport（QStyleSheetStyle 也忽略 autoFillBackground），
        # 必须对 viewport 直接设内联透明样式。
        self._scroll.viewport().setStyleSheet(
            "QWidget { background-color: transparent; }"
        )

        container = QWidget()
        container.setObjectName("profitContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 8)
        container_layout.setSpacing(0)

        # 制造产物推荐（纵向不扩展，按内容高度排列）
        self.crafting_page = CraftingPage()
        self.crafting_page.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        container_layout.addWidget(self.crafting_page)

        # 兑换利润
        self.exchange_page = ExchangePage()
        self.exchange_page.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
        )
        container_layout.addWidget(self.exchange_page)

        container_layout.addStretch()

        self._scroll.setWidget(container)
        outer.addWidget(self._scroll)

    def refresh(self) -> None:
        """刷新所有子页面。"""
        self.crafting_page.refresh()
        self.exchange_page.refresh()

    def shutdown(self) -> None:
        """关闭时回收所有子页面后台线程（MainWindow.closeEvent 调用，T-01）。"""
        self.crafting_page.shutdown()
        self.exchange_page.shutdown()

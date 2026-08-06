"""
利润页面：包含制造产物推荐和兑换利润两个子模块的标签页容器。

将「制造」板块正式更名为「利润」，下设两个标签页：
- 制造产物：原制造产物推荐（CraftingPage）
- 兑换利润：子弹自选包兑换利润（ExchangePage）
"""

from __future__ import annotations

__all__ = ["ProfitPage"]

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.crafting_page import CraftingPage
from app.exchange_page import ExchangePage

logger = logging.getLogger(__name__)


class ProfitPage(QWidget):
    """利润页面（QStackedWidget Page 1），内含两个标签页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("profitPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("profitTabs")
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.setDocumentMode(True)

        # Tab 0：制造产物
        self.crafting_page = CraftingPage()
        self._tabs.addTab(self.crafting_page, "🔧 制造产物")

        # Tab 1：兑换利润
        self.exchange_page = ExchangePage()
        self._tabs.addTab(self.exchange_page, "📦 兑换利润")

        layout.addWidget(self._tabs)

    def refresh(self) -> None:
        """刷新所有子页面。"""
        self.crafting_page.refresh()
        self.exchange_page.refresh()
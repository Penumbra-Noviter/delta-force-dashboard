"""
制造产物推荐页面：展示 4 个制造台位的最新推荐产物。

数据来源于 kkrb.net API（KkrbClient.fetch_ov_data），手动刷新。
"""

from __future__ import annotations

__all__ = ["CraftingPage"]

import logging
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kkrb_client import CraftingProduct, KkrbClient, KkrbError
from formatting import format_money

logger = logging.getLogger(__name__)

_EMPTY_STATION = CraftingProduct("—", "暂无数据", 0, 0, "")


class CraftingPage(QWidget):
    """制造产物推荐页面（QStackedWidget Page 1）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = KkrbClient()
        self._products: list[CraftingProduct] = []
        self._loading = False
        self._error: str | None = None

        self._build_ui()

    # ── UI 构建 ─────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(16)

        # 标题栏
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("制造产物推荐")
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)

        title_layout.addStretch()

        self._refresh_btn = QPushButton("🔄 刷新")
        self._refresh_btn.setObjectName("refreshBtn")
        self._refresh_btn.clicked.connect(self._load_data)
        title_layout.addWidget(self._refresh_btn)

        layout.addWidget(title_bar)

        # 状态提示
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        # 4 个台位卡片（2×2 网格）
        self._card_grid = QGridLayout()
        self._card_grid.setSpacing(12)
        self._cards: list[QFrame] = []
        for i in range(4):
            card = self._build_card()
            self._cards.append(card)
            self._card_grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(self._card_grid)

        layout.addStretch()

    def _build_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("craftingCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(6)

        station = QLabel("—")
        station.setObjectName("craftStation")
        cl.addWidget(station)

        product = QLabel("暂无数据")
        product.setObjectName("craftProduct")
        product.setStyleSheet("font-size: 18px; font-weight: bold;")
        cl.addWidget(product)

        profit = QLabel("")
        profit.setObjectName("craftProfit")
        cl.addWidget(profit)

        price = QLabel("")
        price.setObjectName("craftPrice")
        cl.addWidget(price)

        sell_time = QLabel("")
        sell_time.setObjectName("craftSellTime")
        cl.addWidget(sell_time)

        return card

    # ── 数据加载 ────────────────────────────────────────

    def _load_data(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._error = None
        self._status_label.setText("🔄 加载中…")
        self._status_label.setVisible(True)
        self._refresh_btn.setEnabled(False)

        QTimer.singleShot(0, self._do_fetch)

    def _do_fetch(self) -> None:
        try:
            self._products = self._client.fetch_ov_data()
            self._error = None
            self._status_label.setVisible(False)
        except KkrbError as e:
            logger.warning("制造产物数据获取失败: %s", e)
            self._error = str(e)
            self._status_label.setText("⚠️ 数据获取失败，点击重试")
            self._status_label.setVisible(True)
            self._products = []
        except Exception as e:
            logger.error("制造产物数据获取异常: %s", e)
            self._error = str(e)
            self._status_label.setText("⚠️ 网络异常，请检查连接后重试")
            self._status_label.setVisible(True)
            self._products = []
        finally:
            self._loading = False
            self._refresh_btn.setEnabled(True)
            self._render_cards()

    def _render_cards(self) -> None:
        products = self._products or []
        # 确保 4 个卡片都有数据
        display = products[:4]
        while len(display) < 4:
            display.append(_EMPTY_STATION)

        for i, card in enumerate(self._cards):
            product = display[i]
            layout = card.layout()
            if layout is None:
                continue

            # station name
            station = layout.itemAt(0).widget()
            if isinstance(station, QLabel):
                station.setText(product.station)

            # product name
            prod = layout.itemAt(1).widget()
            if isinstance(prod, QLabel):
                prod.setText(product.product if product.product else "暂无数据")

            # profit
            profit = layout.itemAt(2).widget()
            if isinstance(profit, QLabel):
                profit.setText(f"利润：{format_money(product.profit)}")

            # ideal price
            price = layout.itemAt(3).widget()
            if isinstance(price, QLabel):
                price.setText(f"理想售价：{format_money(product.ideal_price)}")

            # sell time
            sell = layout.itemAt(4).widget()
            if isinstance(sell, QLabel):
                sell.setText(f"建议出售：{product.sell_time}")

    def refresh(self) -> None:
        """公开刷新方法（供外部调用）。"""
        self._load_data()
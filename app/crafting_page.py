"""
制造产物推荐页面：展示 4 个制造台位的最新推荐产物。

数据来源于 kkrb.net API（KkrbClient.fetch_ov_data），手动刷新。
懒加载/加载状态机/后台线程管理继承自 FetchPageBase。
"""

from __future__ import annotations

__all__ = ["CraftingPage"]

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from app.fetch_page_base import FetchPageBase
from kkrb_client import CraftingProduct
from formatting import format_money

_EMPTY_STATION = CraftingProduct("—", "暂无数据", 0, 0, "")


class CraftingPage(FetchPageBase):
    """制造产物推荐页面（QStackedWidget Page 1 的子页面）。"""

    _title = "制造产物推荐"
    _page_name = "制造产物"

    # ── 数据获取 ────────────────────────────────────────

    def _fetch(self) -> list[CraftingProduct]:
        """后台线程执行的取数函数。"""
        return self._client.fetch_ov_data()

    # ── UI 构建 ─────────────────────────────────────────

    def _build_body(self, layout: QVBoxLayout) -> None:
        """构建 4 个台位卡片（2×2 网格）。"""
        self._card_grid = QGridLayout()
        self._card_grid.setSpacing(12)
        self._cards: list[QFrame] = []
        for i in range(4):
            card = self._build_card()
            self._cards.append(card)
            self._card_grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(self._card_grid)

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

    # ── 渲染 ────────────────────────────────────────────

    def _render_data(self, data: list[CraftingProduct]) -> None:
        """将产物数据渲染到 4 个卡片。"""
        products = data or []
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
                profit.setText(f"总利润：{format_money(product.profit)}")

            # current price
            price = layout.itemAt(3).widget()
            if isinstance(price, QLabel):
                price.setText(f"当前售价：{format_money(product.ideal_price)}")

            # sell time
            sell = layout.itemAt(4).widget()
            if isinstance(sell, QLabel):
                sell.setText(f"建议出售时段：{product.sell_time}")

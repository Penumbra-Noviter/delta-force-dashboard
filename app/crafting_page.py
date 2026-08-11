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
        """构建一张台位卡：持有全部标签的直接引用（C2-04）。

        直接引用（_station_label / _product_label / _profit_label /
        _price_label / _sell_time_label）供 _render_data 按槽位更新文案，
        取代布局索引回读；空槽位由 _render_data 显式重置为占位文案
        （站名 —、产物 暂无数据、其余空串，spec 4.2.9）。
        """
        card = QFrame()
        card.setObjectName("craftingCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(6)

        card._station_label = QLabel("—")
        card._station_label.setObjectName("craftStation")
        cl.addWidget(card._station_label)

        card._product_label = QLabel("暂无数据")
        card._product_label.setObjectName("craftProduct")
        # U-02：卡片主角名归 section 档（原 18px 越过页面标题 16px 层级）
        card._product_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        cl.addWidget(card._product_label)

        card._profit_label = QLabel("")
        card._profit_label.setObjectName("craftProfit")
        cl.addWidget(card._profit_label)

        card._price_label = QLabel("")
        card._price_label.setObjectName("craftPrice")
        cl.addWidget(card._price_label)

        card._sell_time_label = QLabel("")
        card._sell_time_label.setObjectName("craftSellTime")
        cl.addWidget(card._sell_time_label)

        return card

    # ── 渲染 ────────────────────────────────────────────

    def _render_data(self, data: list[CraftingProduct]) -> None:
        """将产物数据渲染到 4 个卡片。

        前 ``len(data)`` 张卡按数据更新；空槽位显式重置为占位文案
        （站名 —、产物 暂无数据、利润/价格/时段空串）——空数据渲染
        不构造 CraftingProduct 实例（模块级假领域对象已删除）。
        """
        products = data or []
        for i, card in enumerate(self._cards):
            if i < len(products):
                product = products[i]
                card._station_label.setText(product.station or "—")
                card._product_label.setText(
                    product.product if product.product else "暂无数据"
                )
                card._profit_label.setText(
                    f"总利润：{format_money(product.profit)}"
                )
                card._price_label.setText(
                    f"当前售价：{format_money(product.ideal_price)}"
                )
                card._sell_time_label.setText(
                    f"建议出售时段：{product.sell_time}"
                )
            else:
                card._station_label.setText("—")
                card._product_label.setText("暂无数据")
                card._profit_label.setText("")
                card._price_label.setText("")
                card._sell_time_label.setText("")

    def _render_error(self) -> None:
        """错误态渲染：与空态可区分的错误文案（C2-05，spec 4.2.10）。

        站名 —、产物「加载失败，点击重试」（空态为「暂无数据」）、
        利润/价格/时段清空——用户可分辨「没数据」与「出错了」。
        """
        for card in self._cards:
            card._station_label.setText("—")
            card._product_label.setText("加载失败，点击重试")
            card._profit_label.setText("")
            card._price_label.setText("")
            card._sell_time_label.setText("")

    def apply_theme(self) -> None:
        """主题切换钩子：空操作（C1-07）。

        制造卡颜色全部由 QSS 选择器驱动（QFrame#craftingCard /
        QLabel#craftStation 等在 generate_qss 中按当前主题生成），
        卡片内联样式仅字号/字重（无颜色），无需重解析。
        """


"""
子弹自选包兑换利润页面：展示所有子弹自选包中利润最高的子弹方案。

包类型（7 种）：
  - 普通：3/4/5 级子弹自选包
  - 特殊：通行证基础/高级、进阶物流、特级物流
数据来源于 kkrb.net API（KkrbClient.fetch_ammo_package_data），手动刷新。
"""

from __future__ import annotations

__all__ = ["ExchangePage"]

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from typing import NamedTuple

from app.fetch_worker import FetchWorker
from kkrb_client import AmmoPackageItem, KkrbClient, KkrbError
from formatting import format_money

logger = logging.getLogger(__name__)

# 包类型显示配置
class _PackageConfig(NamedTuple):
    """一个子弹自选包类型的显示配置。"""
    display_name: str   # 包全名（在 API 中用作 key）
    short_name: str     # 卡片上显示的短标签
    color: str          # 标签颜色

_PACKAGE_CONFIG: list[_PackageConfig] = [
    _PackageConfig("3级子弹自选包", "3级子弹", "#6BA08A"),
    _PackageConfig("4级子弹自选包", "4级子弹", "#C08A3E"),
    _PackageConfig("5级子弹自选包", "5级子弹", "#D46A6A"),
    _PackageConfig("通行证基础子弹自选包", "通行证基础", "#7B8CFF"),
    _PackageConfig("通行证高级子弹自选包", "通行证高级", "#A58BFF"),
    _PackageConfig("进阶物流子弹自选包", "进阶物流", "#E8A33D"),
    _PackageConfig("特级物流子弹自选包", "特级物流", "#E8833D"),
]

# 每行卡片数
_COLS = 4


class ExchangePage(QWidget):
    """子弹自选包兑换利润页面（QStackedWidget 子页面）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = KkrbClient()
        self._items: list[AmmoPackageItem] = []
        self._loading = False
        self._error: str | None = None
        self._loaded_once = False
        self._worker: FetchWorker | None = None

        self._build_ui()

    def showEvent(self, event: QShowEvent) -> None:
        """首次显示时自动加载数据。"""
        super().showEvent(event)
        if not self._loaded_once:
            self._loaded_once = True
            self._load_data()

    # ── UI 构建 ─────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(16)

        # 标题栏
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("兑换利润（子弹自选包）")
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

        # 所有包卡片（网格布局，每行 4 列）
        self._card_grid = QGridLayout()
        self._card_grid.setSpacing(10)
        self._cards: list[QFrame] = []
        for i, cfg in enumerate(_PACKAGE_CONFIG):
            card = self._build_package_card(cfg.short_name, cfg.color)
            self._cards.append(card)
            self._card_grid.addWidget(card, i // _COLS, i % _COLS)
        layout.addLayout(self._card_grid)

        layout.addStretch()

    def _build_package_card(self, short_name: str, color: str) -> QFrame:
        """构建单个包类型的卡片。"""
        card = QFrame()
        card.setObjectName("exchangeCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        # 包名标签（带颜色）
        pkg_label = QLabel(short_name)
        pkg_label.setObjectName("exchangePackageLabel")
        pkg_label.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {color};"
        )
        cl.addWidget(pkg_label)

        # 子弹名
        item_name = QLabel("加载中…")
        item_name.setObjectName("exchangeItemName")
        item_name.setStyleSheet("font-size: 15px; font-weight: bold;")
        cl.addWidget(item_name)

        # 等级标签
        grade_label = QLabel("")
        grade_label.setObjectName("exchangeGradeAndCount")
        grade_label.setStyleSheet("font-size: 11px;")
        cl.addWidget(grade_label)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: rgba(128,128,128,0.15); max-height: 1px;")
        cl.addWidget(sep)

        # 利润
        profit = QLabel("")
        profit.setObjectName("exchangeProfit")
        cl.addWidget(profit)

        # 单个售价
        price = QLabel("")
        price.setObjectName("exchangePrice")
        cl.addWidget(price)

        # 总价 + 数量
        total = QLabel("")
        total.setObjectName("exchangeTotal")
        cl.addWidget(total)

        cl.addStretch()

        # 存储子控件引用
        card._item_name = item_name
        card._grade_label = grade_label
        card._profit = profit
        card._price = price
        card._total = total

        return card

    def _update_card(self, card: QFrame, item: AmmoPackageItem | None) -> None:
        """更新卡片内容。"""
        if item is None:
            card._item_name.setText("暂无数据")
            card._grade_label.setText("")
            card._profit.setText("")
            card._price.setText("")
            card._total.setText("")
            return

        card._item_name.setText(item.item_name)
        card._grade_label.setText(f"Lv.{item.item_grade}  ×{item.item_count}")
        card._profit.setText(f"利润：{format_money(item.profit)}")
        card._price.setText(f"单价：{format_money(item.single_price)}")
        card._total.setText(f"总价：{format_money(item.total_price)}")

    # ── 数据加载 ────────────────────────────────────────

    def _load_data(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._error = None
        self._status_label.setText("🔄 加载中…")
        self._status_label.setVisible(True)
        self._refresh_btn.setEnabled(False)

        self._worker = FetchWorker(self._client.fetch_ammo_package_data)
        self._worker.done.connect(self._on_fetch_done)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_fetch_done(self, items: list[AmmoPackageItem]) -> None:
        self._loaded_once = True
        self._items = items
        self._error = None
        self._status_label.setVisible(False)
        self._loading = False
        self._refresh_btn.setEnabled(True)
        self._render_cards()

    def _on_fetch_error(self, e: Exception) -> None:
        if isinstance(e, KkrbError):
            logger.warning("弹药包数据获取失败: %s", e)
            self._status_label.setText("⚠️ 数据获取失败，点击重试")
        else:
            logger.error("弹药包数据获取异常: %s", e)
            self._status_label.setText("⚠️ 网络异常，请检查连接后重试")
        self._error = str(e)
        self._status_label.setVisible(True)
        self._items = []
        self._loading = False
        self._refresh_btn.setEnabled(True)
        self._render_cards()

    def _render_cards(self) -> None:
        """为每个包类型选取利润最高的条目并渲染卡片。"""
        # 按包名分组，每组取利润最高
        best_by_package: dict[str, AmmoPackageItem] = {}
        for item in self._items:
            pkg = item.package_name
            if pkg not in best_by_package or item.profit > best_by_package[pkg].profit:
                best_by_package[pkg] = item

        # 按配置顺序更新卡片
        for i, cfg in enumerate(_PACKAGE_CONFIG):
            if i >= len(self._cards):
                break
            best = best_by_package.get(cfg.display_name)
            self._update_card(self._cards[i], best)

    def refresh(self) -> None:
        """公开刷新方法（供外部调用）。"""
        self._load_data()
"""
子弹自选包兑换利润页面：展示 3/4/5 级中利润最高的子弹兑换方案。

数据来源于 kkrb.net API（KkrbClient.fetch_ammo_package_data），手动刷新。
"""

from __future__ import annotations

__all__ = ["ExchangePage"]

import logging
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kkrb_client import AmmoPackageItem, KkrbClient, KkrbError
from formatting import format_money

logger = logging.getLogger(__name__)

_GRADE_LABELS = {3: "3级子弹", 4: "4级子弹", 5: "5级子弹"}
_GRADE_COLORS = {3: "#6BA08A", 4: "#C08A3E", 5: "#D46A6A"}


class ExchangePage(QWidget):
    """子弹自选包兑换利润页面（QStackedWidget 子页面）。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = KkrbClient()
        self._items: list[AmmoPackageItem] = []
        self._loading = False
        self._error: str | None = None
        self._loaded_once = False

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

        # 3 个等级卡片（水平排列）
        self._card_row = QHBoxLayout()
        self._card_row.setSpacing(12)
        self._cards: dict[int, QFrame] = {}
        for grade in (3, 4, 5):
            card = self._build_grade_card(grade)
            self._cards[grade] = card
            self._card_row.addWidget(card, 1)
        layout.addLayout(self._card_row)

        layout.addStretch()

    def _build_grade_card(self, grade: int) -> QFrame:
        """构建单个等级卡片。"""
        card = QFrame()
        card.setObjectName("exchangeCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(8)

        # 等级标签（带颜色）
        grade_label = QLabel(_GRADE_LABELS.get(grade, f"{grade}级子弹"))
        grade_label.setObjectName("exchangeGradeLabel")
        color = _GRADE_COLORS.get(grade, "#6BA08A")
        grade_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {color};"
        )
        cl.addWidget(grade_label)

        # 子弹名
        item_name = QLabel("加载中…")
        item_name.setObjectName("exchangeItemName")
        item_name.setStyleSheet("font-size: 16px; font-weight: bold;")
        cl.addWidget(item_name)

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

        # 总价
        total = QLabel("")
        total.setObjectName("exchangeTotal")
        cl.addWidget(total)

        # 包名
        pkg = QLabel("")
        pkg.setObjectName("exchangePackage")
        pkg.setStyleSheet("font-size: 11px;")
        cl.addWidget(pkg)

        cl.addStretch()

        # 存储子控件引用
        card._grade = grade
        card._item_name = item_name
        card._profit = profit
        card._price = price
        card._total = total
        card._pkg = pkg

        return card

    def _update_card(self, card: QFrame, item: AmmoPackageItem | None) -> None:
        """更新卡片内容。"""
        if item is None:
            card._item_name.setText("暂无数据")
            card._profit.setText("")
            card._price.setText("")
            card._total.setText("")
            card._pkg.setText("")
            return

        card._item_name.setText(item.item_name)
        card._profit.setText(f"利润：{format_money(item.profit)}")
        card._price.setText(f"单个售价：{format_money(item.single_price)}")
        card._total.setText(f"总价：{format_money(item.total_price)}")
        card._pkg.setText(f"来源：{item.package_name} × {item.item_count}")

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
            self._items = self._client.fetch_ammo_package_data()
            self._error = None
            self._status_label.setVisible(False)
        except KkrbError as e:
            logger.warning("弹药包数据获取失败: %s", e)
            self._error = str(e)
            self._status_label.setText("⚠️ 数据获取失败，点击重试")
            self._status_label.setVisible(True)
            self._items = []
        except Exception as e:
            logger.error("弹药包数据获取异常: %s", e)
            self._error = str(e)
            self._status_label.setText("⚠️ 网络异常，请检查连接后重试")
            self._status_label.setVisible(True)
            self._items = []
        finally:
            self._loading = False
            self._refresh_btn.setEnabled(True)
            self._render_cards()

    def _render_cards(self) -> None:
        """为每个等级选取利润最高的条目并渲染卡片。"""
        # 按等级分组
        best_by_grade: dict[int, AmmoPackageItem] = {}
        for item in self._items:
            g = item.item_grade
            if g not in best_by_grade or item.profit > best_by_grade[g].profit:
                best_by_grade[g] = item

        # 更新卡片
        for grade in (3, 4, 5):
            card = self._cards.get(grade)
            if card is None:
                continue
            best = best_by_grade.get(grade)
            self._update_card(card, best)

    def refresh(self) -> None:
        """公开刷新方法（供外部调用）。"""
        self._load_data()
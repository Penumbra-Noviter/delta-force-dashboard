"""
密码门页面：展示 kkrb.net 每日各图密码门密码（BD-02，桌面端第三模块）。

数据来源于 kkrb.net API（KkrbClient.fetch_bonus_door_data，az3r6 已在
client 层剔除），手动刷新。懒加载/加载状态机/后台线程管理继承自
FetchPageBase。网格卡片动态构建：数据量小（当前 6 张图固定，未来可能
变化），_render_data 清空网格按数据重建，重建成本可忽略。

**不展示更新时间**（v5 拍板）：每卡 = 地图名 + 密码大字；位置图明确不做。
"""

from __future__ import annotations

__all__ = ["BonusDoorPage"]

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from app.fetch_page_base import FetchPageBase
from kkrb_client import BonusDoorItem

#: 网格列数（当前 6 卡 → 3×2）。
_COLS = 3


class BonusDoorPage(FetchPageBase):
    """密码门页面（QStackedWidget Page 2）。"""

    _title = "密码门"
    _page_name = "密码门"

    # ── 数据获取 ────────────────────────────────────────

    def _fetch(self) -> list[BonusDoorItem]:
        """后台线程执行的取数函数。"""
        return self._client.fetch_bonus_door_data()

    # ── UI 构建 ─────────────────────────────────────────

    def _build_body(self, layout: QVBoxLayout) -> None:
        """构建动态卡片网格 + 占位标签（空态/错误态共用，BD-02）。"""
        self._card_grid = QGridLayout()
        self._card_grid.setSpacing(12)
        self._cards: list[QFrame] = []

        self._placeholder = QLabel("暂无数据")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setVisible(False)

        layout.addLayout(self._card_grid)
        layout.addWidget(self._placeholder)

    def _build_card(self, item: BonusDoorItem) -> QFrame:
        """构建一张地图密码卡：地图名 + 密码大字（直接引用，C2-04 惯例）。

        密码大字字号/字重为内联样式（34px bold，与 KPI 同字号体系），
        颜色全部 QSS 选择器驱动（#bonusDoorPassword → TEXT_PRIMARY），
        无构建期冻结色（C1 契约）。

        文本入参 ``or ""`` 兜底（BD-债3）：QLabel 构造入参契约是 str，
        None 字段仅 stub 手造可达（真实路径 parse 恒产 str），纯防御。
        """
        card = QFrame()
        card.setObjectName("bonusDoorCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(6)

        card._map_label = QLabel(item.name or "")
        card._map_label.setObjectName("bonusDoorMap")
        cl.addWidget(card._map_label)

        card._password_label = QLabel(item.password or "")
        card._password_label.setObjectName("bonusDoorPassword")
        card._password_label.setStyleSheet(
            "font-size: 34px; font-weight: bold;"
        )
        cl.addWidget(card._password_label)

        return card

    def _rebuild_cards(self, items: list[BonusDoorItem]) -> None:
        """清空卡片网格并按数据重建（数据量小，重建成本可忽略）。

        None 条目跳过（BD-债批次评审②）：list 内 None 仅 stub 手造可达，
        真实路径 parse 恒产 BonusDoorItem，纯防御。
        """
        while self._card_grid.count():
            widget = self._card_grid.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        self._cards = []
        for i, item in enumerate(items):
            if item is None:
                continue
            card = self._build_card(item)
            self._cards.append(card)
            self._card_grid.addWidget(card, i // _COLS, i % _COLS)

    # ── 渲染 ────────────────────────────────────────────

    def _show_placeholder(self, text: str) -> None:
        """显示占位文案（空态/错误态共用，AA-02 思路同 crafting _reset_card）。"""
        self._placeholder.setText(text)
        self._placeholder.setVisible(True)

    def _render_data(self, data: list[BonusDoorItem]) -> None:
        """按数据动态重建卡片网格；空数据 → 显式占位「暂无数据」。"""
        items = data or []
        self._rebuild_cards(items)
        if items:
            self._placeholder.setVisible(False)
        else:
            self._show_placeholder("暂无数据")

    def _render_error(self) -> None:
        """错误态渲染：占位「加载失败，点击重试」（与空态可区分，C2-05）。"""
        self._rebuild_cards([])
        self._show_placeholder("加载失败，点击重试")

    def apply_theme(self) -> None:
        """主题切换钩子：空操作（C1-07）。

        密码门卡颜色全部由 QSS 选择器驱动（QFrame#bonusDoorCard /
        QLabel#bonusDoorMap / QLabel#bonusDoorPassword 在 generate_qss
        中按当前主题生成），卡片内联样式仅字号/字重（无颜色），无需重解析。
        """

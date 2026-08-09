"""
子弹自选包兑换利润页面：展示所有子弹自选包中利润最高的子弹方案。

包类型（7 种）：
  - 普通：3/4/5 级子弹自选包
  - 特殊：通行证基础/高级、进阶物流、特级物流
数据来源于 kkrb.net API（KkrbClient.fetch_ammo_package_data），手动刷新。
懒加载/加载状态机/后台线程管理继承自 FetchPageBase。
"""

from __future__ import annotations

__all__ = ["ExchangePage"]

from typing import NamedTuple

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from app.fetch_page_base import FetchPageBase
from app.theme import get_color
from kkrb_client import AmmoPackageItem
from formatting import format_money

# 包类型显示配置
class _PackageConfig(NamedTuple):
    """一个子弹自选包类型的显示配置。"""
    display_name: str   # 包全名（在 API 中用作 key）
    short_name: str     # 卡片上显示的短标签
    color: str          # 标签颜色：装饰色主题键（PACKAGE_COLOR_0~6，运行期解析）

# 7 种包全部走单一装饰键 PACKAGE_COLOR_0~6（U-03 键名如实：无 CHART_SERIES_* 双套键）；
# 色值随主题联动。无 hex 回退路径——get_color 缺失键返回 ""，键完整性由
# tests/test_theme_roles.py 在双主题下断言（防漏改静默失效）。
_PACKAGE_CONFIG: list[_PackageConfig] = [
    _PackageConfig("3级子弹自选包", "3级子弹", "PACKAGE_COLOR_2"),
    _PackageConfig("4级子弹自选包", "4级子弹", "PACKAGE_COLOR_1"),
    _PackageConfig("5级子弹自选包", "5级子弹", "PACKAGE_COLOR_3"),
    _PackageConfig("通行证基础子弹自选包", "通行证基础", "PACKAGE_COLOR_0"),
    _PackageConfig("通行证高级子弹自选包", "通行证高级", "PACKAGE_COLOR_4"),
    _PackageConfig("进阶物流子弹自选包", "进阶物流", "PACKAGE_COLOR_5"),
    _PackageConfig("特级物流子弹自选包", "特级物流", "PACKAGE_COLOR_6"),
]

# 每行卡片数
_COLS = 4


def _resolve_color(color: str) -> str:
    """主题色键 → 当前主题色值（运行期解析，非 import 期）。

    无 hex 回退路径：get_color 对缺失键返回 ""（无效色），
    全部包色键由 tests/test_theme_roles.py 断言双主题存在，防漏改静默失效。
    """
    return get_color(color)


class ExchangePage(FetchPageBase):
    """子弹自选包兑换利润页面（QStackedWidget 子页面）。"""

    _title = "兑换利润（子弹自选包）"
    _page_name = "弹药包"

    # ── 数据获取 ────────────────────────────────────────

    def _fetch(self) -> list[AmmoPackageItem]:
        """后台线程执行的取数函数。"""
        return self._client.fetch_ammo_package_data()

    # ── UI 构建 ─────────────────────────────────────────

    def _build_body(self, layout: QVBoxLayout) -> None:
        """构建所有包卡片（网格布局，每行 4 列）。"""
        self._card_grid = QGridLayout()
        self._card_grid.setSpacing(10)
        self._cards: list[QFrame] = []
        for i, cfg in enumerate(_PACKAGE_CONFIG):
            card = self._build_package_card(cfg.short_name, _resolve_color(cfg.color))
            self._cards.append(card)
            self._card_grid.addWidget(card, i // _COLS, i % _COLS)
        layout.addLayout(self._card_grid)

    def _build_package_card(self, short_name: str, color: str) -> QFrame:
        """构建单个包类型的卡片。"""
        card = QFrame()
        card.setObjectName("exchangeCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        # 包名标签（带颜色）；字号/字重由 QSS exchangePackageLabel 统一
        # （15px/700），内联只留运行期解析的动态色（主题双轨收敛）
        pkg_label = QLabel(short_name)
        pkg_label.setObjectName("exchangePackageLabel")
        pkg_label.setStyleSheet(f"color: {color};")
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

        # 分隔线（主题 SEPARATOR 色，随主题联动）
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"background-color: {get_color('SEPARATOR')}; max-height: 1px;"
        )
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
        card._pkg_label = pkg_label
        card._item_name = item_name
        card._grade_label = grade_label
        card._profit = profit
        card._price = price
        card._total = total

        return card

    def apply_theme(self) -> None:
        """主题切换后重解析 7 个包标签色（运行期 get_color，防构建期冻结）。

        包标签色是内联样式，构建期解析会冻结在构建时主题；亮暗色板分离后
        残留即失效（评审修复，U-03）。由 main_window.refresh_theme 调用，
        模式同 chart_widget.apply_theme：增量更新，不销毁重建。
        """
        for i, cfg in enumerate(_PACKAGE_CONFIG):
            if i >= len(self._cards):
                break
            self._cards[i]._pkg_label.setStyleSheet(
                f"color: {_resolve_color(cfg.color)};"
            )

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

    # ── 渲染 ────────────────────────────────────────────

    def _render_data(self, data: list[AmmoPackageItem]) -> None:
        """为每个包类型选取利润最高的条目并渲染卡片。"""
        # 按包名分组，每组取利润最高
        best_by_package: dict[str, AmmoPackageItem] = {}
        for item in data:
            pkg = item.package_name
            if pkg not in best_by_package or item.profit > best_by_package[pkg].profit:
                best_by_package[pkg] = item

        # 按配置顺序更新卡片
        for i, cfg in enumerate(_PACKAGE_CONFIG):
            if i >= len(self._cards):
                break
            best = best_by_package.get(cfg.display_name)
            self._update_card(self._cards[i], best)

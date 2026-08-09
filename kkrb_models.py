"""
kkrb.net API 数据模型与异常（零依赖叶子）。

模型被解析模块（kkrb_parsing）、客户端（kkrb_client）与 UI 页共同引用，
独立成叶子避免循环 import（仿 signals.py 先例：零依赖叶子收敛共享类型）。
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["AmmoPackageItem", "CraftingProduct", "KkrbError"]


@dataclass(frozen=True)
class CraftingProduct:
    """制造产物推荐数据。"""

    station: str          # 台位名（技术中心/工作台/制药台/防具台）
    product: str          # 产物名
    profit: int           # 单件总利润（当前售价 - 材料成本）
    ideal_price: int      # 当前单个售价
    sell_time: str        # 建议出售时段（如「晚上8点」「上午6点」）


@dataclass(frozen=True)
class AmmoPackageItem:
    """子弹自选包兑换利润数据。"""

    package_name: str        # 包名（如「3级子弹自选包」）
    item_name: str           # 子弹名（如「5.7x28mm L191」）
    item_grade: int          # 等级（3/4/5）
    item_count: int          # 数量
    single_price: int        # 单个售价
    total_price: int         # 总价
    profit: int              # 利润


class KkrbError(Exception):
    """kkrb.net API 请求失败。"""

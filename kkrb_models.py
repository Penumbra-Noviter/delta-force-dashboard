"""
kkrb.net API 数据模型与异常（零依赖叶子）。

模型被解析模块（kkrb_parsing）、客户端（kkrb_client）与 UI 页共同引用，
独立成叶子避免循环 import（仿 signals.py 先例：零依赖叶子收敛共享类型）。
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AmmoPackageItem",
    "BonusDoorItem",
    "BONUS_DOOR_NAMES",
    "CraftingProduct",
    "KkrbError",
]


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


@dataclass(frozen=True)
class BonusDoorItem:
    """密码门地图条目（BD-01，getBonusDoorData 单图数据）。

    字段全为 str（密码/时间戳按原样字符串传递，不做类型转换——
    updated 为 ``YYYYMMDDHHMMSS`` 时间戳，展示层不展示（v5 拍板）。
    """

    key: str                 # 地图键（如 db/cgxg/bks）
    name: str                # 中文地图名（来自 BONUS_DOOR_NAMES 映射）
    password: str            # 当日密码（缺省空串）
    updated: str             # 密码更新时间戳（缺省空串）


#: 地图键 → 中文名映射（§5.1 实测；页面单源）。
#: 定义顺序即输出顺序（解析稳定序）；kkrb 新增地图需在此扩展。
BONUS_DOOR_NAMES: dict[str, str] = {
    "db": "零号大坝",
    "cgxg": "长弓溪谷",
    "bks": "巴克什",
    "htjd": "航天基地",
    "cxjy": "潮汐监狱",
    "az3": "AZ3",
    "az3r6": "AZ3彩六联动房",
}


class KkrbError(Exception):
    """kkrb.net API 请求失败。"""

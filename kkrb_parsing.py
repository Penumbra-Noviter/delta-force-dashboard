"""
kkrb.net API 响应解析（纯函数模块，零网络依赖）。

从 kkrb_client 拆出（架构深化候选 1）：两套响应解析是数据链路中
最易被畸形输入击穿的部分，独立后可脱离网络直接单测（畸形矩阵）。
KkrbClient 保留会话/传输/缓存，这里只做「响应数据 → 领域模型」。
"""

from __future__ import annotations

__all__ = [
    "parse_ammo_package_response",
    "parse_bonus_door_response",
    "parse_ov_response",
]

import logging
from typing import Any

from kkrb_models import (
    AmmoPackageItem,
    BonusDoorItem,
    BONUS_DOOR_NAMES,
    CraftingProduct,
    KkrbError,
)

logger = logging.getLogger(__name__)


def parse_ov_response(data: Any) -> list[CraftingProduct]:
    """解析 getOVData 响应为制造产物列表（按利润降序）。

    实际格式：
    {
        "code": 1,
        "data": {
            "spData": {
                "tech":     { "placeName": "技术中心", "itemName": "...",
                              "profit": 24669, "singlePrice": 39077,
                              "yesterdayHighestTime": "晚上8点",
                              "totalMaterialLists": [...], "totalMaterialValue": 10109 },
                "workbench": { ... },
                "pharmacy":  { ... },
                "armory":    { ... },
            }
        }
    }

    Args:
        data: _post_json 的产物（任意 JSON 值）。

    Returns:
        台位产物列表；顶层非 dict 抛 KkrbError；结构缺失/畸形条目跳过。
    """
    if not isinstance(data, dict):
        raise KkrbError(f"OV 数据格式异常: 期望 dict，got {type(data).__name__}")

    raw = data.get("data", {})
    if isinstance(raw, dict):
        raw = raw.get("spData", {})

    if not isinstance(raw, dict):
        return []

    products: list[CraftingProduct] = []
    for _place_key, station in raw.items():
        if not isinstance(station, dict):
            continue

        products.append(
            CraftingProduct(
                station=str(station.get("placeName", _place_key)),
                product=str(station.get("itemName", "")),
                # 总利润（当前售价 - 材料成本）
                profit=_int_or_zero(station.get("profit")),
                # 当前单个售价
                ideal_price=_int_or_zero(station.get("singlePrice")),
                # 昨日最高价出现时段
                sell_time=str(station.get("yesterdayHighestTime", "")),
            )
        )

    products.sort(key=lambda p: p.profit, reverse=True)
    return products


def parse_ammo_package_response(data: Any) -> list[AmmoPackageItem]:
    """解析 getAmmoPackageData 响应为子弹包条目列表（按利润降序）。

    实际格式：
    {
        "code": 1,
        "data": {
            "cn": [...],
            "en": [...],
            "version": "..."
        }
    }

    每个条目格式：
    {
        "packageName": "3级子弹自选包",
        "itemName": "5.7x28mm L191",
        "itemGrade": 3,
        "itemCount": 200,
        "singlePrice": 555,
        "totalPrice": 111000,
        "profit": 98790
    }

    Args:
        data: _post_json 的产物（任意 JSON 值）。

    Returns:
        子弹包条目列表；顶层非 dict 抛 KkrbError；结构缺失/畸形条目跳过。
    """
    if not isinstance(data, dict):
        raise KkrbError(
            f"弹药包数据格式异常: 期望 dict，got {type(data).__name__}"
        )

    raw = data.get("data", {})
    if not isinstance(raw, dict):
        return []

    items: list[AmmoPackageItem] = []
    for region in ("cn",):
        region_data = raw.get(region, [])
        if not isinstance(region_data, list):
            continue
        for entry in region_data:
            if not isinstance(entry, dict):
                continue
            items.append(
                AmmoPackageItem(
                    package_name=str(entry.get("packageName", "")),
                    item_name=str(entry.get("itemName", "")),
                    item_grade=_int_or_zero(entry.get("itemGrade")),
                    item_count=_int_or_zero(entry.get("itemCount")),
                    single_price=_int_or_zero(entry.get("singlePrice")),
                    total_price=_int_or_zero(entry.get("totalPrice")),
                    profit=_int_or_zero(entry.get("profit")),
                )
            )

    # 按利润降序排列
    items.sort(key=lambda p: p.profit, reverse=True)
    return items


def parse_bonus_door_response(data: Any) -> list[BonusDoorItem]:
    """解析 getBonusDoorData 响应为密码门条目列表（BD-01）。

    实际格式：
    {
        "code": 1,
        "data": {
            "db":    { "password": "870140", "updated": "20260813000000",
                       "overridden": false },
            "cgxg":  { ... },
            ...
        }
    }

    输出按 ``BONUS_DOOR_NAMES`` 定义顺序（稳定顺序，与响应键序无关）；
    **映射外键跳过并 logger.warning**（BD-债2：kkrb 新增地图时需扩展
    kkrb_models.BONUS_DOOR_NAMES 映射，单源契约 §5.1，未知键留日志）。
    本函数不剔除 ``az3r6``：排除策略（两端一致硬排除）单点落在
    kkrb_client.fetch_bonus_door_data（§5.2）。

    Args:
        data: _post_json 的产物（任意 JSON 值）。

    Returns:
        地图条目列表；顶层非 dict 抛 KkrbError；业务失败（code 存在且
        != 1）抛 KkrbError（消息携带响应 msg）；data 缺失/非 dict → []；
        畸形条目（非 dict）跳过；password/updated 缺省空串。
    """
    if not isinstance(data, dict):
        raise KkrbError(f"密码门数据格式异常: 期望 dict，got {type(data).__name__}")

    code = data.get("code")
    if code is not None and code != 1:
        # BD-债1：业务失败（如 {"code": 0, "msg": "..."}）不能被吞成「暂无数据」
        msg = data.get("msg", "")
        suffix = f": {msg}" if msg else ""
        raise KkrbError(f"密码门业务失败{suffix}")

    raw = data.get("data", {})
    if not isinstance(raw, dict):
        return []

    # BD-债2：映射外键静默跳过不可观测——未知键留 warning（键名可读，排序稳定）
    unknown_keys = sorted(str(key) for key in set(raw) - set(BONUS_DOOR_NAMES))
    if unknown_keys:
        logger.warning(
            "密码门未知地图键（需扩展 BONUS_DOOR_NAMES）: %s",
            ", ".join(unknown_keys),
        )

    items: list[BonusDoorItem] = []
    for key, name in BONUS_DOOR_NAMES.items():
        entry = raw.get(key)
        if not isinstance(entry, dict):
            continue
        items.append(
            BonusDoorItem(
                key=key,
                name=name,
                password=str(entry.get("password") or ""),
                updated=str(entry.get("updated") or ""),
            )
        )
    return items


def _int_or_zero(value: Any) -> int:
    """安全转为 int，失败返回 0。"""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

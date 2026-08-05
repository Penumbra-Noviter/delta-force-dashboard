"""
kkrb.net API 客户端：获取制造产物推荐和卡战备方案数据。

纯 stdlib 实现（urllib.request + http.cookiejar），零外部依赖。
"""

from __future__ import annotations

__all__ = [
    "CraftingProduct",
    "GearItem",
    "GearScheme",
    "KkrbClient",
    "KkrbError",
]

import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from typing import Any
from urllib.request import HTTPCookieProcessor, Request, build_opener

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.kkrb.net"
_OV_ENDPOINT = f"{_BASE_URL}/getOVData"
_CPV_ENDPOINT = f"{_BASE_URL}/getCPVData"
_TIMEOUT = 10


# ── 数据模型 ────────────────────────────────────────────


@dataclass(frozen=True)
class CraftingProduct:
    """制造产物推荐数据。"""

    station: str          # 台位名（技术中心/工作台/制药台/防具台）
    product: str          # 产物名
    profit: int           # 每小时利润（最高等级）
    ideal_price: int      # 材料总成本
    sell_time: str        # 生产耗时


@dataclass(frozen=True)
class GearItem:
    """卡战备方案中的单个装备项。"""

    name: str             # 装备名
    cost: int             # 花费
    battle_value: int     # 战备值
    source: str           # 来源（市场/兑换等）
    wear: str = ""        # 磨损度（API 暂不提供）


@dataclass(frozen=True)
class GearScheme:
    """卡战备方案。"""

    title: str              # 方案标题
    total_cost: int         # 总花费
    final_bv: int           # 最终战备值
    items: list[GearItem]   # 装备清单


# ── 自定义异常 ──────────────────────────────────────────


class KkrbError(Exception):
    """kkrb.net API 请求失败。"""


# ── 客户端 ──────────────────────────────────────────────


class KkrbClient:
    """kkrb.net API 客户端。

    用法：
        client = KkrbClient()
        products = client.fetch_ov_data()
        schemes = client.fetch_cpv_data()
    """

    def __init__(self) -> None:
        self._cookie_jar = CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self._cookie_jar))
        self._csrf_token: str | None = None

    # ── 公开接口 ────────────────────────────────────────

    def fetch_ov_data(self) -> list[CraftingProduct]:
        """获取制造产物推荐数据。

        Returns:
            4 个台位的 CraftingProduct 列表，按利润降序排列。

        Raises:
            KkrbError: 网络请求失败或数据解析失败。
        """
        data = self._post_json(_OV_ENDPOINT)
        return self._parse_ov_response(data)

    def fetch_cpv_data(self, tier: int | None = None) -> dict[int, list[GearScheme]]:
        """获取卡战备方案数据。

        Args:
            tier: 可选，指定战备档位（如 112500）。不传则返回所有档位。

        Returns:
            {档位: [GearScheme, ...]} 的映射。

        Raises:
            KkrbError: 网络请求失败或数据解析失败。
        """
        data = self._post_json(_CPV_ENDPOINT)
        return self._parse_cpv_response(data, tier)

    # ── CSRF 管理 ───────────────────────────────────────

    def _ensure_csrf(self) -> str:
        """获取 CSRF token（首次通过首页→getMenu 两步获取，后续缓存复用）。"""
        if self._csrf_token is not None:
            return self._csrf_token

        # Step 1: 访问首页 → 拿到 PHPSESSID cookie
        try:
            req = Request(_BASE_URL)
            req.add_header("User-Agent", self._user_agent())
            req.add_header("X-Requested-With", "XMLHttpRequest")
            self._opener.open(req, timeout=_TIMEOUT)
        except (OSError, ValueError) as e:
            logger.warning("首页访问失败: %s", e)
            return ""

        # Step 2: POST /getMenu → 服务端设置 csrf_token cookie
        try:
            menu_data = urllib.parse.urlencode({"globalData": "false"}).encode()
            req = Request(f"{_BASE_URL}/getMenu", data=menu_data, method="POST")
            req.add_header("User-Agent", self._user_agent())
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            req.add_header("X-Requested-With", "XMLHttpRequest")
            self._opener.open(req, timeout=_TIMEOUT)
        except (OSError, ValueError) as e:
            logger.warning("getMenu 请求失败: %s", e)
            return ""

        # Step 3: 从 cookie jar 提取 csrf_token
        for c in self._cookie_jar:
            if c.name == "csrf_token":
                self._csrf_token = c.value
                logger.info("CSRF token 已获取")
                return self._csrf_token

        logger.warning("cookie 中未找到 csrf_token")
        return ""

    # ── HTTP 请求 ───────────────────────────────────────

    def _post_json(self, url: str) -> Any:
        """发送 POST 请求并解析 JSON 响应。"""
        token = self._ensure_csrf()
        headers = {
            "User-Agent": self._user_agent(),
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": token,
            "X-Requested-With": "XMLHttpRequest",
        }
        data = b""
        req = Request(url, data=data, headers=headers, method="POST")
        try:
            with self._opener.open(req, timeout=_TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return self._parse_json(body)
        except (OSError, ValueError) as e:
            msg = f"POST {url} 失败: {e}"
            logger.error(msg)
            raise KkrbError(msg) from e

    # ── 解析 ────────────────────────────────────────────

    @staticmethod
    def _parse_json(body: str) -> Any:
        """安全解析 JSON，处理 kkrb.net 的 BOM 和异常格式。"""
        text = body.lstrip("﻿").strip()
        if not text:
            raise KkrbError("空响应")
        import json  # noqa: PLC0415

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise KkrbError(f"JSON 解析失败: {e}") from e

    @staticmethod
    def _parse_ov_response(data: Any) -> list[CraftingProduct]:
        """解析 getOVData 响应。

        实际格式：
        {
            "code": 1,
            "data": {
                "spData": {
                    "tech":     { "placeName": "技术中心", "itemName": "...", "productionTime": 6,
                                  "itemForge": [{"hourlyProfit": 2762, ...}, ...],
                                  "totalMaterialLists": [{"totalPrice": 18309, ...}, ...] },
                    "workbench": { ... },
                    "pharmacy":  { ... },
                    "armory":    { ... },
                }
            }
        }
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

            # 取最高等级 hourlyProfit
            hourly_profit = 0
            for f in station.get("itemForge", []):
                if isinstance(f, dict):
                    hp = _int_or_zero(f.get("hourlyProfit"))
                    if hp > hourly_profit:
                        hourly_profit = hp

            # 材料总成本
            total_material_cost = 0
            for mat in station.get("totalMaterialLists", []):
                if isinstance(mat, dict):
                    total_material_cost += _int_or_zero(mat.get("totalPrice"))

            prod_time = station.get("productionTime", "")

            products.append(
                CraftingProduct(
                    station=str(station.get("placeName", _place_key)),
                    product=str(station.get("itemName", "")),
                    profit=hourly_profit,
                    ideal_price=total_material_cost,
                    sell_time=f"{prod_time}小时" if prod_time else "",
                )
            )

        products.sort(key=lambda p: p.profit, reverse=True)
        return products

    @staticmethod
    def _parse_cpv_response(data: Any, filter_tier: int | None = None) -> dict[int, list[GearScheme]]:
        """解析 getCPVData 响应。

        实际格式：
        {
            "code": 1,
            "data": [
                {
                    "targetValue": 112500,
                    "totalHafCost": 104854,
                    "currentValue": 112564,
                    "schemeType": "market",
                    "schemeItems": [
                        { "objectName": "M870霰弹枪", "costHafCoin": 5000, "currentValue": 4733, "from": "市场" },
                        ...
                    ]
                },
                ...
            ]
        }
        """
        if not isinstance(data, dict):
            raise KkrbError(f"CPV 数据格式异常: 期望 dict，got {type(data).__name__}")

        tiers = data.get("data", [])
        if not isinstance(tiers, list):
            if isinstance(tiers, dict) and not tiers:
                return {}
            raise KkrbError(f"CPV 数据格式异常: 期望列表，got {type(tiers).__name__}")

        result: dict[int, list[GearScheme]] = {}
        for tier_item in tiers:
            if not isinstance(tier_item, dict):
                continue
            try:
                tier_value = int(tier_item.get("targetValue", 0))
            except (ValueError, TypeError):
                continue
            if filter_tier is not None and tier_value != filter_tier:
                continue

            if tier_value not in result:
                result[tier_value] = []

            items_raw = tier_item.get("schemeItems", [])
            items = [
                GearItem(
                    name=str(it.get("objectName", "")),
                    cost=_int_or_zero(it.get("costHafCoin")),
                    battle_value=_int_or_zero(it.get("currentValue")),
                    source=str(it.get("from", "")),
                )
                for it in items_raw
                if isinstance(it, dict)
            ]

            scheme_idx = len(result[tier_value]) + 1
            result[tier_value].append(
                GearScheme(
                    title=f"方案 #{scheme_idx}",
                    total_cost=_int_or_zero(tier_item.get("totalHafCost")),
                    final_bv=_int_or_zero(tier_item.get("currentValue")),
                    items=items,
                )
            )

        return result

    # ── 辅助 ────────────────────────────────────────────

    @staticmethod
    def _user_agent() -> str:
        return "ProfitCalculator/1.0"

    def reset(self) -> None:
        """重置 CSRF token 和 cookie jar（强制下次请求重新认证）。"""
        self._csrf_token = None
        self._cookie_jar.clear()


def _int_or_zero(value: Any) -> int:
    """安全转为 int，失败返回 0。"""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
"""
kkrb.net API 客户端：获取制造产物推荐和卡战备方案数据。

纯 stdlib 实现（urllib.request），零外部依赖。
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
import re
import urllib.request
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.kkrb.net"
_OV_ENDPOINT = f"{_BASE_URL}/getOVData"
_CPV_ENDPOINT = f"{_BASE_URL}/getCPVData"
_CSRF_RE = re.compile(r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)')
_TIMEOUT = 10


# ── 数据模型 ────────────────────────────────────────────


@dataclass(frozen=True)
class CraftingProduct:
    """制造产物推荐数据。"""

    station: str          # 台位名（技术中心/工作台/制药台/防具台）
    product: str          # 产物名
    profit: int           # 当前利润
    ideal_price: int      # 理想售价
    sell_time: str        # 建议出售时间


@dataclass(frozen=True)
class GearItem:
    """卡战备方案中的单个装备项。"""

    name: str             # 装备名
    cost: int             # 花费
    battle_value: int     # 战备值
    source: str           # 来源（市场/兑换等）
    wear: str = ""        # 磨损度（如「全新」「破损」）


@dataclass(frozen=True)
class GearScheme:
    """卡战备方案。"""

    title: str              # 方案标题（方案 #1, #2...）
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
        """获取 CSRF token（首次从首页 HTML 提取，后续缓存复用）。"""
        if self._csrf_token is not None:
            return self._csrf_token
        try:
            req = urllib.request.Request(_BASE_URL)
            req.add_header("User-Agent", self._user_agent())
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            m = _CSRF_RE.search(html)
            if m:
                self._csrf_token = m.group(1)
                logger.info("CSRF token 已获取")
                return self._csrf_token
            logger.warning("首页未找到 CSRF token，尝试空 token 请求")
            return ""
        except (OSError, ValueError) as e:
            logger.warning("CSRF token 获取失败: %s", e)
            return ""

    # ── HTTP 请求 ───────────────────────────────────────

    def _post_json(self, url: str) -> Any:
        """发送 POST 请求并解析 JSON 响应。"""
        token = self._ensure_csrf()
        headers = {
            "User-Agent": self._user_agent(),
            "Content-Type": "application/x-www-form-urlencoded",
            "X-CSRF-Token": token,
        }
        data = b""
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                # 尝试从响应头提取 CSRF token（若服务端返回新 token 则更新缓存）
                resp_token = resp.headers.get("X-CSRF-Token") or resp.headers.get("csrf-token")
                if resp_token:
                    self._csrf_token = resp_token
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

        预期格式：{ "code": 0, "data": { "stations": [...] } }
        或直接返回列表。
        """
        raw = data.get("data", data) if isinstance(data, dict) else data
        stations = raw.get("stations", raw) if isinstance(raw, dict) else raw
        if not isinstance(stations, list):
            if isinstance(stations, dict) and not stations:
                return []
            raise KkrbError(f"OV 数据格式异常: 期望列表，got {type(stations).__name__}")

        products: list[CraftingProduct] = []
        for item in stations:
            if not isinstance(item, dict):
                continue
            products.append(
                CraftingProduct(
                    station=str(item.get("stationName", "")),
                    product=str(item.get("productName", "")),
                    profit=_int_or_zero(item.get("profit")),
                    ideal_price=_int_or_zero(item.get("idealPrice")),
                    sell_time=str(item.get("sellTime", "")),
                )
            )
        products.sort(key=lambda p: p.profit, reverse=True)
        return products

    @staticmethod
    def _parse_cpv_response(data: Any, filter_tier: int | None = None) -> dict[int, list[GearScheme]]:
        """解析 getCPVData 响应。

        预期格式：{ "code": 0, "data": { "tiers": [...] } }
        每个 tier 包含 tierValue 和 schemes 列表。
        """
        raw = data.get("data", data) if isinstance(data, dict) else data
        tiers = raw.get("tiers", raw) if isinstance(raw, dict) else raw
        if not isinstance(tiers, list):
            if isinstance(tiers, dict) and not tiers:
                return {}
            raise KkrbError(f"CPV 数据格式异常: 期望列表，got {type(tiers).__name__}")

        result: dict[int, list[GearScheme]] = {}
        for tier_item in tiers:
            if not isinstance(tier_item, dict):
                continue
            try:
                tier_value = int(tier_item.get("tierValue", 0))
            except (ValueError, TypeError):
                continue
            if filter_tier is not None and tier_value != filter_tier:
                continue

            schemes_raw = tier_item.get("schemes", [])
            schemes: list[GearScheme] = []
            for s in schemes_raw:
                if not isinstance(s, dict):
                    continue
                items_raw = s.get("items", [])
                items = [
                    GearItem(
                        name=str(it.get("name", "")),
                        cost=_int_or_zero(it.get("cost")),
                        battle_value=_int_or_zero(it.get("battleValue")),
                        source=str(it.get("source", "")),
                        wear=str(it.get("wear", it.get("durability", ""))),
                    )
                    for it in items_raw
                    if isinstance(it, dict)
                ]
                schemes.append(
                    GearScheme(
                        title=str(s.get("title", "")),
                        total_cost=_int_or_zero(s.get("totalCost")),
                        final_bv=_int_or_zero(s.get("finalBv")),
                        items=items,
                    )
                )
            result[tier_value] = schemes

        return result

    # ── 辅助 ────────────────────────────────────────────

    @staticmethod
    def _user_agent() -> str:
        return "ProfitCalculator/1.0"

    def reset(self) -> None:
        """重置 CSRF token（强制下次请求重新获取）。"""
        self._csrf_token = None


def _int_or_zero(value: Any) -> int:
    """安全转为 int，失败返回 0。"""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0
"""
kkrb.net API 客户端：会话管理 + HTTP 传输 + TTL 缓存。

纯 stdlib 实现（urllib.request + http.cookiejar），零外部依赖。
架构深化（候选 1）：响应解析已拆至 kkrb_parsing（纯函数，独立单测），
数据模型与异常在 kkrb_models（零依赖叶子）；本模块协议表面收敛为
`fetch_*` + `reset`——CSRF 握手、cookie 会话、缓存细节全部隐藏。
"""

from __future__ import annotations

__all__ = [
    "AmmoPackageItem",
    "CraftingProduct",
    "KkrbClient",
    "KkrbError",
]

import logging
import time
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from typing import Any
from urllib.request import HTTPCookieProcessor, Request, build_opener

# 重新导出（协议表面保持）：模型/异常定义在 kkrb_models 叶子
from kkrb_models import AmmoPackageItem, CraftingProduct, KkrbError  # noqa: F401
from kkrb_parsing import parse_ammo_package_response, parse_ov_response

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.kkrb.net"
_OV_ENDPOINT = f"{_BASE_URL}/getOVData"
_AMMO_PACKAGE_ENDPOINT = f"{_BASE_URL}/getAmmoPackageData"
_TIMEOUT = 10
_CACHE_TTL = 60  # 秒；缓存有效期内不重复请求


# ── 客户端 ──────────────────────────────────────────────


class KkrbClient:
    """kkrb.net API 客户端（会话 + 传输 + 缓存）。

    用法：
        client = KkrbClient()
        products = client.fetch_ov_data()
    """

    def __init__(self) -> None:
        self._cookie_jar = CookieJar()
        self._opener = build_opener(HTTPCookieProcessor(self._cookie_jar))
        self._csrf_token: str | None = None
        self._cache: dict[str, tuple[float, Any]] = {}  # url → (timestamp, data)

    # ── 公开接口 ────────────────────────────────────────

    def fetch_ov_data(self) -> list[CraftingProduct]:
        """获取制造产物推荐数据。

        Returns:
            4 个台位的 CraftingProduct 列表，按利润降序排列。

        Raises:
            KkrbError: 网络请求失败或数据解析失败。
        """
        data = self._post_json(_OV_ENDPOINT)
        return parse_ov_response(data)

    def fetch_ammo_package_data(self) -> list[AmmoPackageItem]:
        """获取子弹自选包兑换利润数据。

        Returns:
            AmmoPackageItem 列表，按利润降序排列。

        Raises:
            KkrbError: 网络请求失败或数据解析失败。
        """
        data = self._post_json(_AMMO_PACKAGE_ENDPOINT)
        return parse_ammo_package_response(data)

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
        """发送 POST 请求并解析 JSON 响应（带 TTL 缓存）。"""
        # 缓存命中且未过期 → 直接返回
        now = time.monotonic()
        if url in self._cache:
            cached_at, data = self._cache[url]
            if now - cached_at < _CACHE_TTL:
                return data

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
            data = self._parse_json(body)
            self._cache[url] = (time.monotonic(), data)
            return data
        except (OSError, ValueError) as e:
            msg = f"POST {url} 失败: {e}"
            logger.error(msg)
            raise KkrbError(msg) from e

    # ── 辅助 ────────────────────────────────────────────

    @staticmethod
    def _parse_json(body: str) -> Any:
        """安全解析 JSON，处理 kkrb.net 的 BOM 和异常格式。"""
        text = body.lstrip("\ufeff").strip()
        if not text:
            raise KkrbError("空响应")
        import json  # noqa: PLC0415

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise KkrbError(f"JSON 解析失败: {e}") from e

    @staticmethod
    def _user_agent() -> str:
        return "DeltaForceDashboard/1.0"

    def reset(self) -> None:
        """重置 CSRF token、cookie jar 和缓存（强制下次请求重新认证）。"""
        self._csrf_token = None
        self._cookie_jar.clear()
        self._cache.clear()

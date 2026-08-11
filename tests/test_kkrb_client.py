"""kkrb_client 单元测试（会话/传输/缓存）。

架构深化（候选 1）后：响应解析测试迁至 test_kkrb_parsing.py（纯函数直调）；
本文件保留数据模型（经 kkrb_client 重新导出访问，验证协议表面）与
KkrbClient 的网络/缓存行为。
"""

from __future__ import annotations

import json
import threading
import time
from http.cookiejar import Cookie, CookieJar
from typing import Any
from urllib.request import Request

import pytest

from kkrb_client import (
    AmmoPackageItem,
    CraftingProduct,
    KkrbClient,
    KkrbError,
)


class TestDataModels:
    def test_crafting_product_frozen(self) -> None:
        p = CraftingProduct("技术中心", "复合弓", 24669, 39077, "晚上8点")
        assert p.station == "技术中心"
        assert p.profit == 24669

    def test_ammo_package_item_frozen(self) -> None:
        item = AmmoPackageItem(
            package_name="3级子弹自选包",
            item_name="5.7x28mm L191",
            item_grade=3,
            item_count=200,
            single_price=555,
            total_price=111000,
            profit=98790,
        )
        assert item.package_name == "3级子弹自选包"
        assert item.item_name == "5.7x28mm L191"
        assert item.item_grade == 3
        assert item.item_count == 200
        assert item.single_price == 555
        assert item.total_price == 111000
        assert item.profit == 98790


class TestKkrbClient:
    def test_fetch_parses_through_kkrb_parsing(self, monkeypatch) -> None:
        """fetch_ov_data 经 kkrb_parsing 解析（client 不再自带解析）。"""
        import kkrb_parsing

        calls: list[Any] = []

        def fake_post_json(self, url: str):
            calls.append(url)
            return {
                "data": {
                    "spData": {
                        "tech": {
                            "placeName": "技术中心",
                            "itemName": "复合弓",
                            "profit": 100,
                            "singlePrice": 200,
                            "yesterdayHighestTime": "晚上8点",
                        }
                    }
                }
            }

        monkeypatch.setattr(KkrbClient, "_post_json", fake_post_json)
        client = KkrbClient()
        products = client.fetch_ov_data()
        assert len(products) == 1
        assert products[0].station == "技术中心"
        # client 不再暴露私有解析方法（协议表面收敛）
        assert not hasattr(KkrbClient, "_parse_ov_response")
        assert not hasattr(KkrbClient, "_parse_ammo_package_response")
        assert not hasattr(KkrbClient, "_int_or_zero")

    def test_fetch_network_error_raises_kkrb_error(self, monkeypatch) -> None:
        """传输失败 → KkrbError（解析层异常也统一为 KkrbError 家族）。"""

        def fake_post_json(self, url: str):
            raise KkrbError("POST 失败")

        monkeypatch.setattr(KkrbClient, "_post_json", fake_post_json)
        client = KkrbClient()
        with pytest.raises(KkrbError):
            client.fetch_ov_data()


# ── 传输层 fake（fake opener 注入）──────────────────────

# 端到端用例的真实响应样例（与 kkrb_parsing 契约一致）
_OV_URL = "https://www.kkrb.net/getOVData"
_AMMO_URL = "https://www.kkrb.net/getAmmoPackageData"
_OV_PAYLOAD = {
    "code": 1,
    "data": {
        "spData": {
            "tech": {
                "placeName": "技术中心",
                "itemName": "复合弓",
                "profit": 24669,
                "singlePrice": 39077,
                "yesterdayHighestTime": "晚上8点",
            }
        }
    },
}
_AMMO_PAYLOAD = {
    "code": 1,
    "data": {
        "cn": [
            {
                "packageName": "3级子弹自选包",
                "itemName": "5.7x28mm L191",
                "itemGrade": 3,
                "itemCount": 200,
                "singlePrice": 555,
                "totalPrice": 111000,
                "profit": 98790,
            }
        ]
    },
}


class _FakeResponse:
    """urllib response 的最小实现（read + 上下文管理）。"""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


def _make_cookie(name: str, value: str) -> Cookie:
    """构造 kkrb.net 域下的会话 cookie（供 FakeOpener 注入 csrf_token）。"""
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain="kkrb.net",
        domain_specified=True,
        domain_initial_dot=False,
        path="/",
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


class FakeOpener:
    """脚本式 fake opener：open 按顺序消费 script 条目，记录全部请求。

    script 条目：
      - bytes              → 作为响应体返回
      - Exception 实例     → 原样抛出（模拟网络/协议错误）
      - (bytes, str, str)  → 响应体 + 向 cookie jar 注入 cookie（握手成功路径）

    用法：`client._opener = FakeOpener(client._cookie_jar, script)`——
    `_opener` 是传输 seam，替换后 KkrbClient 的 CSRF 握手 / TTL 缓存 /
    错误路径全部走真实代码，仅网络层被替换（D-04：被测试的路径=真实路径）。
    """

    def __init__(self, cookie_jar: CookieJar, script: list[Any]) -> None:
        self._jar = cookie_jar
        self._script = list(script)
        self.requests: list[Request] = []

    def open(self, req: Request, timeout: float | None = None) -> _FakeResponse:
        self.requests.append(req)
        step = self._script.pop(0) if self._script else b""
        if isinstance(step, Exception):
            raise step
        if isinstance(step, tuple):
            body, name, value = step
            self._jar.set_cookie(_make_cookie(name, value))
        else:
            body = step
        return _FakeResponse(body)


def _header_value(req: Request, name: str) -> str | None:
    """大小写不敏感取 urllib Request 头（add_header 会 capitalize 键）。"""
    for key, value in req.header_items():
        if key.lower() == name.lower():
            return value
    return None


class _URLRoutedOpener:
    """URL 路由 fake opener：按请求 URL 返回固定响应（并发测试专用）。

    并发下哪个线程先抢到锁是不确定的，脚本式按位置消费无法与请求顺序
    对齐；改为按 URL 路由，任意线程调度下行为确定。每次 open 主动让出
    GIL，放大竞争窗口（无锁实现下确定性失败）。
    """

    def __init__(self, cookie_jar: CookieJar, routes: dict[str, Any]) -> None:
        self._jar = cookie_jar
        self._routes = dict(routes)
        self.requests: list[Request] = []

    def open(self, req: Request, timeout: float | None = None) -> _FakeResponse:
        self.requests.append(req)
        time.sleep(0.01)
        step = self._routes.get(req.full_url, b"")
        if isinstance(step, Exception):
            raise step
        if isinstance(step, tuple):
            body, name, value = step
            self._jar.set_cookie(_make_cookie(name, value))
            return _FakeResponse(body)
        return _FakeResponse(step)


@pytest.fixture
def transport_client():
    """返回 (client, opener)：client 的 _opener 替换为脚本式 FakeOpener。"""

    def _make(script: list[Any]) -> tuple[KkrbClient, FakeOpener]:
        client = KkrbClient()
        opener = FakeOpener(client._cookie_jar, script)
        client._opener = opener
        return client, opener

    return _make


class TestCsrfHandshake:
    """CSRF 三步握手：首页 → getMenu → cookie 提取，含全部降级路径。"""

    def test_extracts_token_and_caches_handshake(self, transport_client) -> None:
        """握手成功后 token 缓存复用：第二次 fetch 不再发握手请求。"""
        client, opener = transport_client(
            [b"home", (b"menu", "csrf_token", "tok123"), json.dumps(_OV_PAYLOAD).encode()]
        )
        client.fetch_ov_data()
        assert len(opener.requests) == 3  # 首页 + getMenu + POST

        # 第二次 fetch：数据缓存命中，0 新请求（握手也复用）
        client.fetch_ov_data()
        assert len(opener.requests) == 3

    def test_homepage_failure_falls_back_to_empty_token(self, transport_client) -> None:
        """首页失败 → 不抛异常，空 token 继续 POST。"""
        client, opener = transport_client(
            [OSError("net down"), json.dumps(_OV_PAYLOAD).encode()]
        )
        products = client.fetch_ov_data()
        assert products[0].station == "技术中心"
        post = [r for r in opener.requests if "getOVData" in r.full_url][0]
        assert _header_value(post, "X-CSRF-Token") == ""

    def test_getmenu_failure_falls_back_to_empty_token(self, transport_client) -> None:
        """getMenu 失败 → 降级为空 token，请求链路不中断。"""
        client, opener = transport_client(
            [b"home", OSError("menu down"), json.dumps(_OV_PAYLOAD).encode()]
        )
        client.fetch_ov_data()
        assert len(opener.requests) == 3  # 首页成功 + getMenu 失败 + POST

    def test_valueerror_in_handshake_tolerated(self, transport_client) -> None:
        """握手层 (OSError, ValueError) 双分支均降级为空 token。"""
        client, opener = transport_client(
            [ValueError("bad header"), json.dumps(_OV_PAYLOAD).encode()]
        )
        client.fetch_ov_data()
        assert len(opener.requests) == 2

    def test_missing_csrf_cookie_retries_handshake(self, transport_client) -> None:
        """cookie 中无 csrf_token → 每次 fetch 都重新握手（不缓存空值）。"""
        client, opener = transport_client(
            [
                b"home", b"menu", json.dumps(_OV_PAYLOAD).encode(),
                b"home", b"menu", json.dumps(_AMMO_PAYLOAD).encode(),
            ]
        )
        client.fetch_ov_data()
        client.fetch_ammo_package_data()
        assert len(opener.requests) == 6  # 2×(首页+getMenu) + 2×POST


class TestPostJsonTransport:
    """_post_json 传输 + TTL 缓存 + 请求头。"""

    def test_cache_hit_skips_network(self, transport_client) -> None:
        """TTL 内缓存命中：同一 URL 二次 fetch 零网络请求。"""
        client, opener = transport_client(
            [b"home", b"menu", json.dumps(_OV_PAYLOAD).encode()]
        )
        client.fetch_ov_data()
        client.fetch_ov_data()
        assert len(opener.requests) == 3

    def test_cache_expiry_triggers_refetch(self, transport_client) -> None:
        """缓存过期（TTL 60s）→ 重新请求，但 CSRF 握手仍复用。"""
        client, opener = transport_client(
            [
                b"home", (b"menu", "csrf_token", "tok123"),
                json.dumps(_OV_PAYLOAD).encode(), json.dumps(_OV_PAYLOAD).encode(),
            ]
        )
        client.fetch_ov_data()
        # 注入 61s 前的过期时间戳
        client._cache[_OV_URL] = (time.monotonic() - 61, _OV_PAYLOAD)
        client.fetch_ov_data()
        assert len(opener.requests) == 4  # 握手 2 + POST 2

    def test_network_error_raises_kkrb_error(self, transport_client) -> None:
        client, _ = transport_client([b"home", b"menu", OSError("timeout")])
        with pytest.raises(KkrbError, match="POST"):
            client.fetch_ov_data()

    def test_valueerror_raises_kkrb_error(self, transport_client) -> None:
        client, _ = transport_client([b"home", b"menu", ValueError("bad")])
        with pytest.raises(KkrbError):
            client.fetch_ov_data()

    def test_invalid_json_body_raises(self, transport_client) -> None:
        client, _ = transport_client([b"home", b"menu", b"<html>oops</html>"])
        with pytest.raises(KkrbError, match="JSON"):
            client.fetch_ov_data()

    def test_empty_body_raises(self, transport_client) -> None:
        client, _ = transport_client([b"home", b"menu", b""])
        with pytest.raises(KkrbError, match="空响应"):
            client.fetch_ov_data()

    def test_request_headers_carry_token_and_ua(self, transport_client) -> None:
        """POST 头完整：X-CSRF-Token / User-Agent / X-Requested-With / Content-Type。"""
        client, opener = transport_client(
            [b"home", (b"menu", "csrf_token", "tok123"), b"{}"]
        )
        client.fetch_ov_data()
        post = [r for r in opener.requests if "getOVData" in r.full_url][0]
        assert _header_value(post, "X-CSRF-Token") == "tok123"
        assert _header_value(post, "User-Agent") == "DeltaForceDashboard/1.0"
        assert _header_value(post, "X-Requested-With") == "XMLHttpRequest"
        assert _header_value(post, "Content-Type") == "application/x-www-form-urlencoded"
        assert post.get_method() == "POST"


class TestParseJson:
    """_parse_json 安全解析：BOM / 空响应 / 畸形 JSON。"""

    def test_strips_bom(self) -> None:
        assert KkrbClient._parse_json('\ufeff{"a": 1}') == {"a": 1}

    def test_empty_raises(self) -> None:
        with pytest.raises(KkrbError, match="空响应"):
            KkrbClient._parse_json("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(KkrbError, match="空响应"):
            KkrbClient._parse_json("\ufeff  \n  ")

    def test_malformed_raises(self) -> None:
        with pytest.raises(KkrbError, match="JSON"):
            KkrbClient._parse_json('{"a": ')

    def test_list_passthrough(self) -> None:
        assert KkrbClient._parse_json("[1, 2]") == [1, 2]


class TestUserAgent:
    def test_matches_current_product_name(self) -> None:
        assert KkrbClient._user_agent() == "DeltaForceDashboard/1.0"


class TestReset:
    def test_clears_token_cache_and_session(self, transport_client) -> None:
        """reset 后 CSRF token / 数据缓存 / cookie 会话清空，重新完整握手。"""
        client, opener = transport_client(
            [
                b"home", (b"menu", "csrf_token", "tok123"),
                json.dumps(_OV_PAYLOAD).encode(),
                b"home", b"menu", json.dumps(_OV_PAYLOAD).encode(),
            ]
        )
        client.fetch_ov_data()
        assert len(opener.requests) == 3
        client.reset()
        client.fetch_ov_data()
        assert len(opener.requests) == 6  # 重新握手 2 + 重新 POST 1

    def test_reset_serializes_with_in_flight_request(self, transport_client) -> None:
        """AA-03：reset 纳入 _lock——锁被在途请求持有时 reset 阻塞，不并发清缓存。

        确定性锁边界断言：主线程持有 _lock（模拟在途 fetch 持锁），
        reset 线程应阻塞等待；锁释放后 reset 才执行完毕。
        无锁实现下 reset 立即执行（事件立刻置位），本断言失败。
        """
        client, _ = transport_client([b"home"])
        done = threading.Event()

        client._lock.acquire()
        try:
            t = threading.Thread(target=lambda: (client.reset(), done.set()))
            t.start()
            assert not done.wait(timeout=0.3), "reset 不应在锁被持有时执行"
        finally:
            client._lock.release()
        assert done.wait(timeout=2.0), "锁释放后 reset 应完成"
        t.join(timeout=2.0)


class TestEndToEnd:
    """真实传输链路：FakeOpener 网络层 + 真实握手/缓存/解析全走。"""

    def test_fetch_ov_data_full_transport(self, transport_client) -> None:
        client, _ = transport_client(
            [b"home", b"menu", json.dumps(_OV_PAYLOAD).encode()]
        )
        products = client.fetch_ov_data()
        assert len(products) == 1
        assert products[0].station == "技术中心"
        assert products[0].profit == 24669

    def test_fetch_ammo_package_full_transport(self, transport_client) -> None:
        client, _ = transport_client(
            [b"home", b"menu", json.dumps(_AMMO_PAYLOAD).encode()]
        )
        items = client.fetch_ammo_package_data()
        assert len(items) == 1
        assert items[0].item_name == "5.7x28mm L191"
        assert items[0].profit == 98790

    def test_transport_error_bubbles_to_caller(self, transport_client) -> None:
        client, _ = transport_client(
            [b"home", b"menu", OSError("connection refused")]
        )
        with pytest.raises(KkrbError):
            client.fetch_ammo_package_data()


class TestConcurrency:
    """共享 client 并发安全（spec C2-01）：握手恰一次、缓存无脏读。"""

    @staticmethod
    def _routed_client(routes: dict[str, Any]) -> tuple[KkrbClient, _URLRoutedOpener]:
        """构造 client：_opener 替换为 URL 路由 opener（传输 seam，同 transport_client）。"""
        client = KkrbClient()
        opener = _URLRoutedOpener(client._cookie_jar, routes)
        client._opener = opener
        return client, opener

    def test_concurrent_fetch_handshakes_once(self) -> None:
        """N 线程同时 fetch_ov_data：握手（首页 + getMenu）总次数 == 1。

        全部线程拿到正确数据、无异常；总请求 = 握手 2 + POST 1。
        """
        n = 8
        client, opener = self._routed_client(
            {
                "https://www.kkrb.net": b"home",
                "https://www.kkrb.net/getMenu": (b"menu", "csrf_token", "tok123"),
                _OV_URL: json.dumps(_OV_PAYLOAD).encode(),
            }
        )
        barrier = threading.Barrier(n)
        results: list[Any] = []
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                barrier.wait()
                results.append(client.fetch_ov_data())
            except BaseException as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == []
        assert all(not t.is_alive() for t in threads)
        assert len(results) == n
        assert all(len(products) == 1 for products in results)
        assert all(products[0].station == "技术中心" for products in results)
        # 握手恰一次：首页 + getMenu 各 1 个请求，总请求 = 2 + 1 POST
        assert len(opener.requests) == 3
        assert len([r for r in opener.requests if "getMenu" in r.full_url]) == 1
        assert len([r for r in opener.requests if "getOVData" in r.full_url]) == 1

    def test_concurrent_fetch_different_urls_share_handshake(self) -> None:
        """并发请求两个不同端点：握手仍恰一次，两路数据各自正确（缓存互不污染）。"""
        n = 6
        client, opener = self._routed_client(
            {
                "https://www.kkrb.net": b"home",
                "https://www.kkrb.net/getMenu": (b"menu", "csrf_token", "tok123"),
                _OV_URL: json.dumps(_OV_PAYLOAD).encode(),
                "https://www.kkrb.net/getAmmoPackageData": json.dumps(_AMMO_PAYLOAD).encode(),
            }
        )
        barrier = threading.Barrier(n)
        results: list[tuple[str, Any]] = []
        errors: list[BaseException] = []

        def worker(index: int) -> None:
            try:
                barrier.wait()
                if index % 2 == 0:
                    results.append(("ov", client.fetch_ov_data()))
                else:
                    results.append(("ammo", client.fetch_ammo_package_data()))
            except BaseException as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert errors == []
        assert all(not t.is_alive() for t in threads)
        assert len(results) == n
        ov = [r for kind, r in results if kind == "ov"]
        ammo = [r for kind, r in results if kind == "ammo"]
        assert len(ov) == n // 2 and len(ammo) == n // 2
        assert all(items[0].station == "技术中心" for items in ov)
        assert all(items[0].item_name == "5.7x28mm L191" for items in ammo)
        # 握手恰一次：首页 + getMenu 各 1，加两路 POST
        assert len(opener.requests) == 4
        assert len([r for r in opener.requests if "getMenu" in r.full_url]) == 1

    def test_concurrent_fetch_with_reset_no_race(self) -> None:
        """AA-03：并发 fetch + reset 无竞争异常；reset 后重新 fetch 数据正确。

        reset 与 fetch 同一把锁串行化——「检查缓存命中 → 读取缓存项」之间
        不会被 reset 清缓存打断（无锁实现可抛 KeyError/半状态），
        reset 后任何线程重新 fetch 均返回完整数据。
        """
        n = 6
        client, opener = self._routed_client(
            {
                "https://www.kkrb.net": b"home",
                "https://www.kkrb.net/getMenu": (b"menu", "csrf_token", "tok123"),
                _OV_URL: json.dumps(_OV_PAYLOAD).encode(),
            }
        )
        barrier = threading.Barrier(n + 1)
        results: list[Any] = []
        errors: list[BaseException] = []

        def fetch_worker() -> None:
            try:
                barrier.wait()
                for _ in range(4):
                    results.append(client.fetch_ov_data())
            except BaseException as e:  # noqa: BLE001
                errors.append(e)

        def reset_worker() -> None:
            try:
                barrier.wait()
                for _ in range(4):
                    client.reset()
                    results.append(client.fetch_ov_data())
            except BaseException as e:  # noqa: BLE001
                errors.append(e)

        threads = [threading.Thread(target=fetch_worker) for _ in range(n)]
        threads.append(threading.Thread(target=reset_worker))
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)

        assert errors == [], f"并发 reset+fetch 出现异常：{errors}"
        assert all(not t.is_alive() for t in threads)
        assert len(results) == (n + 1) * 4
        assert all(len(products) == 1 for products in results)
        assert all(products[0].station == "技术中心" for products in results)

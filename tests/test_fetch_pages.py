"""
FetchWorker 安全关闭 + 数据页懒加载/预加载/重构 回归测试（T-01/T-02/T-03）。

覆盖：
- T-01：FetchWorker.shutdown() 正常等待 / 超时逃生舱托管；请求在途时关闭
  主窗口不崩溃（"QThread: Destroyed while thread is still running" 回归）。
- T-02：preload() 幂等、offscreen 守卫、失败路径记录日志（不静默吞错）。
- T-03：基类提炼后两页外部行为不变（懒加载、渲染、主题色收敛、_error 死状态移除）。
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime

import pytest

from config import DATE_FORMAT
from data_store import DataStore

__all__ = []


# ── 辅助 ──────────────────────────────────────────────────


def _wait_running(worker, timeout: float = 5.0) -> bool:
    """轮询等待 worker 进入运行态。"""
    deadline = time.monotonic() + timeout
    while not worker.isRunning() and time.monotonic() < deadline:
        time.sleep(0.005)
    return worker.isRunning()


def _make_blocking_stub():
    """返回 (阻塞 stub, 释放事件)：stub 在事件释放前不会返回。"""
    release = threading.Event()

    def blocking_fetch():
        release.wait(timeout=10)
        return []

    return blocking_fetch, release


# ── T-01. FetchWorker.shutdown() ──────────────────────────


def test_fetch_worker_shutdown_finished_thread() -> None:
    """shutdown()：未启动/已结束的 worker 立即返回 True。"""
    from app.fetch_worker import FetchWorker

    worker = FetchWorker(lambda: 42)
    assert worker.shutdown() is True  # 未启动
    worker.start()
    assert worker.wait(5000)
    assert worker.shutdown() is True  # 已结束


def test_fetch_worker_shutdown_waits_for_completion() -> None:
    """shutdown()：在途请求在超时前完成 → 等待并返回 True。"""
    from app.fetch_worker import FetchWorker

    release = threading.Event()
    worker = FetchWorker(lambda: (release.wait(10), None)[1])
    worker.start()
    assert _wait_running(worker)
    release.set()
    assert worker.shutdown(5000) is True
    assert not worker.isRunning()


def test_fetch_worker_shutdown_timeout_detaches(qapp) -> None:
    """shutdown()：超时后转入逃生舱托管，运行中的线程不会被销毁（T-01 核心）。"""
    from app import fetch_worker as fw
    from app.fetch_worker import FetchWorker

    entered = threading.Event()
    release = threading.Event()

    def blocking_fetch():
        entered.set()          # 标记已进入阻塞调用（run() 内）
        release.wait(10)
        return None

    worker = FetchWorker(blocking_fetch)
    worker.start()
    assert entered.wait(5)     # 确保已进入阻塞调用，而非仍在启动途中

    assert worker.shutdown(100) is False  # 超时
    assert worker.isRunning()             # 线程仍在运行
    assert worker.parent() is None        # 已脱离父子关系
    assert worker in fw._detached_workers  # 模块级逃生舱持有强引用

    release.set()
    assert worker.wait(5000)              # 线程最终结束
    qapp.processEvents()                  # 投递 finished → 逃生舱清理
    assert worker not in fw._detached_workers


def test_close_window_with_inflight_worker_no_crash(
    qapp, settings_guard, tmp_path, monkeypatch
) -> None:
    """请求在途时关闭主窗口：不抛异常、线程安全回收（T-01 回归）。

    旧实现中 FetchWorker 只挂在页面实例上，closeEvent 不等待/停止线程，
    关窗即触发 "QThread: Destroyed while thread is still running" abort。
    """
    from app.main_window import MainWindow
    from calculator import ProfitCalculatorLogic

    # 绕过 preload 的 offscreen 守卫，让预加载真实启动后台线程
    monkeypatch.setitem(os.environ, "QT_QPA_PLATFORM", "offscreen-t")

    blocking_fetch, release = _make_blocking_stub()

    today = datetime.now().strftime(DATE_FORMAT)
    data = {today: {"cash": 100.0, "warehouse": 200.0}}
    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(data),
    )
    page = win.profit_page.crafting_page
    page._client.fetch_ov_data = blocking_fetch  # 实例级替换为阻塞 stub
    page.preload()

    worker = page._worker
    assert worker is not None
    assert _wait_running(worker)

    win.close()  # 关键：请求在途时关窗，不得崩溃 / abort

    release.set()
    assert worker.wait(5000)
    assert not worker.isRunning()
    win.close()  # 幂等：再次关闭无异常


# ── T-02. preload() ───────────────────────────────────────


def test_preload_skipped_offscreen(qapp) -> None:
    """offscreen 测试模式下 preload() 不启动 worker（原守卫保留）。"""
    from app.crafting_page import CraftingPage

    page = CraftingPage()
    page.preload()
    assert page._worker is None


def test_preload_idempotent(qapp, monkeypatch) -> None:
    """preload() 幂等：加载中/已加载时重复调用不重复启动 worker。"""
    from app.crafting_page import CraftingPage

    monkeypatch.setitem(os.environ, "QT_QPA_PLATFORM", "offscreen-t")
    page = CraftingPage()
    page._client.fetch_ov_data = lambda: []

    page.preload()
    first = page._worker
    assert first is not None and first.isRunning()

    page.preload()  # 加载中 → 直接返回
    assert page._worker is first

    assert first.wait(5000)
    qapp.processEvents()  # 投递 done → 状态机转入 loaded
    assert page.is_loaded is True

    page.preload()  # 已加载 → 直接返回
    assert page._worker is first


def test_refresh_after_loaded_starts_new_worker(qapp, monkeypatch) -> None:
    """候选 2 回归：loaded 态点刷新（refresh）重新加载——新 worker，状态回 loading。"""
    from app.crafting_page import CraftingPage

    monkeypatch.setitem(os.environ, "QT_QPA_PLATFORM", "offscreen-t")
    page = CraftingPage()
    page._client.fetch_ov_data = lambda: []

    page.preload()
    first = page._worker
    assert first is not None
    assert first.wait(5000)
    qapp.processEvents()
    assert page.is_loaded is True

    page.refresh()  # 手动刷新：loaded → loading（新 worker）
    assert page._load_state.is_loading is True
    assert page._worker is not None and page._worker is not first
    assert page._worker.wait(5000)
    qapp.processEvents()
    assert page.is_loaded is True


def test_preload_failure_logs_and_shows_retry(qapp, monkeypatch, caplog) -> None:
    """preload() 失败路径：记录 warning、状态提示可重试、不静默吞错（T-02 回归）。"""
    from app.crafting_page import CraftingPage
    from kkrb_client import KkrbError

    monkeypatch.setitem(os.environ, "QT_QPA_PLATFORM", "offscreen-t")
    page = CraftingPage()
    page._client.fetch_ov_data = lambda: (_ for _ in ()).throw(KkrbError("boom"))

    with caplog.at_level(logging.WARNING, logger="app.fetch_page_base"):
        page.preload()
        worker = page._worker
        assert worker is not None
        assert worker.wait(5000)
        qapp.processEvents()

    assert any("制造产物数据获取失败" in r.message for r in caplog.records)
    assert page._status_label.text() == "⚠️ 数据获取失败，点击重试"
    assert page._load_state.is_loading is False
    assert page._refresh_btn.isEnabled()


def test_error_label_click_retries(qapp, monkeypatch) -> None:
    """U-07：「点击重试」label 真实可点——点击后重新发起加载（新 worker）。"""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from app.crafting_page import CraftingPage
    from kkrb_client import KkrbError

    monkeypatch.setitem(os.environ, "QT_QPA_PLATFORM", "offscreen-t")
    page = CraftingPage()
    page._client.fetch_ov_data = lambda: (_ for _ in ()).throw(KkrbError("boom"))

    page.show()  # label 可见性需父链已显示
    qapp.processEvents()
    page.preload()
    worker = page._worker
    assert worker is not None
    assert worker.wait(5000)
    qapp.processEvents()

    # 错误态：label 可见 + 手型光标（可点提示）
    assert page._status_label.isVisible()
    assert page._status_label.cursor().shape() == Qt.CursorShape.PointingHandCursor

    # 点击 label → 重新加载（新 worker 启动，状态机回到 loading）
    QTest.mouseClick(page._status_label, Qt.MouseButton.LeftButton)
    assert page._load_state.is_loading is True
    assert page._worker is not None and page._worker is not worker


def test_preload_after_shutdown_does_not_start(qapp, monkeypatch) -> None:
    """shutdown() 后不再启动新预加载（关窗后迟到的定时器回调不复活线程）。"""
    from app.crafting_page import CraftingPage

    monkeypatch.setitem(os.environ, "QT_QPA_PLATFORM", "offscreen-t")
    page = CraftingPage()
    page.shutdown()
    page.preload()
    assert page._worker is None


# ── T-03. 基类提炼后外部行为 ──────────────────────────────


def test_crafting_page_lazy_loads_on_show(qapp) -> None:
    """showEvent 首次显示触发加载，成功后渲染卡片并复位状态。"""
    from app.crafting_page import CraftingPage
    from kkrb_client import CraftingProduct

    page = CraftingPage()
    page._client.fetch_ov_data = lambda: [
        CraftingProduct("技术中心", "复合弓", 24669, 39077, "晚上8点"),
    ]

    page.show()  # 触发 showEvent → 懒加载
    assert page._load_state.is_loading is True
    worker = page._worker
    assert worker is not None
    assert worker.wait(5000)
    qapp.processEvents()

    assert page.is_loaded is True
    assert page._load_state.is_loading is False
    assert page._refresh_btn.isEnabled()
    assert page._status_label.isHidden()
    # 第一张卡片已渲染
    card = page._cards[0]
    product_label = card.layout().itemAt(1).widget()
    assert product_label.text() == "复合弓"
    page.hide()


def test_exchange_page_renders_best_per_package(qapp) -> None:
    """兑换页渲染：每组包类型只显示利润最高的条目（重构行为不变）。"""
    from app.exchange_page import ExchangePage
    from kkrb_client import AmmoPackageItem

    page = ExchangePage()
    page._client.fetch_ammo_package_data = lambda: [
        AmmoPackageItem("3级子弹自选包", "低利润弹", 3, 200, 100, 20000, 5000),
        AmmoPackageItem("3级子弹自选包", "高利润弹", 3, 200, 555, 111000, 98790),
        AmmoPackageItem("4级子弹自选包", "唯一弹", 4, 150, 1934, 290100, 258189),
    ]

    page.show()
    worker = page._worker
    assert worker is not None
    assert worker.wait(5000)
    qapp.processEvents()

    # 3 级包卡片显示利润最高的条目
    card3 = page._cards[0]
    assert card3._item_name.text() == "高利润弹"
    # 4 级包卡片正常显示
    card4 = page._cards[1]
    assert card4._item_name.text() == "唯一弹"
    page.hide()


def test_exchange_colors_resolve_from_theme(qapp) -> None:
    """兑换页标签色收敛：7 种包全走单一装饰键 PACKAGE_COLOR_0~6；分隔线用 SEPARATOR。"""
    from app.exchange_page import ExchangePage
    from app.theme import get_color

    page = ExchangePage()

    # 7 张卡按 _PACKAGE_CONFIG 映射到 PACKAGE_COLOR_2/1/3/0/4/5/6（U-03 键名如实）；
    # 色相沿用历史：3 级青绿 / 4 级金 / 5 级红 / 通行证基础蓝紫 / 通行证高级紫 /
    # 进阶物流橙褐 / 特级物流粉红（后两者原为橙/橙红，为满足两两 ΔE 下限向橙褐/粉红漂移）
    keys = (
        "PACKAGE_COLOR_2",
        "PACKAGE_COLOR_1",
        "PACKAGE_COLOR_3",
        "PACKAGE_COLOR_0",
        "PACKAGE_COLOR_4",
        "PACKAGE_COLOR_5",
        "PACKAGE_COLOR_6",
    )
    for i, key in enumerate(keys):
        label = page._cards[i].layout().itemAt(0).widget()
        assert get_color(key) in label.styleSheet()

    # 分隔线：SEPARATOR 主题色（两主题都有定义）
    sep = page._cards[0].layout().itemAt(3).widget()
    assert get_color("SEPARATOR") in sep.styleSheet()


def test_exchange_labels_use_resolved_hex(qapp) -> None:
    """Falsify：标签内联色必须是真实 hex，而非键名/空串（防 get_color 静默漏改）。

    旧实现 `get_color(color) or color` 对缺失键回退键名字符串（无效色），
    且 `"" in styleSheet` 恒真会让子串断言静默通过——hex 正则直接证伪两条路径。
    """
    import re

    from app.exchange_page import ExchangePage

    page = ExchangePage()
    for card in page._cards:
        label = card.layout().itemAt(0).widget()
        assert re.search(r"#[0-9A-Fa-f]{6}", label.styleSheet()), (
            f"标签内联色非有效 hex：{label.styleSheet()!r}"
        )


def test_pages_have_no_dead_error_state(qapp) -> None:
    """_error 死状态（只写不读）已删除，基类不再持有。"""
    from app.crafting_page import CraftingPage
    from app.exchange_page import ExchangePage

    assert not hasattr(CraftingPage(), "_error")
    assert not hasattr(ExchangePage(), "_error")


# ── T-04. 构造注入 client seam（C2-02）────────────────────


def test_crafting_page_injected_client_used_by_fetch(qapp) -> None:
    """构造注入：CraftingPage(client=fake) 后 _fetch 落在 fake 实例（断网能力）。"""
    from types import SimpleNamespace

    from app.crafting_page import CraftingPage

    calls: list[str] = []
    fake = SimpleNamespace(fetch_ov_data=lambda: (calls.append("ov"), [])[1])
    page = CraftingPage(client=fake)
    assert page._fetch() == []
    assert calls == ["ov"]


def test_exchange_page_injected_client_used_by_fetch(qapp) -> None:
    """构造注入：ExchangePage(client=fake) 后 _fetch 落在 fake 实例。"""
    from types import SimpleNamespace

    from app.exchange_page import ExchangePage

    calls: list[str] = []
    fake = SimpleNamespace(fetch_ammo_package_data=lambda: (calls.append("ammo"), [])[1])
    page = ExchangePage(client=fake)
    assert page._fetch() == []
    assert calls == ["ammo"]


def test_pages_without_client_build_own_kkrb_client(qapp) -> None:
    """client=None 现状兼容：自建 KkrbClient（既有直构用例语义不变）。"""
    from kkrb_client import KkrbClient

    from app.crafting_page import CraftingPage
    from app.exchange_page import ExchangePage

    assert isinstance(CraftingPage()._client, KkrbClient)
    assert isinstance(ExchangePage()._client, KkrbClient)


def test_profit_page_preload_fans_out_to_children(qapp) -> None:
    """C2-02：profit_page.preload() 扇出两子页 preload（单出口，不再各页直插）。"""
    from app.profit_page import ProfitPage

    page = ProfitPage()
    calls: list[str] = []
    page.crafting_page.preload = lambda: calls.append("crafting")  # type: ignore[method-assign]
    page.exchange_page.preload = lambda: calls.append("exchange")  # type: ignore[method-assign]
    page.preload()
    assert calls == ["crafting", "exchange"]

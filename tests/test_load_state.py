"""
LoadState 加载状态机转移矩阵单测（候选 2：fetch_page_base 状态机拆分）。

覆盖四态（idle/loading/loaded/failed）的全部转移：
- 正常链路 idle → loading → loaded
- can_load() 仅 loading 态为 False（防重入，不挡手动刷新）
- loaded 态可手动刷新（start() 重新进入 loading）
- failed → loading 重试
- start() loading 中拒绝返回 False 不抛异常
- succeed()/fail() 非 loading 态静默忽略
- is_loaded/is_loading 只读属性各态取值
"""

from __future__ import annotations

from app.load_state import LoadState

__all__ = []


def test_idle_to_loading_to_loaded() -> None:
    """正常链路：idle → loading → loaded，各态守卫与属性正确。"""
    s = LoadState()
    assert not s.is_loaded
    assert not s.is_loading
    assert s.can_load()

    assert s.start() is True
    assert s.is_loading
    assert not s.is_loaded
    assert not s.can_load()

    s.succeed()
    assert s.is_loaded
    assert not s.is_loading
    # loaded 后 can_load 恢复 True：手动刷新不被挡（防重入只挡 loading）
    assert s.can_load()


def test_can_load_false_while_loading() -> None:
    """loading 态 can_load() 为 False：重复/并发触发不会叠加加载。"""
    s = LoadState()
    s.start()
    assert not s.can_load()
    assert s.start() is False  # 加载中二次 start 拒绝


def test_loaded_allows_manual_refresh() -> None:
    """loaded 态可手动刷新：start() 重新进入 loading（kkrb 数据会变，刷新是核心操作）。"""
    s = LoadState()
    s.start()
    s.succeed()
    assert s.is_loaded

    assert s.can_load()
    assert s.start() is True
    assert s.is_loading
    assert not s.is_loaded


def test_failed_allows_retry() -> None:
    """失败可重试：fail() 后 can_load() 恢复 True，start() 重新进入 loading。"""
    s = LoadState()
    s.start()
    s.fail()
    assert not s.is_loaded
    assert not s.is_loading
    assert s.can_load()

    assert s.start() is True
    assert s.is_loading


def test_start_while_loading_returns_false() -> None:
    """start() loading 中返回 False，不抛异常且状态不变。"""
    s = LoadState()
    s.start()
    assert s.start() is False
    assert s.is_loading  # 仍保持 loading


def test_succeed_non_loading_is_silent() -> None:
    """succeed() 非 loading 态（idle/loaded）静默忽略，不改变状态。"""
    s = LoadState()
    s.succeed()  # idle
    assert not s.is_loaded

    s.start()
    s.succeed()
    s.succeed()  # loaded 后再 succeed
    assert s.is_loaded


def test_fail_non_loading_is_silent() -> None:
    """fail() 非 loading 态（idle/loaded）静默忽略，不改变状态。"""
    s = LoadState()
    s.fail()  # idle
    assert s.can_load()  # 仍为 idle

    s.start()
    s.fail()
    s.fail()  # failed 后再 fail
    assert s.can_load()  # 仍为 failed，可重试


def test_is_loaded_is_loading_values_per_state() -> None:
    """is_loaded/is_loading 只读属性在四态取值正确。"""
    s = LoadState()
    assert (s.is_loaded, s.is_loading) == (False, False)  # idle
    s.start()
    assert (s.is_loaded, s.is_loading) == (False, True)  # loading
    s.succeed()
    assert (s.is_loaded, s.is_loading) == (True, False)  # loaded
    s.start()  # loaded 手动刷新 → 重新进入 loading
    assert (s.is_loaded, s.is_loading) == (False, True)

    s2 = LoadState()
    s2.start()
    s2.fail()
    assert (s2.is_loaded, s2.is_loading) == (False, False)  # failed

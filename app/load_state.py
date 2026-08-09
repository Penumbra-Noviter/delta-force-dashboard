"""
页面数据加载状态机（零依赖纯逻辑，供 FetchPageBase 复用）。

四态：idle → loading → loaded / failed → loading（重试 / 刷新）。
转移规则与守卫全部内聚于此，UI 层只调用公开方法，不直接感知内部相位。
"""

from __future__ import annotations

__all__ = ["LoadState"]

from enum import Enum, auto


class _LoadPhase(Enum):
    """加载状态机的内部相位。"""

    IDLE = auto()
    LOADING = auto()
    LOADED = auto()
    FAILED = auto()


class LoadState:
    """页面数据懒加载状态机。

    转移规则：
    - ``start()``：idle/failed/loaded → loading（loaded 允许 = 手动刷新）；
      loading 中拒绝并返回 False
    - ``succeed()``：loading → loaded；非 loading 态静默忽略
    - ``fail()``：loading → failed；非 loading 态静默忽略

    「已加载是否自动重新加载」由调用方守卫区分（can_load 只挡重入）：
    - showEvent / preload 用 ``is_loaded`` 判「已加载不自动刷」；
    - 用户点刷新走 ``_load_data``，loaded 态经 ``can_load()`` 放行强制重载。
    """

    def __init__(self) -> None:
        self._phase = _LoadPhase.IDLE

    def can_load(self) -> bool:
        """是否允许发起加载（仅 loading 中为 False——防重入，不挡手动刷新）。"""
        return self._phase is not _LoadPhase.LOADING

    def start(self) -> bool:
        """尝试进入 loading 态；loading 中返回 False，不抛异常。"""
        if not self.can_load():
            return False
        self._phase = _LoadPhase.LOADING
        return True

    def succeed(self) -> None:
        """标记加载成功：loading → loaded；非 loading 态静默忽略。"""
        if self._phase is _LoadPhase.LOADING:
            self._phase = _LoadPhase.LOADED

    def fail(self) -> None:
        """标记加载失败：loading → failed；非 loading 态静默忽略。"""
        if self._phase is _LoadPhase.LOADING:
            self._phase = _LoadPhase.FAILED

    @property
    def is_loaded(self) -> bool:
        """是否已成功加载（只读）。"""
        return self._phase is _LoadPhase.LOADED

    @property
    def is_loading(self) -> bool:
        """是否加载中（只读）。"""
        return self._phase is _LoadPhase.LOADING

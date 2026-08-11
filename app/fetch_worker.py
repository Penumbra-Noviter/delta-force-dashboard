"""后台请求 worker：将同步网络调用移出 UI 线程。

QThread 子类，在 run() 中执行传入的可调用对象，
通过 done/error 信号回传结果，UI 线程无阻塞。

提供 shutdown() 安全关闭：阻塞中的 urllib 请求无法强制中断，
wait() 超时后转入「逃生舱」托管（脱离父子关系 + 模块级强引用），
保证运行中的线程在任何情况下都不会被销毁（T-01）。
"""

from __future__ import annotations

__all__ = ["FetchWorker"]

import atexit
import logging
import os
import time
from typing import Any, Callable

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

#: shutdown() 超时后仍在运行的 worker 逃生舱。
#: 模块级强引用阻止 GC 销毁运行中的线程；线程结束后经 finished 信号自行清理。
_detached_workers: set[FetchWorker] = set()

#: 解释器退出前等待逃生舱线程的总预算（秒）。逃生舱线程可能阻塞在不可中断
#: 的网络调用（urllib 的 timeout 不覆盖 Windows DNS 解析 getaddrinfo，可
#: 无限挂起）——无限等待会让进程在窗口关闭后永久残留：残留进程占着单实例
#: 锁，后续启动被静默拦截（「窗口未出现但后台有进程」）。预算用尽强杀进程。
_DRAIN_TIMEOUT_S = 5.0


@atexit.register
def _drain_detached_workers() -> None:
    """解释器退出前等待逃生舱 worker 结束；有界等待，超时强杀进程。

    正常场景：逃生舱线程多为已超时的网络请求，socket 超时（_TIMEOUT=10s）
    内自行结束，wait 返回后进程正常退出。异常场景（DNS 挂起等不可中断
    阻塞）：预算用尽仍在线程 → os._exit(0) 跳过 Python/Qt 析构直接终止
    进程——运行中 QThread 随进程终结，不会触发 "QThread: Destroyed while
    thread is still running" abort，进程绝不残留。
    """
    deadline = time.monotonic() + _DRAIN_TIMEOUT_S
    for worker in tuple(_detached_workers):
        remaining_ms = int((deadline - time.monotonic()) * 1000)
        if remaining_ms <= 0:
            break
        logger.warning("等待后台请求线程退出（shutdown 超时转入逃生舱）…")
        worker.wait(remaining_ms)
    if _detached_workers:  # 预算用尽仍有线程 → 强杀进程（绝不残留）
        logger.warning("逃生舱线程仍在运行，强制结束进程（请求结果已丢弃）")
        logging.shutdown()
        os._exit(0)


class FetchWorker(QThread):
    """在后台线程执行任意可调用对象，通过信号回传结果。

    用法：
        worker = FetchWorker(client.fetch_ov_data)
        worker.done.connect(on_done)
        worker.error.connect(on_error)
        worker.start()

    调用方需持有 worker 引用（如 self._worker = ...），否则 GC 会
    在线程仍在运行时回收 QThread 并触发警告。_loading 标志位防止重入，
    保证新 worker 启动时前一个已结束。

    关闭（T-01）：调用 shutdown()（必须从 GUI 线程）请求停止并等待线程
    结束；阻塞中的网络请求无法强制中断，wait() 超时后 worker 脱离父对象
    并由模块级逃生舱托管，线程结束后自动清理——运行中的线程绝不会被销毁，
    也就不会触发 "QThread: Destroyed while thread is still running" abort。
    """

    done = Signal(object)   # 成功结果
    error = Signal(object)  # 异常对象（调用方按类型区分处理）

    def __init__(self, fn: Callable[[], Any], parent=None) -> None:
        super().__init__(parent)
        self._fn = fn
        self.finished.connect(self._on_finished)

    def run(self) -> None:
        try:
            if self.isInterruptionRequested():
                return
            self.done.emit(self._fn())
        except Exception as e:
            self.error.emit(e)

    def shutdown(self, timeout_ms: int = 300) -> bool:
        """请求停止并等待线程结束（必须从 GUI 线程调用）。

        Args:
            timeout_ms: 等待线程结束的最长毫秒数。

        Returns:
            True：线程已结束；False：超时仍未结束——worker 已脱离父子
            关系并转入逃生舱托管，不会被销毁，也不会触发 Qt abort。
        """
        if not self.isRunning():
            return True
        self.requestInterruption()
        if self.wait(timeout_ms):
            return True
        logger.warning(
            "后台请求线程 %dms 内未退出，转入逃生舱托管（结果将被丢弃）",
            timeout_ms,
        )
        self.setParent(None)
        _detached_workers.add(self)
        return False

    def _on_finished(self) -> None:
        """线程结束后从逃生舱移除（信号在 GUI 线程投递）。"""
        _detached_workers.discard(self)

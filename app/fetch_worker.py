"""后台请求 worker：将同步网络调用移出 UI 线程。

QThread 子类，在 run() 中执行传入的可调用对象，
通过 done/error 信号回传结果，UI 线程无阻塞。
"""

from __future__ import annotations

__all__ = ["FetchWorker"]

from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


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
    """

    done = Signal(object)   # 成功结果
    error = Signal(object)  # 异常对象（调用方按类型区分处理）

    def __init__(self, fn: Callable[[], Any], parent=None) -> None:
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.error.emit(e)

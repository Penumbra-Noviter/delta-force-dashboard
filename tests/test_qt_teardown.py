"""DFD-7 回归：Qt 用例进程退出不得以堆损坏收尾。

背景（2026-09-08 定位）：PySide6 的 QObject 引用环（信号连接构成
page ↔ worker ↔ 绑定方法）若交给解释器关闭期的 GC 回收，Qt 对象会在
QApplication 销毁**之后**才析构 → Windows 堆损坏（退出码 0xC0000374）。

症状是「文件单独运行时全部用例通过、进程退出码异常」，故本测试用子进程
直接锁用户可见症状：单独运行 `tests/test_fetch_pages.py`（36 用例，含 4 个
起 FetchWorker 线程的错误态用例）必须退出码 0。

修复：`tests/conftest.py::qt_teardown`（每个用例后强制 gc + DeferredDelete
冲刷）。对照实验：基线 6/6 崩溃、空夹具对照 6/6 崩溃、修复 0/6。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__all__ = []


def test_single_file_run_exits_without_heap_corruption() -> None:
    """子进程单独运行 test_fetch_pages.py → 退出码必须为 0（DFD-7 症状锁）。"""
    repo = Path(__file__).resolve().parent.parent
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            # 独立 basetemp：避免子会话启动时清空父会话的临时目录
            "--basetemp=.pytest_cache/dfd7_subprocess",
            "tests/test_fetch_pages.py",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, (
        f"子进程退出码 {proc.returncode}（0x{proc.returncode & 0xFFFFFFFF:08X}）"
        f"——Qt 对象在解释器关闭期析构？\n"
        f"stdout tail:\n{proc.stdout[-2000:]}\nstderr tail:\n{proc.stderr[-2000:]}"
    )

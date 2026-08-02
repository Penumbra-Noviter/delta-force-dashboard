"""共享 pytest fixtures：进程级 QApplication（offscreen）+ settings.json 隔离。

C5 评审后从 test_table_theme / test_input_panel / test_ui_smoke 收敛而来
（qapp 原 3 处重复、settings_guard 原 2 处重复），供所有 Qt 用例复用。
offscreen 平台必须在任何 QApplication 创建前设置。
"""

from __future__ import annotations

import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

__all__ = []


@pytest.fixture(scope="module")
def qapp():
    """进程级 QApplication（offscreen），供主窗口/表格/图表控件创建。"""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def settings_guard(tmp_path):
    """隔离真实 settings.json：测试期间重定向到 tmp，避免 closeEvent 污染用户设置。"""
    import app.main_window as mw

    orig = mw.SETTINGS_FILE
    mw.SETTINGS_FILE = tmp_path / "settings.json"
    yield
    mw.SETTINGS_FILE = orig


@pytest.fixture
def type_and_settle(qapp):
    """QTest 键入 + 等待去抖定时器，驱动真实事件链路（D-04）。

    D-04 原则：被测试的路径=真实路径。校验/联动类用例不再直调
    `refresh_validity()`（那是同步 seam，不是测试后门），改用 QTest
    `keyClicks` 键入文本，触发 textChanged→150ms 去抖→validity_changed
    →save_btn 的完整真实链路；`qWait(settle_ms)` 让去抖定时器触发。
    """
    from PySide6.QtTest import QTest

    def _type_and_settle(widget, text, settle_ms=200):
        widget.setFocus()
        widget.clear()
        QTest.keyClicks(widget, text)
        QTest.qWait(settle_ms)

    return _type_and_settle

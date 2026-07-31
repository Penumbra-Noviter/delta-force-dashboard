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

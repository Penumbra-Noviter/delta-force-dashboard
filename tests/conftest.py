"""共享 pytest fixtures：进程级 QApplication（offscreen）+ settings.json 隔离。

C5 评审后从 test_table_theme / test_input_panel / test_ui_smoke 收敛而来
（qapp 原 3 处重复、settings_guard 原 2 处重复），供所有 Qt 用例复用。
offscreen 平台必须在任何 QApplication 创建前设置。
C2-03：make_stub_client 工厂为页面/窗口构造注入提供零网络 stub client
（替代已删除的 offscreen 哨兵，见 app/fetch_page_base.preload）。
"""

from __future__ import annotations

import os
from collections.abc import Callable
from types import SimpleNamespace

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

__all__ = []


def make_stub_client(
    ov_impl: Callable[[], list] | None = None,
    ammo_impl: Callable[[], list] | None = None,
    bonus_impl: Callable[[], list] | None = None,
) -> SimpleNamespace:
    """构造零网络 stub client（SimpleNamespace），供页面/窗口构造注入。

    C2-03：preload() 不再读 QT_QPA_PLATFORM 哨兵——测试改用本工厂注入
    stub client 压制网络。fetch_ov_data / fetch_ammo_package_data /
    fetch_bonus_door_data 在 FetchWorker 线程内立即返回（默认 []），
    preload 仍走真实后台线程，线程行为测试能力不丢失。注入后仍可对实例
    属性再赋值（如以阻塞 stub 覆盖 fetch_ov_data，见 test_fetch_pages 的
    T-01 用例）。

    Args:
        ov_impl: fetch_ov_data 的可调用实现（默认返回 []）。
        ammo_impl: fetch_ammo_package_data 的可调用实现（默认返回 []）。
        bonus_impl: fetch_bonus_door_data 的可调用实现（默认返回 []，
            BD-02 新增；既有调用方零改动）。
    """
    return SimpleNamespace(
        fetch_ov_data=ov_impl or (lambda: []),
        fetch_ammo_package_data=ammo_impl or (lambda: []),
        fetch_bonus_door_data=bonus_impl or (lambda: []),
    )


def make_store(tmp_path, max_backups: int = 3):
    """tmp_path 隔离的 DataStore（data.json + data.json.bak + 滚动备份上限）。

    C7 收敛：原 test_data_store 模块级 make_store 与 MainWindow 测试内联
    `DataStore(tmp_path/...，tmp_path/...)` 双参构造共 19 处复制，统一收容
    （文件名双形态 data.json/d.json 的上游测试无文件名依赖，语义等价）。
    """
    from data_store import DataStore

    return DataStore(
        data_file=tmp_path / "data.json",
        backup_file=tmp_path / "data.json.bak",
        max_backups=max_backups,
    )


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


@pytest.fixture
def theme_guard():
    """隔离模块级主题状态：测试前复位为 light，测试后恢复原值（C3 收敛，防状态泄漏）。"""
    import app.theme as theme_mod

    saved = theme_mod._current_theme
    theme_mod.set_theme("light")
    yield
    theme_mod._current_theme = saved


@pytest.fixture(autouse=True)
def cleanup_encryption():
    """每个测试后清理 json_file 全局加密密钥（C2 从两测试文件收敛而来）。

    set_encryption_key(None) 幂等，对不涉及加密的测试无副作用——统一收容
    可防止「新加密测试忘记清理 → 全局密钥泄漏给后续用例」。
    """
    from json_file import set_encryption_key

    yield
    set_encryption_key(None)

"""
主题双轨收敛（候选 5）回归测试：按钮样式单一来源为 QSS。

背景：同一控件样式曾存在「QSS 全局定义 + 内联 setStyleSheet」两处，
内联优先导致过 bug（内联与 QSS 不同步）。收敛后：
- button_style() 已删除（不再有第二轨道）；
- generate_qss 以属性选择器承载 reuseBtn danger 态；
- InputPanel 复用模式切换走 setProperty("state") + repolish，
  saveBtn 编辑模式样式完全由 QSS #saveBtn 提供。
"""

from __future__ import annotations

import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

__all__ = []


def test_generate_qss_contains_reuse_btn_danger_selector():
    """QSS 含 reuseBtn danger 属性选择器及其主题色值（light/dark 双主题）。"""
    from app.theme import THEMES, generate_qss

    for name, palette in THEMES.items():
        qss = generate_qss(name)
        assert 'QPushButton#reuseBtn[state="danger"]' in qss
        # 与原 button_style("danger") 对应的全部色值均落入 QSS 模板
        assert palette["DANGER_BG"] in qss
        assert palette["DANGER_FG"] in qss
        assert palette["DANGER_BORDER"] in qss
        assert palette["DANGER_HOVER_BG"] in qss
        assert palette["BTN_HOVER_FG"] in qss
        # hover 变体同样限定在 danger 态选择器内
        assert 'QPushButton#reuseBtn[state="danger"]:hover' in qss


def test_button_style_removed():
    """button_style 已删除：单一轨道收敛的静态守卫（防复发）。"""
    import app.theme as theme_mod

    assert not hasattr(theme_mod, "button_style")


def test_reuse_mode_switches_state_property(qapp):
    """复用模式切换：state 属性驱动 QSS 选择器，不再走内联 setStyleSheet。"""
    from app.input_panel import InputPanel

    ip = InputPanel()
    ip.set_reuse_mode()
    assert ip.reuse_btn.property("state") == "danger"
    # 内联样式已收敛：reuse/save 按钮均无内联残留
    assert ip.reuse_btn.styleSheet() == ""
    assert ip.save_btn.styleSheet() == ""

    ip.cancel_reuse()
    assert ip.reuse_btn.property("state") == ""
    assert ip.reuse_btn.styleSheet() == ""


def test_edit_mode_keeps_no_inline_style(qapp):
    """编辑模式不再给 saveBtn 设内联样式（QSS #saveBtn 单一来源）。"""
    from app.input_panel import InputPanel

    ip = InputPanel()
    ip.set_edit_mode("2026-07-25", 100.0, 200.0)
    assert ip.save_btn.styleSheet() == ""

    ip.cancel_edit()
    assert ip.save_btn.styleSheet() == ""

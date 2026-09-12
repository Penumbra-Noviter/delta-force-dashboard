"""
多主题（05）回归测试：ThemeDialog 结果契约 + 预填 + 取色 + 预览 + 软提示。

规则来源（.scratch/multi-theme/issues/05）：
- base 下拉（light/dark/nord）+ 6 锚点取色 + 实时预览 + 对比度软提示；
- 打开时预填 base 与 6 锚点（无自定义则以当前主题作 base）；
- QColorDialog 阻塞由 monkeypatch 规避；
- 结果契约 (base, overrides)，仅 6 锚点、非展开 50 键；reject 无副作用；
- 不直接 set_theme、模块顶层禁 get_color、不持有全局主题状态。
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog

from app import theme as theme_mod
from app.theme_dialog import ThemeDialog

__all__ = []


@pytest.fixture
def pick_color(monkeypatch):
    """monkeypatch QColorDialog.getColor 返回固定色，防阻塞（.exec() 会阻塞 offscreen）。"""
    captured: dict = {}

    def _get_color(initial=None, parent=None, title=""):
        captured["initial"] = initial
        captured["title"] = title
        return QColor("#010203")

    monkeypatch.setattr(QColorDialog, "getColor", _get_color)
    return captured


def test_constructs_base_and_six_anchors(qapp):
    """base 下拉含 light/dark/nord，6 锚点取色按钮齐全。"""
    dlg = ThemeDialog("light")

    assert [dlg._base_combo.itemText(i) for i in range(dlg._base_combo.count())] == [
        "light", "dark", "nord",
    ]
    assert set(dlg._color_buttons) == set(theme_mod.ANCHOR_KEYS)
    dlg.close()


def test_prefills_base_and_overrides(qapp):
    """打开时预填：base 生效，overrides 覆盖 base 默认锚点，其余继承 base。"""
    dlg = ThemeDialog("dark", {"BTN_BG": "#010203"})

    assert dlg._base_combo.currentData() == "dark"
    assert dlg._overrides["BTN_BG"] == "#010203"
    assert dlg._overrides["BG"] == theme_mod.THEMES["dark"]["BG"]
    dlg.close()


def test_prefills_without_custom_uses_current_base(qapp):
    """无自定义 overrides 时以 base 的 6 锚点默认值预填。"""
    dlg = ThemeDialog("nord")

    assert dlg._base_combo.currentData() == "nord"
    assert dlg._overrides["BTN_BG"] == theme_mod.THEMES["nord"]["BTN_BG"]
    assert dlg._overrides["FG_NEG"] == theme_mod.THEMES["nord"]["FG_NEG"]
    dlg.close()


def test_base_change_resets_anchors(qapp):
    """base 下拉变更：6 锚点重置为新 base 默认值并刷新预览。"""
    dlg = ThemeDialog("light", {"BTN_BG": "#010203"})

    dlg._base_combo.setCurrentIndex(1)  # → dark

    assert dlg._base_combo.currentData() == "dark"
    assert dlg._overrides["BTN_BG"] == theme_mod.THEMES["dark"]["BTN_BG"]
    assert dlg._overrides["BG"] == theme_mod.THEMES["dark"]["BG"]
    dlg.close()


def test_pick_color_updates_anchor(qapp, pick_color):
    """6 锚点经 QColorDialog 取色：点击锚点按钮更新对应 overrides。"""
    dlg = ThemeDialog("light")

    dlg._color_buttons["BTN_BG"].click()

    assert dlg._overrides["BTN_BG"] == "#010203"
    assert pick_color["title"] == "按钮背景"
    dlg.close()


def test_preview_reflects_color_change(qapp, pick_color):
    """实时预览：改色后示例按钮内联样式反映新锚点色。"""
    dlg = ThemeDialog("light")

    dlg._color_buttons["BTN_BG"].click()

    assert "#010203" in dlg._preview_btn.styleSheet()
    dlg.close()


def test_contrast_hints_shown_on_low_contrast(qapp):
    """对比度软提示：白底白字按钮（BTN_BG vs BTN_FG <4.5:1）→ 非阻断提示。"""
    dlg = ThemeDialog("light", {"BTN_BG": "#ffffff"})

    assert "按钮文字" in dlg._hints_label.text()
    dlg.close()


def test_contrast_hints_empty_when_ok(qapp):
    """达标色板无软提示（hint label 为空）。"""
    dlg = ThemeDialog("light", {
        "BTN_BG": "#000000",  # 黑按钮 + 白字 → 高对比
        "BG": "#ffffff",      # 白底
        "FG_TODAY": "#000000",
        "FG_POS": "#008000",
        "FG_NEG": "#800000",
    })

    assert dlg._hints_label.text() == ""
    dlg.close()


def test_result_contract_returns_base_and_overrides(qapp, pick_color):
    """结果契约：accept 后 result() 返回 (base, overrides)，仅含实际覆盖锚点。"""
    dlg = ThemeDialog("dark")

    dlg._color_buttons["BTN_BG"].click()  # → #010203
    dlg.accept()

    base, overrides = dlg.result()
    assert base == "dark"
    assert overrides == {"BTN_BG": "#010203"}
    dlg.close()


def test_result_overrides_subset_of_six_anchors(qapp):
    """结果 overrides 键集 ⊆ 6 锚点（非展开 50 键）。"""
    dlg = ThemeDialog("light")

    _, overrides = dlg.result()
    assert set(overrides) <= set(theme_mod.ANCHOR_KEYS)
    dlg.close()


def test_reject_has_no_side_effect(qapp, pick_color):
    """reject 后 result 仍可用且无副作用（不 set_theme / 不落盘）。"""
    dlg = ThemeDialog("light")

    dlg._color_buttons["BTN_BG"].click()
    dlg.reject()

    assert dlg.result() == ("light", {"BTN_BG": "#010203"})
    dlg.close()


def test_dialog_does_not_mutate_global_theme(qapp, theme_guard, pick_color):
    """对话框构造/取色/result 不改变全局主题状态（不 set_theme / 不 register_custom）。"""
    before_theme = theme_mod._current_theme
    before_custom = dict(theme_mod.CUSTOM)

    dlg = ThemeDialog("light")
    dlg._color_buttons["BTN_BG"].click()
    dlg.result()

    assert theme_mod._current_theme == before_theme
    assert theme_mod.CUSTOM == before_custom
    dlg.close()


def test_module_no_top_level_get_color_or_set_theme():
    """C1：theme_dialog.py 模块顶层禁 get_color；全文不调 set_theme。"""
    import ast
    import pathlib

    import app.theme_dialog as td

    source = pathlib.Path(td.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in tree.body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                if sub.func.id == "get_color":
                    pytest.fail(f"theme_dialog 模块顶层调用 get_color: L{sub.lineno}")
    assert "set_theme(" not in source, "ThemeDialog 不得直接调用 set_theme"

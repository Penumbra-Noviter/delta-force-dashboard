"""
多主题（01）回归测试：resolve_palette 统一取色通路 + 自定义槽位。

规则来源（.scratch/multi-theme/spec.md + issues/01）：
- resolve_palette(name)：内置命中直返；custom 命中合并 {**THEMES[base], **overrides}；
  其余回退 THEMES["light"]；全函数永不 raise。
- register_custom(name, base, overrides)：name 与内置重名、或 base 非内置时
  拒绝写入并记 warning（CUSTOM 保持原状，不 raise）；合法写入 {"base", "overrides"}。
- set_theme 接受 THEMES ∪ CUSTOM；get_color / generate_qss 均经 resolve_palette 取色。

均为纯函数/模块级状态测试，无 Qt、无文件 IO；CUSTOM 槽位由 theme_guard 隔离。
"""

from __future__ import annotations

import logging

from app import theme as theme_mod

__all__ = []


# ── resolve_palette：内置直返 / 未知回退 ──────────────────


def test_resolve_palette_builtin_returns_same_palette() -> None:
    """内置命中直返该色板对象（不复制，不重解析）。"""
    for name, palette in theme_mod.THEMES.items():
        assert theme_mod.resolve_palette(name) is palette


def test_resolve_palette_unknown_falls_back_to_light() -> None:
    """未知名（含空串）回退 light 色板，不 raise。"""
    assert theme_mod.resolve_palette("no_such_theme") is theme_mod.THEMES["light"]
    assert theme_mod.resolve_palette("") is theme_mod.THEMES["light"]
    assert theme_mod.resolve_palette("CUSTOM") is theme_mod.THEMES["light"]


# ── register_custom：合法写入 ─────────────────────────────


def test_register_custom_writes_base_and_overrides(theme_guard) -> None:
    """合法注册写入 {"base", "overrides"}，不展开 base 的 50 键快照。"""
    overrides = {"BTN_BG": "#123456"}
    theme_mod.register_custom("custom", "dark", overrides)

    assert "custom" in theme_mod.CUSTOM
    assert theme_mod.CUSTOM["custom"] == {"base": "dark", "overrides": overrides}


# ── resolve_palette：custom 合并覆盖 base ─────────────────


def test_resolve_palette_custom_merges_overrides_over_base(theme_guard) -> None:
    """custom 命中返回 override 覆盖 base 后的完整色板，其余键继承 base。"""
    theme_mod.register_custom(
        "custom",
        "dark",
        {"BTN_BG": "#010203", "FG_TODAY": "#abcdef"},
    )

    merged = theme_mod.resolve_palette("custom")

    # override 覆盖 base 同名键
    assert merged["BTN_BG"] == "#010203"
    assert merged["FG_TODAY"] == "#abcdef"
    # 未覆盖键继承 base
    assert merged["BG"] == theme_mod.THEMES["dark"]["BG"]
    assert merged["FG_POS"] == theme_mod.THEMES["dark"]["FG_POS"]


def test_resolve_palette_custom_does_not_mutate_builtin(theme_guard) -> None:
    """合并产生新 dict，覆盖不污染内置色板（只读视图语义）。"""
    base_btn_bg = theme_mod.THEMES["dark"]["BTN_BG"]
    theme_mod.register_custom("custom", "dark", {"BTN_BG": "#000000"})

    theme_mod.resolve_palette("custom")

    assert theme_mod.THEMES["dark"]["BTN_BG"] == base_btn_bg


# ── register_custom：非法注册拒绝（不 raise，CUSTOM 原状） ─


def test_register_custom_rejects_name_colliding_with_builtin(
    caplog, theme_guard
) -> None:
    """name 与内置主题重名 → 拒绝写入 + 记 warning，CUSTOM 保持原状。"""
    with caplog.at_level(logging.WARNING, logger="app.theme"):
        theme_mod.register_custom("light", "dark", {"BTN_BG": "#123456"})

    assert theme_mod.CUSTOM == {}
    assert [r for r in caplog.records if r.levelno == logging.WARNING], (
        "重名注册应记 warning"
    )


def test_register_custom_rejects_non_builtin_base(caplog, theme_guard) -> None:
    """base 非内置主题 → 拒绝写入 + 记 warning，CUSTOM 保持原状。"""
    with caplog.at_level(logging.WARNING, logger="app.theme"):
        theme_mod.register_custom("custom", "solarized", {"BTN_BG": "#123456"})

    assert theme_mod.CUSTOM == {}
    assert [r for r in caplog.records if r.levelno == logging.WARNING], (
        "base 非内置应记 warning"
    )


def test_register_custom_rejection_keeps_existing_slot(theme_guard) -> None:
    """非法注册不覆盖已存在的合法槽位（CUSTOM 原状）。"""
    theme_mod.register_custom("custom", "dark", {"BTN_BG": "#111111"})

    # name 与内置重名（"dark"）→ 拒绝，原槽位不动
    theme_mod.register_custom("dark", "light", {"BTN_BG": "#222222"})

    assert theme_mod.CUSTOM["custom"] == {
        "base": "dark",
        "overrides": {"BTN_BG": "#111111"},
    }


# ── 三入口走 resolve_palette ──────────────────────────────


def test_set_theme_accepts_custom(theme_guard) -> None:
    """set_theme 接受已注册 custom；get_color 经 resolve_palette 返回 override 值。"""
    theme_mod.register_custom("custom", "dark", {"BTN_BG": "#010203"})

    theme_mod.set_theme("custom")

    assert theme_mod.get_color("BTN_BG") == "#010203"
    assert theme_mod.get_color("BG") == theme_mod.THEMES["dark"]["BG"]


def test_set_theme_ignores_unknown(theme_guard) -> None:
    """未知名不改变当前主题（沿用 resolve_palette 回退语义，静默忽略）。"""
    theme_mod.set_theme("dark")
    theme_mod.set_theme("no_such_theme")

    assert theme_mod._current_theme == "dark"


def test_generate_qss_custom_uses_merged_palette(theme_guard) -> None:
    """generate_qss("custom") 用合并色板渲染，不因缺键 KeyError，override 落入 QSS。"""
    theme_mod.register_custom(
        "custom",
        "light",
        {"BTN_BG": "#010203", "FG_TODAY": "#abcdef"},
    )

    qss = theme_mod.generate_qss("custom")

    assert "#010203" in qss
    assert "#abcdef" in qss
    # base 键齐保证，约 20 处 t[...] 直接索引不抛 KeyError（能生成即通过）
    assert "QPushButton#saveBtn" in qss
    assert theme_mod.THEMES["light"]["BG"] in qss  # 未覆盖键继承 base


def test_generate_qss_unknown_falls_back_to_light() -> None:
    """generate_qss 未知名回退 light 色板渲染。"""
    qss = theme_mod.generate_qss("no_such_theme")

    assert theme_mod.THEMES["light"]["BG"] in qss
    assert "QPushButton#saveBtn" in qss


# ── get_color 未知键语义不变（C1-06） ─────────────────────


def test_get_color_unknown_key_warns_no_raise(caplog) -> None:
    """未知键返回 "" + 记 warning（含键名），不 raise（防御语义保持）。"""
    with caplog.at_level(logging.WARNING, logger="app.theme"):
        assert theme_mod.get_color("NON_EXISTENT_KEY") == ""

    assert any("NON_EXISTENT_KEY" in r.message for r in caplog.records), (
        "warning 应含键名"
    )


# ── resolve_palette 永不 raise（畸形 custom 防御） ────────


def test_resolve_palette_never_raises_on_malformed_custom(theme_guard) -> None:
    """CUSTOM 槽位畸形（base 非法 / 缺 overrides）→ 回退 light，不 raise。"""
    theme_mod.CUSTOM["custom"] = {"base": "nope"}
    assert theme_mod.resolve_palette("custom") is theme_mod.THEMES["light"]

    theme_mod.CUSTOM["custom"] = "not-a-dict"  # type: ignore[dict-item]
    assert theme_mod.resolve_palette("custom") is theme_mod.THEMES["light"]


# ── 信号映射经 get_color → resolve_palette ───────────────


def test_signal_color_uses_custom_palette(theme_guard) -> None:
    """signal_color 经 get_color → resolve_palette：custom 下返回 override 信号色。"""
    from signals import RateSignal

    theme_mod.register_custom("custom", "light", {"FG_POS": "#010203"})
    theme_mod.set_theme("custom")

    assert theme_mod.signal_color(RateSignal.POSITIVE) == "#010203"
    assert theme_mod.signal_color(RateSignal.NEUTRAL) == theme_mod.THEMES["light"]["FG_MUTED"]


def test_summary_style_both_branches(theme_guard) -> None:
    """summary_style 两分支（NONE 小号灰字 / 非 NONE 大号信号色）均经 resolve_palette。"""
    from signals import RateSignal

    none_style = theme_mod.summary_style(RateSignal.NONE)
    pos_style = theme_mod.summary_style(RateSignal.POSITIVE)

    assert "16px" in none_style
    assert "22px" in pos_style
    assert theme_mod.get_color("FG_POS") in pos_style

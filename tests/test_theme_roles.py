"""
U-03 色彩角色系统化回归测试：装饰色（包标签）角色规则机器证伪。

规则来源（TO-TICKETS.md U-03 + app/theme.py 注释）：
- 键名如实：7 包色收敛为单一角色键 PACKAGE_COLOR_0~6（双主题各自定义，
  不抽常亮色防 Locality 坑）；CHART_SERIES_*/PACKAGE_COLOR_* 双套键已删除。
- 装饰 ≠ 语义：装饰键值 ≠ FG_POS/FG_NEG，且 HSL 亮度差 ≥ 0.05
  （dark 下旧 CHART_SERIES_2/3 与语义色完全同值——5 级包标签=亏色、3 级包标签=涨色，必须修）。
- 明度带量化：light 深墨带 L∈[0.20,0.32] / dark 亮彩带 L∈[0.72,0.84]，
  带内宽度 ≤ 0.10，饱和度 ≥ 0.55（colorsys 计算）。
- 两两可分辨：同主题内 7 装饰色两两 ΔE76 ≥ 25（防明度统一后色相过近更难分）。
- 可读性底线：装饰色对 CARD_BG 对比度 ≥ 4.5:1（WCAG AA，包标签文字浅底深字）。

阈值均为「现状必然违反、目标色板留有余量」的固定字面量（非用实现重算，非恒真）。
"""

from __future__ import annotations

import colorsys

import pytest

from app import theme as theme_mod

__all__ = []


@pytest.fixture
def theme_guard():
    """隔离模块级主题状态：测试前复位为 light，测试后恢复原值（防状态泄漏）。"""
    saved = theme_mod._current_theme
    theme_mod.set_theme("light")
    yield
    theme_mod._current_theme = saved


# ── 角色规则阈值（U-03 验收标准量化） ─────────────────────

DECORATIVE_KEYS = tuple(f"PACKAGE_COLOR_{i}" for i in range(7))  # 固定键清单 0~6
DELTA_L_MIN = 0.05        # 装饰 vs 语义的 HSL 亮度差下限
LIGHT_BAND = (0.20, 0.32)  # light 深墨带
DARK_BAND = (0.72, 0.84)   # dark 亮彩带
BAND_WIDTH_MAX = 0.10     # 带内最大宽度
SATURATION_MIN = 0.55     # 饱和度下限
DELTA_E_MIN = 25.0        # 两两色差（ΔE76）下限
CONTRAST_MIN = 4.5        # 标签文字对比度（WCAG AA）


# ── 颜色计算辅助（仅测试用，标准 sRGB/CIE 公式） ───────────


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    """'#RRGGBB' → (r, g, b) 0~1 归一化分量。"""
    c = color.lstrip("#")
    return tuple(int(c[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def _hls(color: str) -> tuple[float, float, float]:
    """'#RRGGBB' → (hue, lightness, saturation)，colorsys 标准公式。"""
    return colorsys.rgb_to_hls(*_hex_to_rgb(color))  # type: ignore[arg-type]


def _lin(c: float) -> float:
    """sRGB 分量 → 线性光分量（WCAG 反 gamma）。"""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(color: str) -> float:
    """sRGB → WCAG 相对亮度（0~1）。"""
    r, g, b = (_lin(c) for c in _hex_to_rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(a: str, b: str) -> float:
    """两色 WCAG 对比度（(L1+0.05)/(L2+0.05)）。"""
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _lab(color: str) -> tuple[float, float, float]:
    """sRGB → CIELAB（D65），用于 ΔE76 色差。"""
    r, g, b = (_lin(c) for c in _hex_to_rgb(color))
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    def _f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = _f(x / 0.95047), _f(y / 1.0), _f(z / 1.08883)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _delta_e76(a: str, b: str) -> float:
    """CIE76 色差（欧氏距离，Lab 空间）。"""
    la, lb = _lab(a), _lab(b)
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5


# ── 键名如实：单一角色键集 ────────────────────────────────


def test_package_color_keys_defined_in_both_themes() -> None:
    """固定键清单 PACKAGE_COLOR_0~6 在 light/dark 双主题均存在且非空。"""
    for theme in theme_mod.THEMES:
        palette = theme_mod.THEMES[theme]
        for key in DECORATIVE_KEYS:
            assert key in palette, f"{theme} 缺少装饰键 {key}"
            assert palette[key], f"{theme} 装饰键 {key} 为空"


def test_chart_series_and_old_package_keys_removed() -> None:
    """CHART_SERIES_*/PACKAGE_COLOR_* 双套键已删除（键名如实的静态守卫）。"""
    for theme in theme_mod.THEMES:
        palette = theme_mod.THEMES[theme]
        for stale in ("CHART_SERIES_0", "CHART_SERIES_1", "CHART_SERIES_2", "CHART_SERIES_3"):
            assert stale not in palette, f"{theme} 残留撒谎键名 {stale}"
    # 每主题装饰键恰好 7 个（PACKAGE_COLOR_0~6），无第三套键混入
    for theme in theme_mod.THEMES:
        keys = [k for k in theme_mod.THEMES[theme] if k.startswith("PACKAGE_COLOR_")]
        assert sorted(keys) == sorted(DECORATIVE_KEYS), f"{theme} 装饰键清单漂移：{keys}"


# ── 键引用完整：exchange_page 引用的键全部可解析 ───────────


def test_exchange_referenced_keys_resolve_in_both_themes(theme_guard) -> None:
    """兑换页 _PACKAGE_CONFIG 引用的全部色键，双主题下 get_color 均非空。

    防 get_color() 缺失键静默返回 ""（漏改不报错 → 标签色直接失效）。
    theme_guard：循环以 dark 结束时恢复原主题，防全局状态泄漏给后续测试。
    """
    from app.exchange_page import _PACKAGE_CONFIG

    referenced = [cfg.color for cfg in _PACKAGE_CONFIG]
    assert len(referenced) == 7, "包类型配置应为 7 项"
    assert set(referenced) == set(DECORATIVE_KEYS), f"引用键集漂移：{referenced}"
    for theme in theme_mod.THEMES:
        theme_mod.set_theme(theme)
        for key in referenced:
            resolved = theme_mod.get_color(key)
            assert resolved, f"{theme} 下 get_color({key}) 返回空——键缺失漏改"


def test_decorative_values_are_six_digit_hex() -> None:
    """装饰键值必须为 6 位 hex——格式先于解析。

    _hex_to_rgb 对 8 位 hex 会静默丢弃 alpha（断言全过但 Qt 渲染不同），
    rgba() 值则直接崩溃；先显式断言格式，颜色计算才有意义。
    """
    import re

    for theme in theme_mod.THEMES:
        palette = theme_mod.THEMES[theme]
        for key in DECORATIVE_KEYS:
            assert re.fullmatch(r"#[0-9A-Fa-f]{6}", palette[key]), (
                f"{theme}/{key} 非 6 位 hex：{palette[key]!r}"
            )


# ── 装饰 ≠ 语义：与涨跌色分离 ─────────────────────────────


def test_decorative_differs_from_semantic_colors() -> None:
    """双主题下装饰键值 ≠ FG_POS/FG_NEG，且 HSL 亮度差 ≥ 0.05。

    现状缺陷：dark 下 CHART_SERIES_2/3 与 FG_POS/FG_NEG 完全同值
    （5 级包标签=亏色、3 级包标签=涨色）——本测试必须首先为红。
    """
    for theme in theme_mod.THEMES:
        palette = theme_mod.THEMES[theme]
        for key in DECORATIVE_KEYS:
            value = palette[key]
            assert value != palette["FG_POS"], f"{theme}/{key} 与涨色同值"
            assert value != palette["FG_NEG"], f"{theme}/{key} 与跌色同值"
            for semantic_key in ("FG_POS", "FG_NEG"):
                d_l = abs(_hls(value)[1] - _hls(palette[semantic_key])[1])
                assert d_l >= DELTA_L_MIN, (
                    f"{theme}/{key} 与 {semantic_key} 亮度差 {d_l:.3f} < {DELTA_L_MIN}"
                )


# ── 明度带量化：统一明度/饱和度带 ─────────────────────────


def test_decorative_lightness_band() -> None:
    """7 装饰色 HSL 亮度落统一区间（light 深墨带 / dark 亮彩带），宽度 ≤ 0.10。

    现状缺陷：light L∈[0.498,0.773] 宽度 0.275（#C08A3E 暗 vs #A58BFF 亮，混排显脏）。
    """
    bands = {"light": LIGHT_BAND, "dark": DARK_BAND}
    for theme, (lo, hi) in bands.items():
        palette = theme_mod.THEMES[theme]
        lightness = [_hls(palette[key])[1] for key in DECORATIVE_KEYS]
        assert all(lo <= l <= hi for l in lightness), (
            f"{theme} 装饰色亮度越界：{[round(l, 3) for l in lightness]} 应∈[{lo},{hi}]"
        )
        width = max(lightness) - min(lightness)
        assert width <= BAND_WIDTH_MAX, f"{theme} 明度带过宽：{width:.3f}"


def test_decorative_saturation_floor() -> None:
    """7 装饰色饱和度 ≥ 0.55（低于则发灰、失去游戏感多色）。"""
    for theme in theme_mod.THEMES:
        palette = theme_mod.THEMES[theme]
        for key in DECORATIVE_KEYS:
            saturation = _hls(palette[key])[2]
            assert saturation >= SATURATION_MIN, (
                f"{theme}/{key} 饱和度 {saturation:.2f} < {SATURATION_MIN}"
            )


# ── 两两可分辨：同主题内色差下限 ──────────────────────────


def test_decorative_pairwise_distinguishable() -> None:
    """同主题内 7 装饰色两两 ΔE76 ≥ 25。

    防明度统一后 #7B8CFF/#A58BFF 类色相过近更难分（色相轴不够用，亮度差兜底）。
    """
    for theme in theme_mod.THEMES:
        palette = theme_mod.THEMES[theme]
        values = [palette[key] for key in DECORATIVE_KEYS]
        for i, a in enumerate(values):
            for b in values[i + 1 :]:
                d = _delta_e76(a, b)
                assert d >= DELTA_E_MIN, f"{theme} 色差不足：{a} vs {b} ΔE76={d:.1f}"


# ── 可读性底线：标签文字 AA 4.5:1 ─────────────────────────


def test_decorative_label_contrast_against_card() -> None:
    """装饰色（包标签文字）对 CARD_BG 对比度 ≥ 4.5:1（浅底深字，WCAG AA）。"""
    for theme in theme_mod.THEMES:
        palette = theme_mod.THEMES[theme]
        card_bg = palette["CARD_BG"]
        for key in DECORATIVE_KEYS:
            ratio = _contrast_ratio(palette[key], card_bg)
            assert ratio >= CONTRAST_MIN, (
                f"{theme}/{key} 标签文字对比度 {ratio:.2f}:1 < {CONTRAST_MIN}:1"
            )


# ── 评审修复：主题切换后包标签色重解析 ────────────────────


def test_exchange_apply_theme_reresolves_labels(qapp, theme_guard) -> None:
    """apply_theme() 用当前主题 PACKAGE_COLOR_* 重绘 7 个包标签。

    评审发现：包标签色在 _build_body 构建期解析冻结（无 apply_theme），
    亮暗色板分离后亮→暗切换残留 light 深墨色于 dark 卡面（对比度跌破 AA）。
    """
    from app.exchange_page import ExchangePage, _PACKAGE_CONFIG

    page = ExchangePage()
    for theme in theme_mod.THEMES:
        theme_mod.set_theme(theme)
        page.apply_theme()
        for i, cfg in enumerate(_PACKAGE_CONFIG):
            assert theme_mod.get_color(cfg.color) in page._cards[i]._pkg_label.styleSheet(), (
                f"{theme} 下 apply_theme 后第 {i} 卡标签未用当前主题色"
            )


def test_exchange_apply_theme_updates_separator(qapp, theme_guard) -> None:
    """apply_theme() 用当前主题 SEPARATOR 色刷新卡片分隔线。

    Z-01（U-03 遗留）：分隔线同为构建期内联样式，主题切换后残留构建时色
    ——SEPARATOR 双主题值不同（light #d6d3cc / dark rgba(255,255,255,.06)），
    亮→暗切换后暗面残留浅色线，直到窗口重建。
    """
    from app.exchange_page import ExchangePage

    page = ExchangePage()
    for theme in theme_mod.THEMES:
        theme_mod.set_theme(theme)
        page.apply_theme()
        for i, card in enumerate(page._cards):
            assert theme_mod.get_color("SEPARATOR") in card._sep.styleSheet(), (
                f"{theme} 下 apply_theme 后第 {i} 卡分隔线未用当前主题色"
            )

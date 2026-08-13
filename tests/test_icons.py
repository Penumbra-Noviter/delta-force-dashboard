"""SVG 图标模块（app/icons.py）测试（IC-01，ADR-0006）。

契约面：ICONS 键集稳定（防误删/新增未同步）、每键渲染有效（SVG 可解析、
非空像素）、颜色注入生效（主题色 → 像素）、尺寸/未知键行为、模板占位符
无残留（Falsify：format 漏替换会留下字面 {color} 或渲染黑块）。
"""

from __future__ import annotations

from app.icons import ICONS, render_icon

# 键集守卫：新增图标键必须在此显式登记（防散落与误删）
_ICON_KEYS = [
    "key",
    "ledger",
    "moon",
    "pin",
    "plus",
    "refresh",
    "save",
    "sun",
    "wrench",
]


def _dominant_color(icon, size: int):
    """取图标像素中 alpha 最高的颜色（抗锯齿下即主体填充色）。"""
    img = icon.pixmap(size, size).toImage()
    best = None
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 0 and (best is None or c.alpha() > best.alpha()):
                best = c
    assert best is not None, "图标渲染结果全透明（SVG 无效或模板漏替换）"
    return best


def _assert_close_to(rgb, expected, tol: int = 3):
    """RGB 通道近似断言（细线图标的抗锯齿边缘允许 ±tol 偏差）。"""
    for actual, want in zip(rgb, expected):
        assert abs(actual - want) <= tol, f"{rgb} 与 {expected} 偏差超 {tol}"


def test_icon_keys_stable(qapp):
    """ICONS 键集与登记表一致（新增/删除须同步本测试）。"""
    assert sorted(ICONS) == _ICON_KEYS


def test_render_valid_for_all_keys(qapp):
    """每键可渲染：逻辑尺寸 16×16、非全透明、含主题色像素。

    deviceIndependentSize 断言逻辑口径——QIcon.pixmap 返回尺寸随屏幕 DPR
    缩放（DPR-2 屏为 32×32@DPR2），直接断言 width 会在高 DPR 屏失败
    （code-review 发现，IC 批次评审）。
    """
    for name in _ICON_KEYS:
        icon = render_icon(name, "#3c4a43")
        pm = icon.pixmap(16, 16)
        size = pm.deviceIndependentSize()
        assert size.width() == 16 and size.height() == 16
        _assert_close_to(_dominant_color(icon, 16).getRgb()[:3],
                         (0x3C, 0x4A, 0x43), tol=6), name


def test_render_color_injected(qapp):
    """颜色注入生效：不同主题色渲染出不同像素（Falsify：漏注入会恒黑）。"""
    _assert_close_to(_dominant_color(render_icon("save", "#ff0000"), 16)
                     .getRgb()[:3], (255, 0, 0))
    _assert_close_to(_dominant_color(render_icon("save", "#00ff00"), 16)
                     .getRgb()[:3], (0, 255, 0))


def test_render_size_respected(qapp):
    """size 参数生效：逻辑尺寸=size、物理像素=size×DPR（任意屏幕 DPR 成立）。

    QIcon.pixmap 返回的 pixmap 已按屏幕 DPR 缩放（DPR-1 → size×1、DPR-2 →
    size×2），故逻辑口径用 deviceIndependentSize、物理口径用 DPR 推导——
    修复 code-review 发现：原断言 width==24 在 DPR-2 屏（实际 48）会失败。
    """
    icon = render_icon("plus", "#000000", size=24)
    pm = icon.pixmap(24, 24)
    size = pm.deviceIndependentSize()
    assert size.width() == 24 and size.height() == 24
    assert pm.width() == int(24 * pm.devicePixelRatio())


def test_render_unknown_key_raises(qapp):
    """未知图标名 → KeyError（快速失败，消息含键名）。"""
    import pytest

    with pytest.raises(KeyError, match="unknown_icon"):
        render_icon("unknown_icon", "#000000")


def test_svg_templates_no_placeholder_leftover(qapp):
    """模板 {color} 占位符全部可替换（Falsify：漏 format 留字面占位符）。"""
    for name, template in ICONS.items():
        assert "{color}" in template, f"{name} 模板缺 {color} 占位符"
        rendered = template.format(color="#123456")
        assert "{color}" not in rendered, f"{name} format 后残留占位符"

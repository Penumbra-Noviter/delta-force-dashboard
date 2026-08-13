"""
SVG 矢量图标模块（ADR-0006，IC-01）：内嵌单色 SVG 模板 + QIcon 渲染。

替代 U-05 的 emoji 装饰图标：颜色由调用方按当前主题注入（模块内零
get_color 调用，遵守 C1「禁止 import 期调 get_color」铁律），HiDPI
通过 2x 渲染 + devicePixelRatio 实现。

图标数据为 24×24 viewBox 单色填充路径（Material Design Icons 系，
Apache 2.0 / MIT 许可族），风格统一；更换风格只需替换 ICONS 表数据，
调用方零改动。
"""

from __future__ import annotations

__all__ = ["ICONS", "render_icon"]

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# 图标名 → SVG 模板（{color} 占位注入当前主题色）
ICONS: dict[str, str] = {
    "ledger": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12'
        'c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/>'
        "</svg>"
    ),
    "wrench": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9'
        '-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1'
        'c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3'
        'c.5-.4.5-1.1.1-1.4z"/>'
        "</svg>"
    ),
    "key": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 '
        '2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65z'
        'M7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>'
        "</svg>"
    ),
    "plus": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>'
        "</svg>"
    ),
    "pin": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M16 9V4l1-1V2H7v1l1 1v5c0 1.66-1.34 3-3 3v2'
        'h5.97v7l1 1 1-1v-7H19v-2c-1.66 0-3-1.34-3-3z"/>'
        "</svg>"
    ),
    "moon": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M9.37 5.51c-.18.64-.27 1.31-.27 1.99 0 '
        '4.08 3.32 7.4 7.4 7.4.68 0 1.35-.09 1.99-.27C17.45 17.19 14.93 '
        '19 12 19c-3.86 0-7-3.14-7-7 0-2.93 1.81-5.45 4.37-6.49zM12 3'
        'c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36'
        '-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 '
        '0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"/>'
        "</svg>"
    ),
    "sun": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 '
        '5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 '
        '.45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 '
        '.45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1'
        '-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1'
        '-1s-1 .45-1 1zM5.99 4.58c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 '
        '0 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 '
        '4.58zm12.37 12.37c-.39-.39-1.03-.39-1.41 0-.39.39-.39 1.03 0 '
        '1.41l1.06 1.06c.39.39 1.03.39 1.41 0 .39-.39.39-1.03 0-1.41l-1.06'
        '-1.06zm1.06-10.96c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 '
        '0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM7.05'
        ' 18.36c.39-.39.39-1.03 0-1.41-.39-.39-1.03-.39-1.41 0l-1.06 1.06'
        'c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z"/>'
        "</svg>"
    ),
    "refresh": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0'
        '-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08'
        'c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69'
        ' 4.22 1.78L13 11h7V4l-2.35 2.35z"/>'
        "</svg>"
    ),
    "save": (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
        '<path fill="{color}" d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14'
        'c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 '
        '3 3-1.34 3-3 3zm3-10H5V5h10v4z"/>'
        "</svg>"
    ),
}

# 渲染 DPR（HiDPI：2x 物理像素 + devicePixelRatio 缩放）
_RENDER_DPR = 2.0


def render_icon(name: str, color: str, size: int = 16) -> QIcon:
    """按当前主题色渲染命名图标为 QIcon。

    调用方负责传入主题色（运行期 ``get_color`` 解析）；本模块零
    ``get_color`` 调用（C1 铁律）。未知图标名 raise KeyError——图标名是
    编译期常量，未知名属程序员错误，快速失败比静默空白诚实。

    Args:
        name: ``ICONS`` 键（如 "ledger" / "refresh"）。
        color: 注入 SVG 的主题色（任意 CSS 颜色字符串，如 "#3c4a43"）。
        size: 逻辑尺寸（px）；物理像素为 size×2 并经 devicePixelRatio
            缩放，HiDPI 屏上保持清晰。

    Returns:
        可设置到 QPushButton / QAction / QListWidgetItem 的 QIcon。

    Raises:
        KeyError: ``name`` 不在 ICONS 表中。
    """
    if name not in ICONS:
        raise KeyError(
            f"未知图标: {name!r}（可用: {', '.join(sorted(ICONS))}）"
        )
    svg = ICONS[name].format(color=color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        raise ValueError(f"图标 SVG 无效: {name!r}")

    physical = int(size * _RENDER_DPR)
    pixmap = QPixmap(physical, physical)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(_RENDER_DPR)
    return QIcon(pixmap)

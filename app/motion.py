"""
反馈型动效工具（U-06）：QWidget 淡入 + 通用属性动画。

Qt Widgets 的 QSS 不支持 transition（hover 背景色无法平滑过渡——
技术约束，见 DEV_LOG U-06 取舍），因此动效集中在可动画处：
- 页面切换淡入（QGraphicsOpacityEffect + QPropertyAnimation）
- 图表曲线绘制揭示（QVariantAnimation 驱动 QGraphicsItem.setOpacity）
- 保存指示淡入

规则（product register「feedback-only motion」）：
- 只做触发后 ≤250ms 的反馈动画，无装饰性循环；
- 动画是纯视觉增强，终态即时可达——中断/关闭动画不影响功能；
- 动画对象持有引用（防 GC 提前回收），结束后移除 QGraphicsEffect
  （避免 effect 通道常驻带来的渲染开销）。
"""

from __future__ import annotations

__all__ = ["fade_in_widget"]

from typing import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


def fade_in_widget(
    widget: QWidget,
    duration_ms: int = 150,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QPropertyAnimation:
    """让 widget 从透明淡入到不透明，动画结束后移除 opacity effect。

    返回值是运行中的动画对象，调用方必须持有引用（如挂到 self 属性）
    直至动画结束，防止被 GC 回收。

    Args:
        widget: 目标控件（动画期间短暂挂 QGraphicsOpacityEffect）
        duration_ms: 淡入时长（毫秒）
        easing: 缓动曲线
    """
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)
    anim.finished.connect(lambda: widget.setGraphicsEffect(None))
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return anim


def animate_property(
    target: object,
    setter: Callable[[float], None],
    duration_ms: int = 250,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QVariantAnimation:
    """通用数值动画：0.0 → 1.0 插值，逐帧回调 setter(value)。

    用于非 QObject property 的目标（如 pyqtgraph 曲线的 QGraphicsItem
    opacity——它不是 QObject property，QPropertyAnimation 无法驱动）。

    Args:
        target: 持有返回值的宿主对象（防止动画被 GC 回收）
        setter: 每帧接收 0.0~1.0 插值的回调
        duration_ms: 动画时长
        easing: 缓动曲线
    """
    anim = QVariantAnimation(target)  # type: ignore[arg-type]
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(setter)
    anim.start()
    return anim

"""
反馈型动效工具（U-06）：QWidget 淡入 + 通用属性动画。

Qt Widgets 的 QSS 不支持 transition（hover 背景色无法平滑过渡——
技术约束，见 DEV_LOG U-06 取舍），因此动效集中在可动画处：
- 页面切换淡入（QGraphicsOpacityEffect + QPropertyAnimation）
- 图表曲线绘制揭示（QVariantAnimation 驱动 QGraphicsItem.setOpacity）
- 保存指示淡入

规则（product register「feedback-only motion」）：
- 只做触发后 ≤200ms 的反馈动画，无装饰性循环；
- 动画是纯视觉增强，终态即时可达——中断/关闭动画不影响功能；
- 动画对象持有引用（防 GC 提前回收），结束后移除 QGraphicsEffect
  （避免 effect 通道常驻带来的渲染开销）；
- 全局开关：settings 键 `animations=false` 时全部动效失效但功能完整
  （MainWindow 启动时经 set_animations_enabled 注入）。
"""

from __future__ import annotations

__all__ = [
    "animate_property",
    "animate_value",
    "animations_enabled",
    "fade_in_widget",
    "set_animations_enabled",
]

import weakref
from typing import Callable

from PySide6.QtCore import QEasingCurve, QObject, QPropertyAnimation, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

# 全局动效开关（默认开；settings `animations=false` 时关闭）
_animations_enabled = True


def set_animations_enabled(enabled: bool) -> None:
    """设置全局动效开关（MainWindow 启动时从 settings 注入）。"""
    global _animations_enabled
    _animations_enabled = enabled


def animations_enabled() -> bool:
    """当前动效开关状态。"""
    return _animations_enabled


def fade_in_widget(
    widget: QWidget,
    duration_ms: int = 150,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QPropertyAnimation | None:
    """让 widget 从透明淡入到不透明，动画结束后移除 opacity effect。

    返回运行中的动画对象（调用方持有引用防 GC）；动效关闭时直接返回
    None 且不设置 effect（终态即时可达，功能不受影响）。

    Args:
        widget: 目标控件（动画期间短暂挂 QGraphicsOpacityEffect）
        duration_ms: 淡入时长（毫秒）
        easing: 缓动曲线

    C4-债6：finished 闭包 weakref 破环 + stop 后同步清 property（对齐
    C4-债3/5 生命周期收敛定案，防 DWS 残留窗口与在途销毁崩溃路径）。
    """
    if not _animations_enabled:
        return None

    # 防竞态：同 widget 连续触发时停掉旧动画——QPropertyAnimation.stop()
    # 不发 finished，旧动画的 effect 清理回调不会误删新 effect。
    # C4-债6：stop 后同步清 property——DWS 自删不发 finished，清理 lambda
    # 不执行，property 会残留已删对象的悬空指针（读路径 use-after-free 窗口）；
    # 同步清后读路径要么 None 要么有效动画，结构性消除残留窗口。
    old = widget.property("_fade_anim")
    if isinstance(old, QPropertyAnimation):
        old.stop()
        widget.setProperty("_fade_anim", None)

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)
    # DeleteWhenStopped 自删动画后，dynamic property 里的 QObject 指针会悬空
    # （下次读取访问已删对象可能崩溃）——finished 时同步清 property。
    # C4-债6：finished 闭包以 weakref 持有 widget 破环（保持原顺序：
    # 先 setGraphicsEffect(None) 再清 property）——强闭包环在「widget 动画
    # 在途时销毁」路径与 DWS 延迟删除互踩 → access violation（C4-债5 实测
    # kpi_presenter/_shake 同款）；weakref 后闭包随动画自删一起释放，
    # 不依赖循环 GC 整链回收。
    owner = weakref.ref(widget)

    def _on_finished() -> None:
        w = owner()
        if w is not None:
            w.setGraphicsEffect(None)
            w.setProperty("_fade_anim", None)

    anim.finished.connect(_on_finished)
    anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    widget.setProperty("_fade_anim", anim)
    return anim


def animate_property(
    parent: QObject,
    setter: Callable[[float], None],
    duration_ms: int = 200,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QVariantAnimation | None:
    """通用数值动画：0.0 → 1.0 插值，逐帧回调 setter(value)。

    用于非 QObject property 的目标（如 pyqtgraph 曲线的 QGraphicsItem
    opacity——它不是 QObject property，QPropertyAnimation 无法驱动）。

    Args:
        parent: 持有动画的 QObject（防止动画被 GC 回收；调用方通常传 self）
        setter: 每帧接收 0.0~1.0 插值的回调
        duration_ms: 动画时长
        easing: 缓动曲线
    """
    if not _animations_enabled:
        setter(1.0)  # 关闭动效时直接落终态
        return None

    anim = QVariantAnimation(parent)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(setter)
    anim.start()
    return anim


def animate_value(
    parent: QObject,
    old_value: float,
    new_value: float,
    setter: Callable[[float], None],
    duration_ms: int = 300,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> QVariantAnimation | None:
    """数值插值动画：old_value → new_value 逐帧回调 setter(value)。

    用于 KPI 数字 count-up 等「数值滚动」反馈（W-01）。

    Args:
        parent: 持有动画的 QObject（防 GC，通常传 self）
        old_value: 起始数值
        new_value: 目标数值
        setter: 每帧接收插值后的 float
        duration_ms: 动画时长
        easing: 缓动曲线
    """
    if not _animations_enabled:
        setter(new_value)  # 关闭动效时直接落终态
        return None

    anim = QVariantAnimation(parent)
    anim.setDuration(duration_ms)
    anim.setStartValue(float(old_value))
    anim.setEndValue(float(new_value))
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(lambda v: setter(float(v)))
    anim.start()
    return anim

"""
反馈型动效工具（U-06 + C1 深化）：QWidget 淡入 + 抖动 + 通用属性/数值动画。

Qt Widgets 的 QSS 不支持 transition（hover 背景色无法平滑过渡——
技术约束，见 DEV_LOG U-06 取舍），因此动效集中在可动画处：
- 保存指示淡入（QGraphicsOpacityEffect + QPropertyAnimation）
- 非法输入抖动（QPropertyAnimation 关键帧位移）
- 图表曲线绘制揭示（QVariantAnimation 驱动 QGraphicsItem.setOpacity）
- KPI 磁贴 count-up（QVariantAnimation 驱动数字插值）

规则（product register「feedback-only motion」）：
- 只做触发后 ≤200ms 的反馈动画，无装饰性循环；
- 动画是纯视觉增强，终态即时可达——中断/关闭动画不影响功能；
- 全局开关：settings 键 `animations=false` 时全部动效失效但功能完整
  （MainWindow 启动时经 set_animations_enabled 注入）。

## C1 深化：动画句柄收进本模块（调用方只报目标）

历史形态（C4-债3~12）是「每个调用方各自手搓一套生命周期四件套」：
在途句柄存放在动态属性 / 字典 / 未初始化属性三种机制里，各自重复实现
weakref 破环、identity 检查、stop 后同步清句柄、DWS/deleteLater 回收。
同一族 bug（在途动画与宿主销毁并发 → access violation）因此被反复修复。

现在唯一实现在本模块：
- 注册表 `_running`：以 target 为**弱键**、动画为值，宿主销毁即自动出表；
- 工厂函数返回 ``bool``（是否真的启动），动画对象不外泄——调用方
  不持有句柄，也就不存在「句柄悬空/误清」的调用方级错误；
- 控制动词：``is_running(target)`` / ``stop(target)``（丢弃，零帧）/
  ``finish(target)``（落终帧）；工厂遇同目标在途动画默认**丢弃**旧动画；
- 动画以 target 为 Qt parent：宿主销毁时动画随 C++ 树消亡，结构性
  保证「在途动画绝不写到已销毁的宿主」；
- 关闭动效的决策点也在此：一次性反馈（fade/shake）直接跳过，数值型
  （property/value）直接落终态——调用方无需再各写一套「关了怎么办」。
"""

from __future__ import annotations

__all__ = [
    "animate_property",
    "animate_value",
    "animations_enabled",
    "fade_in_widget",
    "finish",
    "is_running",
    "set_animations_enabled",
    "shake",
    "stop",
]

import weakref
from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QObject,
    QPoint,
    QPropertyAnimation,
    QVariantAnimation,
)
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

# 全局动效开关（默认开；settings `animations=false` 时关闭）
_animations_enabled = True


@dataclass
class _Entry:
    """一条在途动画：动画对象 + 随其结束/被替换时执行的清理动作。

    ``cleanup`` 必须幂等且对已销毁宿主安全（实现里以 weakref 取宿主）。
    """

    anim: QAbstractAnimation
    cleanup: Callable[[], None] | None = None


#: 在途动画注册表：target（弱键）→ 在途条目。
#: 弱键保证宿主销毁即出表，不留 Python 侧强引用；动画本身以 target 为
#: Qt parent，随宿主 C++ 树销毁，故无需（也不能）在宿主已亡后再清理。
_running: weakref.WeakKeyDictionary[QObject, _Entry] = weakref.WeakKeyDictionary()


def set_animations_enabled(enabled: bool) -> None:
    """设置全局动效开关（MainWindow 启动时从 settings 注入）。"""
    global _animations_enabled
    _animations_enabled = enabled


def animations_enabled() -> bool:
    """当前动效开关状态。"""
    return _animations_enabled


# ── 控制动词 ────────────────────────────────────────────


def _hostable(target: object) -> bool:
    """target 能否作在途动画的宿主（可被弱引用）。

    None / 不可弱引用的对象不能进注册表——按「无宿主 = 无动画」处理，
    让调用方自己的误用（如对 None 控件 setText）在它自己的位置报错，
    而不是在此处抛一个指错方向的 TypeError。
    """
    try:
        weakref.ref(target)
    except TypeError:
        return False
    return True


def is_running(target: QObject) -> bool:
    """target 是否有在途动画。

    注册表只承载在途条目——自然结束、``stop()``、``finish()`` 都在同步
    路径上出表，因此「在表内」即等价于「在途」。
    """
    return _hostable(target) and target in _running


def stop(target: QObject) -> bool:
    """丢弃 target 的在途动画（零帧、不发 finished），返回是否停掉了。

    语义 = 「中断且不落终帧」：用于目标即将被销毁或重置（图表清空、
    账号切换归零）——落终帧只会写一个马上要被覆盖的值。
    """
    return _discard(target)


def finish(target: QObject) -> bool:
    """让 target 的在途动画落终帧并回收，返回是否处理了在途动画。

    语义 = 「优雅落终」：``setCurrentTime(duration())`` 同步触发终帧与
    finished，随后由统一的 finished 处理器出表 + 清理。用于同一目标
    马上要播新动画、需要旧动画先把终值写到位的情形。
    """
    if not _hostable(target):
        return False
    entry = _running.get(target)
    if entry is None:
        return False
    entry.anim.setCurrentTime(entry.anim.duration())
    # 兜底：极端 duration 下 finished 未触发时（C4-债9 同款病理）显式清理，
    # 保证「调用后必然出表」的契约不被时序破坏。
    if _running.get(target) is entry:
        _running.pop(target, None)
        if entry.cleanup is not None:
            entry.cleanup()
        entry.anim.deleteLater()
    return True


# ── 注册表内部实现 ──────────────────────────────────────


def _discard(target: QObject) -> bool:
    """停掉 target 在途动画并回收（零帧、不发 finished、执行 cleanup）。"""
    if not _hostable(target):
        return False
    entry = _running.pop(target, None)
    if entry is None:
        return False
    entry.anim.stop()
    if entry.cleanup is not None:
        entry.cleanup()
    entry.anim.deleteLater()
    return True


def _start(
    target: QObject,
    anim: QAbstractAnimation,
    cleanup: Callable[[], None] | None = None,
) -> bool:
    """把 anim 登记为 target 的在途动画并启动（替换旧的 = 丢弃旧的）。

    前置条件：调用方若需为本次动画预建资源（如 fade 的 opacity effect），
    必须在调用本函数**之前**先调 ``_discard(target)``——否则旧条目的
    cleanup 会作用在刚建好的新资源上（widget 的 graphicsEffect 槽只有一个）。
    本函数内的 ``_discard`` 对已清理的 target 是 no-op。

    finished 处理器三重防护（C4-债3/5/6/7 定案，现集中于此）：
    1. weakref 取宿主，宿主已亡则整段跳过（不碰已销毁对象）；
    2. identity 检查 ``cur.anim is a``，陈旧 finished 不误清新句柄；
    3. 出表 + cleanup + deleteLater 一步不落（不用 DeleteWhenStopped——
       自删后再显式 deleteLater 会对已删 wrapper 抛 RuntimeError）。
    """
    _discard(target)
    anim.setParent(target)
    entry = _Entry(anim, cleanup)
    _running[target] = entry

    owner = weakref.ref(target)

    def _on_finished(a: QAbstractAnimation = anim) -> None:
        current = owner()
        if current is None:
            return
        cur = _running.get(current)
        if cur is not None and cur.anim is a:
            _running.pop(current, None)
            if cur.cleanup is not None:
                cur.cleanup()
            a.deleteLater()

    anim.finished.connect(_on_finished)
    anim.start()
    return True


# ── 工厂 ────────────────────────────────────────────────


def fade_in_widget(
    widget: QWidget,
    duration_ms: int = 150,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> bool:
    """让 widget 从透明淡入到不透明，结束后移除 opacity effect。

    返回是否启动了动画（动效关闭时 False 且不设置 effect——终态即时可达）。
    C4-债9：duration_ms <= 0 钳制为 1（duration=0 时 start 即 Stopped、
    finished 不触发 → 在途条目残留）。
    """
    duration_ms = max(1, duration_ms)

    if not _animations_enabled or not _hostable(widget):
        return False

    # 先丢弃旧动画再建新 effect：旧条目 cleanup 会清空 widget 的 effect 槽，
    # 顺序反了会连新 effect 一起清掉（widget 只剩一个 graphicsEffect 槽）。
    _discard(widget)

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    anim = QPropertyAnimation(effect, b"opacity", widget)
    anim.setDuration(duration_ms)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)

    owner = weakref.ref(widget)

    def _cleanup() -> None:
        w = owner()
        if w is not None:
            w.setGraphicsEffect(None)

    return _start(widget, anim, _cleanup)


def shake(
    widget: QWidget,
    *,
    duration_ms: int = 150,
    offset: int = 6,
) -> bool:
    """非法输入抖动反馈（W-02）：水平平移 [-offset, +offset, -⅔·offset] 回原位。

    关键帧模式内化于此（C1）：调用方只报「抖谁」，位移幅度/时长/回位
    序列不再散落在业务控件里。返回是否启动了动画（动效关闭时 False）。
    """
    if not _animations_enabled or not _hostable(widget):
        return False

    _discard(widget)

    anim = QPropertyAnimation(widget, b"pos", widget)
    anim.setDuration(max(1, duration_ms))
    start = widget.pos()
    anim.setKeyValueAt(0.0, start)
    anim.setKeyValueAt(0.25, start + QPoint(-offset, 0))
    anim.setKeyValueAt(0.5, start + QPoint(offset, 0))
    anim.setKeyValueAt(0.75, start + QPoint(-(offset * 2) // 3, 0))
    anim.setKeyValueAt(1.0, start)
    return _start(widget, anim)


def animate_property(
    target: QObject,
    setter: Callable[[float], None],
    duration_ms: int = 200,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> bool:
    """通用数值动画：0.0 → 1.0 插值，逐帧回调 setter(value)。

    用于非 QObject property 的目标（如 pyqtgraph 曲线的 QGraphicsItem
    opacity——它不是 QObject property，QPropertyAnimation 无法驱动）。

    Args:
        target: 动画宿主（在途注册表的键，同时是动画的 Qt parent）——
            必须是被写入对象的宿主（如 chart 自身），宿主销毁即动画消亡。
        setter: 每帧接收 0.0~1.0 插值的回调。
        duration_ms: 动画时长。
        easing: 缓动曲线。

    Returns:
        是否启动了动画（动效关闭时先落终态 setter(1.0) 再返回 False）。
    """
    if not _animations_enabled or not _hostable(target):
        setter(1.0)  # 关闭动效 / 无有效宿主：直接落终态
        return False

    anim = QVariantAnimation(target)
    anim.setDuration(max(1, duration_ms))
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(setter)
    return _start(target, anim)


def animate_value(
    target: QObject,
    old_value: float,
    new_value: float,
    setter: Callable[[float], None],
    duration_ms: int = 300,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
) -> bool:
    """数值插值动画：old_value → new_value 逐帧回调 setter(value)。

    用于 KPI 数字 count-up 等「数值滚动」反馈（W-01）。

    Args:
        target: 动画宿主（在途注册表的键，同时是动画的 Qt parent）——
            应为被写入的控件（如 KPI 磁贴 label），宿主销毁即动画消亡。
        old_value: 起始数值。
        new_value: 目标数值。
        setter: 每帧接收插值后的 float。
        duration_ms: 动画时长。
        easing: 缓动曲线。

    Returns:
        是否启动了动画（动效关闭时先落终态 setter(new_value) 再返回 False）。
    """
    if not _animations_enabled or not _hostable(target):
        setter(new_value)  # 关闭动效 / 无有效宿主：直接落终态
        return False

    anim = QVariantAnimation(target)
    anim.setDuration(max(1, duration_ms))
    anim.setStartValue(float(old_value))
    anim.setEndValue(float(new_value))
    anim.setEasingCurve(easing)
    anim.valueChanged.connect(lambda v: setter(float(v)))
    return _start(target, anim)

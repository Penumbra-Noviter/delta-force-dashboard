"""C1：motion 在途动画注册表与控制动词单测。

覆盖深化后的接口契约：
- 工厂返回 ``bool``（是否真的启动），动画对象不外泄；
- 同目标在途动画替换 = 丢弃旧的（同目标单在途不变式）；
- ``finish`` 落终帧 / ``stop`` 丢弃（两种语义可观察区分）；
- 关动效 / 不可弱引用宿主 → 落终态或跳过，均返回 False；
- 注册表弱键：宿主销毁即出表，不留 Python 侧强引用；
- fade 的 opacity effect 在结束/丢弃时都被摘除（否则控件停在半透明）。
"""

from __future__ import annotations

import gc
import os
import weakref

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QAbstractAnimation, QVariantAnimation
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QFrame, QLabel, QWidget

from app import motion

__all__ = []


def _anims(widget: QWidget) -> int:
    """widget 上残留的 QVariantAnimation 子对象数。"""
    return sum(isinstance(c, QVariantAnimation) for c in widget.children())


def _running_anims(widget: QWidget) -> int:
    """widget 上处于 Running 的 QVariantAnimation 子对象数。"""
    return sum(
        isinstance(c, QVariantAnimation)
        and c.state() == QAbstractAnimation.State.Running
        for c in widget.children()
    )


# ── 工厂契约 ────────────────────────────────────────────


def test_fade_in_widget_returns_bool_and_registers(qapp):
    """fade 启动 → 返回 True + 在途在表 + effect 就位。"""
    box = QFrame()
    assert motion.fade_in_widget(box, duration_ms=50) is True
    assert motion.is_running(box)
    assert box.graphicsEffect() is not None
    motion.stop(box)
    assert not motion.is_running(box)


def test_animate_property_registers_and_finishes(qapp):
    """animate_property：在途在表 → finish 落终帧（setter 收 1.0）→ 出表。"""
    label = QLabel()
    seen: list[float] = []
    assert motion.animate_property(label, seen.append, duration_ms=200) is True
    assert motion.is_running(label)

    assert motion.finish(label) is True
    assert seen[-1] == 1.0  # 落终帧
    assert not motion.is_running(label)


def test_animate_value_registers_and_finishes(qapp):
    """animate_value：finish 落终值 + 出表。"""
    label = QLabel()
    seen: list[float] = []
    assert motion.animate_value(label, 0.0, 100.0, seen.append, duration_ms=200) is True
    assert motion.is_running(label)

    assert motion.finish(label) is True
    assert seen[-1] == 100.0
    assert not motion.is_running(label)


def test_shake_registers_and_clears_on_natural_end(qapp):
    """shake：关键帧模式内化，自然结束后出表 + 子对象回收。"""
    box = QWidget()
    assert motion.shake(box, duration_ms=30) is True
    assert motion.is_running(box)
    assert _running_anims(box) == 1

    QTest.qWait(250)
    assert not motion.is_running(box)
    assert _anims(box) == 0


# ── 替换 / 停止 / 落终语义 ──────────────────────────────


def test_replacement_discards_previous_single_inflight(qapp):
    """同目标在途再触发：丢弃旧的，同目标恒单在途（Running 动画恰一条）。"""
    label = QLabel()
    motion.animate_property(label, lambda v: None, duration_ms=500)
    assert _running_anims(label) == 1

    motion.animate_property(label, lambda v: None, duration_ms=500)
    assert motion.is_running(label)
    assert _running_anims(label) == 1  # 旧动画已丢弃，不叠加竞争写
    motion.stop(label)


def test_stop_discards_without_final_frame(qapp):
    """stop = 丢弃：不落终帧（setter 收不到 1.0），出表并回收。"""
    label = QLabel()
    seen: list[float] = []
    motion.animate_property(label, seen.append, duration_ms=500)
    QTest.qWait(50)

    assert motion.stop(label) is True
    assert not motion.is_running(label)
    assert seen[-1] != 1.0  # 未落终帧
    QTest.qWait(100)
    assert _anims(label) == 0  # 对象已回收


def test_finish_returns_false_without_inflight(qapp):
    """无在途时 finish/stop 返回 False（幂等，不抛）。"""
    label = QLabel()
    assert motion.finish(label) is False
    assert motion.stop(label) is False
    assert motion.is_running(label) is False


def test_fade_removes_effect_on_stop_and_natural_end(qapp):
    """fade 的 effect 在丢弃与自然结束两条路径都被摘除（不残留半透明控件）。"""
    box = QFrame()
    motion.fade_in_widget(box, duration_ms=500)
    assert box.graphicsEffect() is not None
    motion.stop(box)
    assert box.graphicsEffect() is None  # 丢弃也要摘 effect

    motion.fade_in_widget(box, duration_ms=30)
    QTest.qWait(250)
    assert box.graphicsEffect() is None
    assert not motion.is_running(box)


# ── 关动效 / 无宿主 ─────────────────────────────────────


def test_animations_off_lands_terminal_and_returns_false(qapp):
    """关动效：四工厂均返回 False，数值型直接落终态，不产生在途。"""
    motion.set_animations_enabled(False)
    try:
        box = QFrame()
        assert motion.fade_in_widget(box, duration_ms=50) is False
        assert box.graphicsEffect() is None  # 不挂 effect
        assert motion.shake(box) is False

        seen_prop: list[float] = []
        assert motion.animate_property(box, seen_prop.append) is False
        assert seen_prop == [1.0]

        seen_value: list[float] = []
        assert motion.animate_value(box, 10.0, 20.0, seen_value.append) is False
        assert seen_value == [20.0]

        assert not motion.is_running(box)
    finally:
        motion.set_animations_enabled(True)


def test_unhostable_target_is_no_animation(qapp):
    """None / 不可弱引用目标：控制动词返回 False，工厂落终态不建动画。"""
    assert motion.is_running(None) is False
    assert motion.stop(None) is False
    assert motion.finish(None) is False

    seen: list[float] = []
    assert motion.animate_value(None, 1.0, 2.0, seen.append) is False
    assert seen == [2.0]  # 终态仍落（让调用方自己的误用在它自己的位置报错）


def test_registry_drops_entry_when_host_destroyed(qapp):
    """注册表以宿主为弱键：宿主销毁即出表，不留 Python 侧强引用。"""
    label = QLabel()
    motion.animate_property(label, lambda v: None, duration_ms=500)
    assert motion.is_running(label)

    ref = weakref.ref(label)
    del label
    gc.collect()

    assert ref() is None  # 宿主已回收
    assert not any(
        isinstance(k, QLabel) for k in list(motion._running.keys())
    )  # 弱键已出表，无悬空/泄漏条目

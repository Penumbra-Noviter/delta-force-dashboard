"""C4 块 2：KpiPresenter 双磁贴渲染的独立单测。

覆盖三个对外出口：update（文本 + count-up 动画 + 样式全量渲染）、
apply_theme_styles（仅重算 signal 换色，不动文本/动画——C1-08 语义）、
reset（账号切换归零后直落终态，Y-05）；count-up 触发条件
（old≠new 且非 None 且 value≠「数据不足」）与重复触发替换。
"""

from __future__ import annotations

import os

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QLabel

from app.kpi_presenter import KpiPresenter
from app.theme import summary_style
from presentation import format_signed_money
from signals import RateSignal

__all__ = []


class FakeLogic:
    """按 view_n 返回预置 (count, total) 的 logic 替身（零数据、零 I/O）。"""

    def __init__(
        self,
        summary: dict[int, tuple[int, float | None]],
        cash_summary: dict[int, tuple[int, float | None]],
    ) -> None:
        self._summary = summary
        self._cash_summary = cash_summary

    def summary(self, view_n: int) -> tuple[int, float | None]:
        return self._summary[view_n]

    def cash_summary(self, view_n: int) -> tuple[int, float | None]:
        return self._cash_summary[view_n]


@pytest.fixture
def presenter(qapp) -> tuple[KpiPresenter, list[QLabel]]:
    """全新 presenter + 4 个假 labels（summary_label / summary_caption /
    cash_summary_label / cash_summary_caption）。"""
    labels = [QLabel(""), QLabel(""), QLabel(""), QLabel("")]
    return KpiPresenter(*labels), labels


def _tiles(labels: list[QLabel]) -> dict[str, QLabel]:
    """按名字取标签（summary_label / summary_caption / cash_*）。"""
    return {
        "summary_label": labels[0],
        "summary_caption": labels[1],
        "cash_summary_label": labels[2],
        "cash_summary_caption": labels[3],
    }


def test_split_kpi_text(presenter):
    """文本拆分语义：`：` 分隔 → (说明, 数值)；无分隔符整体作说明。"""
    p, _ = presenter
    assert p._split_kpi_text("最近7条总盈亏：+¥41.0M") == ("最近7条总盈亏", "+¥41.0M")
    assert p._split_kpi_text("数据不足") == ("数据不足", "")
    # 多分隔符只拆第一处（split(sep, 1) 语义）
    assert p._split_kpi_text("说明：数值：多余") == ("说明", "数值：多余")


def test_update_renders_caption_value_and_style(presenter):
    """update：双磁贴说明 + 大数字 + 信号色样式全量落地（首帧直落，无动画）。"""
    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)

    assert t["summary_caption"].text() == "最近7条总盈亏"
    assert t["cash_summary_caption"].text() == "最近7条现金总变化"
    assert t["summary_label"].text() == format_signed_money(100.0)[0]
    assert t["cash_summary_label"].text() == format_signed_money(50.0)[0]
    assert t["summary_label"].styleSheet() == summary_style(RateSignal.POSITIVE)
    assert t["cash_summary_label"].styleSheet() == summary_style(RateSignal.POSITIVE)
    assert p._countup_anim is None  # 首帧 last=None → 直落终态


def test_update_data_insufficient_direct_terminal(presenter):
    """数据不足（total None）：文本直落「数据不足」，两次更新均无动画。"""
    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (0, None)}, cash_summary={7: (0, None)})

    p.update(logic, 7)
    assert t["summary_label"].text() == "数据不足"
    assert t["summary_caption"].text() == "最近7条总盈亏"
    assert p._countup_anim is None

    p.update(logic, 7)
    assert t["summary_label"].text() == "数据不足"
    assert p._countup_anim is None


def test_countup_animates_on_value_change(presenter):
    """W-01：数值变化（100 → 200）→ count-up 动画触发，结束后落新值格式化。"""
    from PySide6.QtTest import QTest

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    assert t["summary_label"].text() == format_signed_money(100.0)[0]

    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)
    assert p._countup_anim is not None
    QTest.qWait(400)
    assert t["summary_label"].text() == format_signed_money(200.0)[0]


def test_countup_not_triggered_on_same_value(presenter):
    """数值未变 → 直接设置，不新建动画（动画对象身份不变）。"""
    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)  # 首帧直落
    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)  # 动画触发
    anim_before = p._countup_anim

    p.update(logic, 7)  # 数值未变
    assert p._countup_anim is anim_before
    assert t["summary_label"].text() == format_signed_money(200.0)[0]


def test_countup_replaces_previous_animation(presenter):
    """动画中重复触发替换旧动画（新对象，防 GC 持有）。"""
    from PySide6.QtTest import QTest

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)
    anim1 = p._countup_anim
    assert anim1 is not None

    logic._summary[7] = (2, 300.0)
    p.update(logic, 7)
    anim2 = p._countup_anim
    assert anim2 is not None and anim2 is not anim1  # 替换旧动画

    QTest.qWait(400)
    assert t["summary_label"].text() == format_signed_money(300.0)[0]


def test_countup_skipped_when_value_data_insufficient(presenter):
    """value ==「数据不足」时不触发动画（防御分支），文本直落。"""
    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)
    anim_before = p._countup_anim

    logic._summary[7] = (0, None)
    p.update(logic, 7)
    assert t["summary_label"].text() == "数据不足"
    assert p._countup_anim is anim_before  # 未替换/未新建动画


def test_apply_theme_styles_changes_color_only(presenter):
    """C1-08：apply_theme_styles 只重算 signal 换色——文本不动、不触发动画。"""
    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    text_before = t["summary_label"].text()
    assert t["summary_label"].styleSheet() == summary_style(RateSignal.POSITIVE)

    logic._summary[7] = (2, -100.0)  # 同数值绝对值，仅符号变 → 换色场景
    p.apply_theme_styles(logic, 7)

    assert t["summary_label"].styleSheet() == summary_style(RateSignal.NEGATIVE)
    assert t["summary_label"].text() == text_before  # 数值文本不受影响
    assert p._countup_anim is None  # 不触发动画

    # 随后的 update 仍正常动画（apply_theme_styles 不扰动 last 值）
    logic._summary[7] = (2, 300.0)
    p.update(logic, 7)
    assert p._countup_anim is not None


def test_view_switch_7_30_linked(presenter):
    """视图 7/30 联动：同源 recent_records(view_n)，说明与数值随视图切换。"""
    from PySide6.QtTest import QTest

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(
        summary={7: (2, 100.0), 30: (2, 300.0)},
        cash_summary={7: (2, 50.0), 30: (2, 150.0)},
    )

    p.update(logic, 7)
    assert t["summary_caption"].text() == "最近7条总盈亏"
    assert t["cash_summary_caption"].text() == "最近7条现金总变化"

    p.update(logic, 30)
    # 说明同步切换（文本落地先于动画帧）
    assert t["summary_caption"].text() == "最近30条总盈亏"
    assert t["cash_summary_caption"].text() == "最近30条现金总变化"
    QTest.qWait(400)
    assert t["summary_label"].text() == format_signed_money(300.0)[0]
    assert t["cash_summary_label"].text() == format_signed_money(150.0)[0]

    anim_before = p._countup_anim
    p.update(logic, 30)  # 同视图重复更新 → 数值未变，无新动画
    assert p._countup_anim is anim_before


def test_reset_lands_terminal_without_roll_animation(presenter):
    """Y-05 账号切换：reset() 归零 last 值并停掉在途动画，随后直落终态。"""
    from PySide6.QtTest import QTest

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)  # 在途动画（跨账号滚动风险源）
    assert p._countup_anim is not None

    p.reset()
    assert p._last_summary_total is None
    assert p._last_cash_delta is None
    assert p._countup_anim is None  # 在途动画已停

    logic._summary[7] = (2, 300.0)
    logic._cash_summary[7] = (2, 99.0)
    p.update(logic, 7)
    assert p._countup_anim is None  # 归零后首帧直落，不做跨账号滚动
    assert t["summary_label"].text() == format_signed_money(300.0)[0]
    assert t["cash_summary_label"].text() == format_signed_money(99.0)[0]
    QTest.qWait(400)  # 若误触发动画，文本会被后续帧改写——等待后仍为终态
    assert t["summary_label"].text() == format_signed_money(300.0)[0]


def test_animations_disabled_lands_terminal(presenter):
    """全局动效关闭：animate_value 直落终态，不产生动画对象。"""
    from app import motion

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    motion.set_animations_enabled(False)
    try:
        p.update(logic, 7)
        logic._summary[7] = (2, 200.0)
        p.update(logic, 7)
        assert p._countup_anim is None
        assert t["summary_label"].text() == format_signed_money(200.0)[0]
    finally:
        motion.set_animations_enabled(True)


# ── C4-债1：在途 count-up 动画 vs 直落路径的竞态（per-label 分槽）──


def test_inflight_anim_does_not_overwrite_data_insufficient(presenter):
    """在途 count-up → 数据不足直落 → 等待后「数据不足」终态不被残留帧覆盖。

    基线代码下旧动画未被 stop，其残留帧把「数据不足」改写为 +¥200.00。
    """
    from PySide6.QtTest import QTest

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)  # count-up 动画触发，未等待（在途）
    assert p._countup_anim is not None

    logic._summary[7] = (0, None)
    p.update(logic, 7)  # 数据不足直落
    assert t["summary_label"].text() == "数据不足"
    QTest.qWait(400)  # 若旧动画未停，其残留帧会改写直落文本
    assert t["summary_label"].text() == "数据不足"


def test_inflight_anim_stopped_after_direct_landing(presenter):
    """数据不足直落后，原动画对象已 Stopped 且槽引用仍指向该对象。

    基线代码下直落不改写槽引用但也不停动画——state() 仍为 Running。
    """
    from PySide6.QtCore import QAbstractAnimation

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)
    anim_before = p._countup_anim
    assert anim_before is not None

    logic._summary[7] = (0, None)
    p.update(logic, 7)  # 数据不足直落
    assert p._countup_anim is anim_before  # 旧引用保留（未置 None）
    assert anim_before.state() == QAbstractAnimation.State.Stopped  # 旧动画已停


def test_disable_animations_inflight_lands_terminal(presenter):
    """在途动画 → 动效开关关闭 → 数值变化直落终态并保持（残留帧不覆盖）。"""
    from PySide6.QtTest import QTest

    from app import motion

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    logic._summary[7] = (2, 200.0)
    p.update(logic, 7)  # count-up 在途
    assert p._countup_anim is not None

    motion.set_animations_enabled(False)
    try:
        logic._summary[7] = (2, 300.0)
        p.update(logic, 7)  # 动效关闭：animate_value 直落终态（返回 None）
        assert t["summary_label"].text() == format_signed_money(300.0)[0]
        QTest.qWait(400)
        assert t["summary_label"].text() == format_signed_money(300.0)[0]
    finally:
        motion.set_animations_enabled(True)


def test_direct_landing_one_tile_keeps_other_tile_animation(presenter):
    """per-label：单磁贴直落只停自己的在途动画，不冻结另一磁贴动画。

    双磁贴同帧先后触发动画后，cash 磁贴数据不足直落——summary 磁贴的
    在途动画（已被 cash 动画替换出槽）须继续跑完自身终态；全局 stop 或
    基线残留帧均会使本断言失败。
    """
    from PySide6.QtTest import QTest

    p, labels = presenter
    t = _tiles(labels)
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})

    p.update(logic, 7)
    logic._summary[7] = (2, 200.0)
    logic._cash_summary[7] = (2, 150.0)
    p.update(logic, 7)  # 双磁贴同帧先后触发动画（槽内为 cash 动画）

    logic._cash_summary[7] = (0, None)
    p.update(logic, 7)  # cash 磁贴数据不足直落
    assert t["cash_summary_label"].text() == "数据不足"
    QTest.qWait(400)
    # summary 动画未被跨磁贴 stop——仍达自身动画终态
    assert t["summary_label"].text() == format_signed_money(200.0)[0]
    # cash 直落终态不被自己（同目标）在途动画残留帧覆盖
    assert t["cash_summary_label"].text() == "数据不足"


# ── Falsify：使 presenter 崩溃的输入，错误信息须指明缺失成员 ──


def test_update_none_logic_raises(presenter):
    """None logic → AttributeError 指明缺失 summary 成员。"""
    p, _ = presenter
    with pytest.raises(AttributeError, match="summary"):
        p.update(None, 7)


def test_apply_theme_styles_none_logic_raises(presenter):
    """None logic → AttributeError 指明缺失 summary 成员。"""
    p, _ = presenter
    with pytest.raises(AttributeError, match="summary"):
        p.apply_theme_styles(None, 7)


def test_none_label_raises_on_update(qapp):
    """注入 None label → update 时报 AttributeError（不静默）。"""
    p = KpiPresenter(None, QLabel(), QLabel(), QLabel())
    logic = FakeLogic(summary={7: (2, 100.0)}, cash_summary={7: (2, 50.0)})
    with pytest.raises(AttributeError, match="setText"):
        p.update(logic, 7)


def test_reset_without_update_no_crash(qapp):
    """尚未渲染过的 presenter 直接 reset() 不崩溃。"""
    p = KpiPresenter(QLabel(), QLabel(), QLabel(), QLabel())
    p.reset()
    assert p._last_summary_total is None
    assert p._countup_anim is None

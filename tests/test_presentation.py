"""
Tests for presentation.py — 展示文本生成：format_* 系列纯函数。
"""

from __future__ import annotations

import pytest

from presentation import (
    format_rate,
    format_saved_indicator,
    format_signed_money,
    format_window_text,
    get_pnl_label,
)
from signals import PnLSignal, RateSignal


# ── format_rate ────────────────────────────────────────

def test_format_rate_positive():
    text, signal = format_rate(5.0)
    assert text == "+5.0%"
    assert signal == RateSignal.POSITIVE


def test_format_rate_negative():
    text, signal = format_rate(-3.2)
    assert text == "-3.2%"
    assert signal == RateSignal.NEGATIVE


def test_format_rate_zero():
    text, signal = format_rate(0.0)
    assert text == "0.0%"
    assert signal == RateSignal.NEUTRAL


def test_format_rate_none():
    text, signal = format_rate(None)
    assert text == "—"
    assert signal == RateSignal.NONE


# ── format_signed_money ────────────────────────────────

def test_format_signed_money_positive():
    text, signal = format_signed_money(300.0)
    assert text == "+¥300.00"
    assert signal == RateSignal.POSITIVE


def test_format_signed_money_negative():
    text, signal = format_signed_money(-30.0)
    assert text == "¥-30.00"
    assert signal == RateSignal.NEGATIVE


def test_format_signed_money_zero_has_no_prefix():
    """零值无 + 前缀（表格较前日列 +¥0.00 → ¥0.00，D-01）。"""
    text, signal = format_signed_money(0.0)
    assert text == "¥0.00"
    assert signal == RateSignal.NEUTRAL


def test_format_signed_money_none():
    text, signal = format_signed_money(None)
    assert text == "—"
    assert signal == RateSignal.NONE


# ── format_window_text（参数化版 #6：替代 format_summary + format_cash_summary）─

@pytest.mark.parametrize(
    ("count", "total", "label", "days", "expected_text", "expected_signal"),
    [
        # 无记录
        pytest.param(
            0, None, "总盈亏", 7,
            "最近7条总盈亏：数据不足", RateSignal.NONE,
            id="empty",
        ),
        # 仅 1 条记录（不加 + 前缀，信号 NONE）
        pytest.param(
            1, 500.0, "总盈亏", 7,
            "最近7条总盈亏：¥500.00（仅 1 条记录）", RateSignal.NONE,
            id="single_record_no_plus_prefix",
        ),
        # 正数
        pytest.param(
            2, 300.0, "总盈亏", 7,
            "最近7条总盈亏：+¥300.00", RateSignal.POSITIVE,
            id="positive",
        ),
        # 负数
        pytest.param(
            2, -30.0, "总盈亏", 7,
            "最近7条总盈亏：¥-30.00", RateSignal.NEGATIVE,
            id="negative",
        ),
        # 零
        pytest.param(
            2, 0.0, "总盈亏", 7,
            "最近7条总盈亏：¥0.00", RateSignal.NEUTRAL,
            id="zero",
        ),
        # days 参数化
        pytest.param(
            2, 300.0, "总盈亏", 30,
            "最近30条总盈亏：+¥300.00", RateSignal.POSITIVE,
            id="days_parameterized",
        ),
        # 现金总变化 label
        pytest.param(
            2, 150.0, "现金总变化", 7,
            "最近7条现金总变化：+¥150.00", RateSignal.POSITIVE,
            id="cash_label_positive",
        ),
        # 现金总变化 label + days 参数化
        pytest.param(
            2, -200.0, "现金总变化", 30,
            "最近30条现金总变化：¥-200.00", RateSignal.NEGATIVE,
            id="cash_label_negative_days",
        ),
    ],
)
def test_format_window_text(
    count: int,
    total: float | None,
    label: str,
    days: int,
    expected_text: str,
    expected_signal: RateSignal,
):
    text, signal = format_window_text(count, total, label, days)
    assert text == expected_text
    assert signal == expected_signal


# ── format_saved_indicator ─────────────────────────────

def test_format_saved_indicator_today():
    """保存今日：今日文案 + 仓库总收益。"""
    text = format_saved_indicator(
        "2026-08-02", 460900000.0, "2026-08-02", []
    )
    assert text == "✓ 今日已保存 — 仓库总收益 ¥460.9M"


def test_format_saved_indicator_historical_date():
    """编辑历史日期：短日期「已更新」文案。"""
    text = format_saved_indicator(
        "2026-07-20", 419900000.0, "2026-08-02", []
    )
    assert text == "✓ 07-20 已更新 — 仓库总收益 ¥419.9M"


def test_format_saved_indicator_with_rotation_hint():
    """触发轮转删除：追加清理提示（O-14/O-17 文案）。"""
    text = format_saved_indicator(
        "2026-08-02", 460900000.0, "2026-08-02", ["2026-07-10"]
    )
    assert text == (
        "✓ 今日已保存 — 仓库总收益 ¥460.9M"
        "（已保留最近 30 条记录，自动清理 1 条较早记录）"
    )


# ── get_pnl_label ──────────────────────────────────────

def test_pnl_label_profit():
    label, signal = get_pnl_label(400.0, 420.0)
    assert label == "盈"
    assert signal == PnLSignal.盈


def test_pnl_label_loss():
    label, signal = get_pnl_label(400.0, 380.0)
    assert label == "亏"
    assert signal == PnLSignal.亏


def test_pnl_label_no_change():
    label, signal = get_pnl_label(400.0, 400.0)
    assert label == "—"
    assert signal == PnLSignal.平


def test_pnl_label_no_prev():
    label, signal = get_pnl_label(None, 420.0)
    assert label == "—"
    assert signal == PnLSignal.无
"""
Tests for calculator.py — 业务逻辑：DayRecord、日期查询、差值计算。
"""

import pytest

from calculator import DayRecord, ProfitCalculatorLogic, RateSignal, PnL信号


# ── DayRecord ────────────────────────────────────────

def test_day_record_total():
    """total = warehouse（仓库已包含现金）。"""
    r = DayRecord(cash=1000.0, warehouse=500.0, date="2026-07-20")
    assert r.total == 500.0


def test_day_record_zero():
    r = DayRecord(cash=0.0, warehouse=0.0, date="2026-07-20")
    assert r.total == 0.0


def test_day_record_float():
    r = DayRecord(cash=100.25, warehouse=50.75, date="2026-07-20")
    assert r.total == 50.75


def test_day_record_negative():
    r = DayRecord(cash=-100.0, warehouse=200.0, date="2026-07-20")
    assert r.total == 200.0


def test_day_record_is_frozen():
    r = DayRecord(cash=100.0, warehouse=200.0, date="2026-07-20")
    with pytest.raises(Exception):
        r.cash = 999.0  # type: ignore[misc]


# ── ProfitCalculatorLogic.get_record ─────────────────

def test_get_record_found():
    data = {"2026-07-20": {"cash": 100.0, "warehouse": 200.0}}
    logic = ProfitCalculatorLogic(data)
    record = logic.get_record("2026-07-20")
    assert record is not None
    assert record.cash == 100.0
    assert record.warehouse == 200.0


def test_get_record_missing():
    logic = ProfitCalculatorLogic({})
    assert logic.get_record("2026-07-20") is None


def test_get_record_missing_cash():
    logic = ProfitCalculatorLogic({"2026-07-20": {"warehouse": 200.0}})
    assert logic.get_record("2026-07-20") is None


def test_get_record_missing_warehouse():
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0}})
    assert logic.get_record("2026-07-20") is None


def test_get_record_invalid_type():
    logic = ProfitCalculatorLogic({"2026-07-20": "not_a_dict"})
    assert logic.get_record("2026-07-20") is None


def test_get_record_bad_value():
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": "abc", "warehouse": 200.0}})
    assert logic.get_record("2026-07-20") is None


# ── ProfitCalculatorLogic.save_record ────────────────

def test_save_new_record():
    logic = ProfitCalculatorLogic({})
    record = logic.save_record("2026-07-20", 100.0, 200.0)
    assert record.cash == 100.0
    assert record.warehouse == 200.0
    assert record.total == 200.0  # total = warehouse
    assert logic.data["2026-07-20"]["cash"] == 100.0


def test_save_overwrite():
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 50.0, "warehouse": 60.0}})
    logic.save_record("2026-07-20", 999.0, 111.0)
    assert logic.data["2026-07-20"]["cash"] == 999.0


# ── ProfitCalculatorLogic.last_record_before ─────────

def test_last_record_before_found():
    data = {
        "2026-07-18": {"cash": 100.0, "warehouse": 200.0},
        "2026-07-20": {"cash": 300.0, "warehouse": 400.0},
    }
    logic = ProfitCalculatorLogic(data)
    result = logic.last_record_before("2026-07-20")
    assert result is not None
    assert result[0] == "2026-07-18"
    assert result[1].total == 200.0  # total = warehouse


def test_last_record_before_none():
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    assert logic.last_record_before("2026-07-20") is None


def test_last_record_before_skip_empty():
    data = {
        "2026-07-18": {"cash": 100.0, "warehouse": 200.0},
        "2026-07-19": {},  # 无效
        "2026-07-20": {"cash": 300.0, "warehouse": 400.0},
    }
    logic = ProfitCalculatorLogic(data)
    result = logic.last_record_before("2026-07-20")
    assert result is not None
    assert result[0] == "2026-07-18"


def test_last_record_before_invalid_date():
    logic = ProfitCalculatorLogic({})
    assert logic.last_record_before("bad-date") is None


def test_last_record_before_empty_data():
    logic = ProfitCalculatorLogic({})
    assert logic.last_record_before("2026-07-20") is None


# ── ProfitCalculatorLogic.get_weekly_records ──────────

def test_weekly_all_present():
    """7 天数据全部存在时返回完整列表。"""
    data = {}
    from datetime import datetime, timedelta
    from config import DATE_FORMAT

    today = datetime.now()
    for i in range(7):
        d = today - timedelta(days=6 - i)
        data[d.strftime(DATE_FORMAT)] = {"cash": 100.0 * (i + 1), "warehouse": 50.0 * (i + 1)}

    logic = ProfitCalculatorLogic(data)
    weekly = logic.get_weekly_records(today.strftime(DATE_FORMAT), days=7)

    assert len(weekly) == 7
    for date_str, record in weekly:
        assert record is not None
        assert record.cash > 0


def test_weekly_some_missing():
    """部分日期无数据时对应位置返回 None。"""
    data = {
        (__import__("datetime").datetime.now() - __import__("datetime").timedelta(days=0)).strftime("%Y-%m-%d"): {"cash": 100, "warehouse": 200},
    }
    logic = ProfitCalculatorLogic(data)
    from datetime import datetime

    today_str = datetime.now().strftime("%Y-%m-%d")
    weekly = logic.get_weekly_records(today_str, days=7)

    assert len(weekly) == 7
    # 只有今天有数据
    found = sum(1 for _, r in weekly if r is not None)
    assert found == 1
    # 其他应为 None
    assert weekly[-1][1] is not None  # 今天


def test_weekly_empty_data():
    """无任何数据时全部为 None。"""
    logic = ProfitCalculatorLogic({})
    weekly = logic.get_weekly_records("2026-07-20", days=7)

    assert len(weekly) == 7
    for _, record in weekly:
        assert record is None


def test_weekly_invalid_date():
    """无效日期输入返回空列表。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100, "warehouse": 200}})
    weekly = logic.get_weekly_records("bad-date", days=7)
    assert weekly == []


def test_weekly_custom_days():
    """自定义天数参数。"""
    data = {}
    from datetime import datetime, timedelta
    from config import DATE_FORMAT

    today = datetime.now()
    for i in range(3):
        d = today - timedelta(days=2 - i)
        data[d.strftime(DATE_FORMAT)] = {"cash": 100.0, "warehouse": 200.0}

    logic = ProfitCalculatorLogic(data)
    weekly = logic.get_weekly_records(today.strftime(DATE_FORMAT), days=3)

    assert len(weekly) == 3
    for _, record in weekly:
        assert record is not None


def test_weekly_sorted_order():
    """验证返回列表按日期升序排列。"""
    data = {}
    from datetime import datetime, timedelta
    from config import DATE_FORMAT

    today = datetime.now()
    for i in [0, 2, 5]:  # 非连续
        d = today - timedelta(days=i)
        data[d.strftime(DATE_FORMAT)] = {"cash": 100.0, "warehouse": 200.0}

    logic = ProfitCalculatorLogic(data)
    weekly = logic.get_weekly_records(today.strftime(DATE_FORMAT), days=7)

    dates = [d for d, _ in weekly]
    assert dates == sorted(dates)


# ── Integration-style ────────────────────────────────

def test_full_flow():
    """收益 = 仓库价值变化。"""
    logic = ProfitCalculatorLogic({})
    logic.save_record("2026-07-19", 1000.0, 500.0)
    logic.save_record("2026-07-20", 1200.0, 600.0)

    today = logic.get_record("2026-07-20")
    yesterday = logic.last_record_before("2026-07-20")

    assert today is not None
    assert yesterday is not None
    # total = warehouse
    assert today.total == 600.0
    assert yesterday[0] == "2026-07-19"
    assert yesterday[1].total == 500.0
    # 收益变化 = warehouse 变化
    assert today.warehouse - yesterday[1].warehouse == 100.0


# ── ProfitCalculatorLogic.calculate_rate ─────────────

def test_calculate_rate_normal():
    """正常收益率计算。"""
    rate = ProfitCalculatorLogic.calculate_rate(400.0, 420.0)
    assert rate is not None
    assert abs(rate - 5.0) < 0.001


def test_calculate_rate_negative():
    """负收益率。"""
    rate = ProfitCalculatorLogic.calculate_rate(400.0, 380.0)
    assert rate is not None
    assert abs(rate - (-5.0)) < 0.001


def test_calculate_rate_zero():
    """收益率 0%。"""
    rate = ProfitCalculatorLogic.calculate_rate(400.0, 400.0)
    assert rate is not None
    assert rate == 0.0


def test_calculate_rate_no_prev():
    """前值为零时返回 None。"""
    rate = ProfitCalculatorLogic.calculate_rate(0.0, 400.0)
    assert rate is None


def test_calculate_rate_large():
    """大额收益率。"""
    rate = ProfitCalculatorLogic.calculate_rate(100_000_000.0, 150_000_000.0)
    assert rate is not None
    assert abs(rate - 50.0) < 0.001


# ── ProfitCalculatorLogic.format_rate ────────────────

def test_format_rate_positive():
    text, signal = ProfitCalculatorLogic.format_rate(5.0)
    assert text == "+5.0%"
    assert signal == RateSignal.POSITIVE


def test_format_rate_negative():
    text, signal = ProfitCalculatorLogic.format_rate(-3.2)
    assert text == "-3.2%"
    assert signal == RateSignal.NEGATIVE


def test_format_rate_zero():
    text, signal = ProfitCalculatorLogic.format_rate(0.0)
    assert text == "0.0%"
    assert signal == RateSignal.NEUTRAL


def test_format_rate_none():
    text, signal = ProfitCalculatorLogic.format_rate(None)
    assert text == "—"
    assert signal == RateSignal.NONE


# ── ProfitCalculatorLogic.get_pnl_label ──────────────

def test_pnl_label_profit():
    label, signal = ProfitCalculatorLogic.get_pnl_label(400.0, 420.0)
    assert label == "盈"
    assert signal == PnL信号.盈


def test_pnl_label_loss():
    label, signal = ProfitCalculatorLogic.get_pnl_label(400.0, 380.0)
    assert label == "亏"
    assert signal == PnL信号.亏


def test_pnl_label_no_change():
    label, signal = ProfitCalculatorLogic.get_pnl_label(400.0, 400.0)
    assert label == "—"
    assert signal == PnL信号.平


def test_pnl_label_no_prev():
    label, signal = ProfitCalculatorLogic.get_pnl_label(None, 420.0)
    assert label == "—"
    assert signal == PnL信号.无

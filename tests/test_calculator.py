"""
Tests for calculator.py — 业务逻辑：DayRecord、日期查询、差值计算。
"""

import pytest

from calculator import DayRecord, ProfitCalculatorLogic


# ── DayRecord ────────────────────────────────────────

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


# ── ProfitCalculatorLogic.serialize / 加载时过滤（ADR-0001）──

def test_init_filters_invalid_entries():
    """加载时跳过损坏/非法条目，合法条目保留（ADR-0001 加载时过滤语义）。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-20": {"cash": 100.0, "warehouse": 200.0},
            "2026-07-21": "not_a_dict",
            "2026-07-22": {"warehouse": 200.0},  # 缺 cash
            "2026-07-23": {"cash": "abc", "warehouse": 200.0},
        }
    )
    assert sorted(logic.data) == ["2026-07-20"]
    assert logic.get_record("2026-07-20") is not None
    assert logic.get_record("2026-07-21") is None


def test_init_skipped_record_logs_warning(caplog):
    """加载时跳过的损坏/非法条目记录 warning，含日期（O-01：不允许静默）。"""
    with caplog.at_level("WARNING"):
        ProfitCalculatorLogic({"2026-07-21": "not_a_dict"})
    messages = [rec.message for rec in caplog.records]
    assert any(
        "跳过损坏/非法记录" in m and "2026-07-21" in m for m in messages
    )


def test_serialize_round_trip():
    """serialize 得到磁盘形态裸 dict，可回喂新 logic 重建。"""
    logic = ProfitCalculatorLogic({})
    logic.save_record("2026-07-20", 100.0, 200.0)
    raw = logic.serialize()
    assert raw == {"2026-07-20": {"cash": 100.0, "warehouse": 200.0}}
    rebuilt = ProfitCalculatorLogic(raw)
    record = rebuilt.get_record("2026-07-20")
    assert record is not None
    assert record.warehouse == 200.0


def test_serialize_returns_new_dict():
    """serialize 返回新 dict，修改它不影响内部 data（消灭别名，ADR-0001）。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    raw = logic.serialize()
    assert raw is not logic.data
    raw["2026-07-20"]["cash"] = 999.0
    record = logic.get_record("2026-07-20")
    assert record is not None
    assert record.cash == 100.0


def test_init_accepts_dayrecord_dict():
    """构造函数兼容已解析的 dict[str, DayRecord]（复用/重建路径）。"""
    record = DayRecord(cash=100.0, warehouse=200.0, date="2026-07-20")
    logic = ProfitCalculatorLogic({"2026-07-20": record})
    assert logic.get_record("2026-07-20") is record

def test_save_new_record():
    logic = ProfitCalculatorLogic({})
    record = logic.save_record("2026-07-20", 100.0, 200.0)
    assert record.cash == 100.0
    assert record.warehouse == 200.0
    assert logic.serialize()["2026-07-20"]["cash"] == 100.0


def test_save_overwrite():
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 50.0, "warehouse": 60.0}})
    logic.save_record("2026-07-20", 999.0, 111.0)
    assert logic.serialize()["2026-07-20"]["cash"] == 999.0


def test_save_rounds_cash_and_warehouse_to_two_decimals():
    """保存时现金/仓库四舍五入到 2 位小数，模型与 serialize 均为舍入值。"""
    logic = ProfitCalculatorLogic({})
    record = logic.save_record("2026-07-20", 100.126, 200.999)
    assert record.cash == 100.13
    assert record.warehouse == 201.0
    serialized = logic.serialize()["2026-07-20"]
    assert serialized["cash"] == 100.13
    assert serialized["warehouse"] == 201.0


def test_save_round_follows_bankers_rounding():
    """round 为银行家舍入：精确 2 位小数边界取偶数（0.125→0.12、0.375→0.38）。"""
    logic = ProfitCalculatorLogic({})
    record = logic.save_record("2026-07-21", 0.125, 0.375)
    assert record.cash == 0.12
    assert record.warehouse == 0.38
    assert logic.serialize()["2026-07-21"]["cash"] == 0.12
    assert logic.serialize()["2026-07-21"]["warehouse"] == 0.38


def test_save_round_matches_float_representation():
    """浮点表示语义：2.675 实际存为 2.6749…，round 后为 2.67（与 Python 行为一致）。"""
    logic = ProfitCalculatorLogic({})
    record = logic.save_record("2026-07-22", 2.675, 2.5)
    assert record.cash == 2.67
    assert record.warehouse == 2.5
    assert logic.serialize()["2026-07-22"]["cash"] == 2.67

def test_save_record_logs_warning_when_cash_exceeds_warehouse(caplog):
    """业务层不拦截异常记录（允许保留展示），仅记录 warning（O-08）。"""
    logic = ProfitCalculatorLogic({})
    with caplog.at_level("WARNING"):
        logic.save_record("2026-07-20", 200.0, 100.0)
    assert logic.serialize()["2026-07-20"]["cash"] == 200.0
    assert logic.serialize()["2026-07-20"]["warehouse"] == 100.0
    assert any("违反不变式" in rec.message for rec in caplog.records)


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
    assert result[1].warehouse == 200.0


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


# ── ProfitCalculatorLogic.recent_records ──────────

def test_recent_records_under_limit():
    """记录数不超过上限时全部返回（按日期升序）。"""
    data = {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(10, 17)}
    logic = ProfitCalculatorLogic(data)
    records = logic.recent_records()

    assert [d for d, _ in records] == [f"2026-07-{d:02d}" for d in range(10, 17)]


def test_recent_records_only_entered():
    """只返回实际录入的记录：间断录入不产生空位占位。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100, "warehouse": 200}})
    records = logic.recent_records()

    assert len(records) == 1
    assert records[0][0] == "2026-07-20"


def test_recent_records_empty():
    """无任何数据时返回空列表。"""
    logic = ProfitCalculatorLogic({})
    assert logic.recent_records() == []


def test_recent_records_caps_to_days():
    """超过上限时只返回最近 days 条（间断录入的较老记录保留在 data 但不上表）。"""
    data = {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(1, 11)}
    logic = ProfitCalculatorLogic(data)
    records = logic.recent_records()

    dates = [d for d, _ in records]
    assert len(records) == 7
    assert dates == [f"2026-07-{d:02d}" for d in range(4, 11)]


def test_recent_records_custom_days():
    """自定义天数参数。"""
    data = {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(10, 13)}
    logic = ProfitCalculatorLogic(data)
    records = logic.recent_records(days=3)

    assert [d for d, _ in records] == ["2026-07-10", "2026-07-11", "2026-07-12"]


def test_recent_records_skips_malformed():
    """无效/缺失字段的记录被跳过，且不占条数上限。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-20": {"cash": 100.0, "warehouse": 200.0},
            "2026-07-21": {"cash": "abc", "warehouse": 240.0},  # 无效
            "2026-07-22": {"cash": 120.0, "warehouse": 250.0},
        }
    )
    records = logic.recent_records()

    assert [d for d, _ in records] == ["2026-07-20", "2026-07-22"]


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
    assert today.warehouse == 600.0
    assert yesterday[0] == "2026-07-19"
    assert yesterday[1].warehouse == 500.0
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


# ── ProfitCalculatorLogic.is_cash_under_warehouse ───

def test_is_cash_under_warehouse_true():
    """现金小于仓库：不变式成立。"""
    assert ProfitCalculatorLogic.is_cash_under_warehouse(100.0, 500.0)


def test_is_cash_under_warehouse_equal_boundary():
    """现金等于仓库：不变式成立（边界，不触发警告/拦截/红框）。"""
    assert ProfitCalculatorLogic.is_cash_under_warehouse(500.0, 500.0)


def test_is_cash_under_warehouse_false():
    """现金大于仓库：不变式违反。"""
    assert not ProfitCalculatorLogic.is_cash_under_warehouse(600.0, 500.0)


# ── ProfitCalculatorLogic.delete_record ────────────

def test_delete_record_existing():
    """删除存在的记录后返回 True，数据被移除。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    assert logic.delete_record("2026-07-20") is True
    assert logic.get_record("2026-07-20") is None


def test_delete_record_missing():
    """删除不存在的记录返回 False，数据不变。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    assert logic.delete_record("2026-07-19") is False
    assert logic.get_record("2026-07-20") is not None


# ── ProfitCalculatorLogic.rotate_weekly ────────────

def test_rotate_weekly_under_limit():
    """数据不超过保留上限 30 条时不做裁剪。"""
    data = {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(10, 32)}
    logic = ProfitCalculatorLogic(data)
    assert logic.rotate_weekly() == []
    assert len(logic.data) == 22


def test_rotate_weekly_at_limit_no_trim():
    """恰好 30 条时不删（满上限不删，第 31 条才删最旧）。"""
    data = {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(1, 31)}
    logic = ProfitCalculatorLogic(data)
    assert logic.rotate_weekly() == []
    assert len(logic.data) == 30


def test_rotate_weekly_trims_oldest():
    """超过 30 条时删除最旧记录，保留最近 30 条。"""
    data = {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(1, 33)}
    logic = ProfitCalculatorLogic(data)
    deleted = logic.rotate_weekly()
    dates = sorted(logic.data.keys())
    assert len(dates) == 30
    assert "2026-07-01" not in dates
    assert "2026-07-02" not in dates
    assert "2026-07-03" in dates  # 保留下来的最旧一天
    assert "2026-07-32" in dates
    # 返回被删除的日期列表（O-14）
    assert deleted == ["2026-07-01", "2026-07-02"]


def test_rotate_weekly_logs_deletion(caplog):
    """裁剪时记录 info 日志，便于状态栏提示溯源（O-14）。"""
    data = {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(1, 33)}
    logic = ProfitCalculatorLogic(data)
    with caplog.at_level("INFO", logger="calculator"):
        logic.rotate_weekly()
    assert any("2026-07-01" in r.message for r in caplog.records)


# ── ProfitCalculatorLogic.summary ──────────────────

def test_summary_empty():
    """无记录时返回 (0, None)。"""
    logic = ProfitCalculatorLogic({})
    count, total = logic.summary()
    assert count == 0
    assert total is None


def test_summary_single_record():
    """仅一条记录时返回该条仓库值。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0, "warehouse": 500.0}})
    count, total = logic.summary()
    assert count == 1
    assert total == 500.0


def test_summary_multiple_records():
    """总盈亏 = 最新记录仓库值 − 最旧记录仓库值。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-14": {"cash": 100.0, "warehouse": 400.0},
            "2026-07-18": {"cash": 200.0, "warehouse": 700.0},
        }
    )
    count, total = logic.summary()
    assert count == 2
    assert total == 300.0


def test_summary_negative():
    """下跌时总盈亏为负。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-14": {"cash": 100.0, "warehouse": 700.0},
            "2026-07-18": {"cash": 200.0, "warehouse": 400.0},
        }
    )
    count, total = logic.summary()
    assert count == 2
    assert total == -300.0


def test_summary_zero():
    """最新与最旧仓库值相等时总盈亏为 0。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-14": {"cash": 100.0, "warehouse": 400.0},
            "2026-07-18": {"cash": 200.0, "warehouse": 400.0},
        }
    )
    count, total = logic.summary()
    assert count == 2
    assert total == 0.0


def test_summary_caps_to_recent_days():
    """超过上限时只统计最近 days 条记录（间断录入的较老记录不参与）。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-01": {"cash": 100.0, "warehouse": 100.0},
            **{f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0} for d in range(10, 18)},
        }
    )
    count, total = logic.summary()
    assert count == 7
    assert total == 0.0  # 07-11~07-17 仓库值恒为 200，07-01 不在最近 7 条内



def test_summary_days_parameterized_window():
    """J 系列：summary(days) 的窗口随参数收窄/放宽（视图 7/30 同源统计）。"""
    logic = ProfitCalculatorLogic(
        {f"2026-07-{d:02d}": {"cash": 100.0, "warehouse": 200.0 + d} for d in range(1, 31)}
    )
    count_7, _ = logic.summary(7)
    count_30, _ = logic.summary(30)
    assert count_7 == 7
    assert count_30 == 30

# ── ProfitCalculatorLogic.cash_summary ──────────────

def test_cash_summary_empty():
    """无记录时返回 (0, None)。"""
    logic = ProfitCalculatorLogic({})
    count, total = logic.cash_summary()
    assert count == 0
    assert total is None


def test_cash_summary_single_record():
    """仅一条记录时返回该条现金值。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 300.0, "warehouse": 500.0}})
    count, total = logic.cash_summary()
    assert count == 1
    assert total == 300.0


def test_cash_summary_multiple_records():
    """现金总变化 = 最新记录现金 − 最旧记录现金。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-14": {"cash": 100.0, "warehouse": 400.0},
            "2026-07-18": {"cash": 250.0, "warehouse": 700.0},
        }
    )
    count, total = logic.cash_summary()
    assert count == 2
    assert total == 150.0


def test_cash_summary_negative():
    """现金下降时总变化为负（仓库上升但现金减少）。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-14": {"cash": 300.0, "warehouse": 400.0},
            "2026-07-18": {"cash": 100.0, "warehouse": 700.0},
        }
    )
    count, total = logic.cash_summary()
    assert count == 2
    assert total == -200.0


def test_cash_summary_zero():
    """最新与最旧现金相等时总变化为 0。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-14": {"cash": 100.0, "warehouse": 400.0},
            "2026-07-18": {"cash": 100.0, "warehouse": 400.0},
        }
    )
    count, total = logic.cash_summary()
    assert count == 2
    assert total == 0.0


def test_cash_summary_caps_to_recent_days():
    """超过上限时只统计最近 days 条记录（与 summary 同窗口语义）。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-01": {"cash": 999.0, "warehouse": 999.0},
            **{f"2026-07-{d:02d}": {"cash": 100.0 + d, "warehouse": 200.0 + d} for d in range(10, 18)},
        }
    )
    count, total = logic.cash_summary()
    assert count == 7
    assert total == 6.0  # 07-11~07-17 现金 111→117（差 6），07-01 不在最近 7 条内


def test_export_csv_empty():
    """无数据时只有表头行。"""
    csv_text = ProfitCalculatorLogic({}).export_csv()
    assert csv_text == "日期,现金,仓库,较前日,收益率\n"


def test_export_csv_header():
    """表头列顺序：日期/现金/仓库/较前日/收益率。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    lines = logic.export_csv().splitlines()
    assert lines[0] == "日期,现金,仓库,较前日,收益率"


def test_export_csv_single_record():
    """仅一条记录时较前日/收益率为 "—"。"""
    logic = ProfitCalculatorLogic({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    lines = logic.export_csv().splitlines()
    assert len(lines) == 2
    assert lines[1] == "2026-07-20,¥100.00,¥200.00,—,—"


def test_export_csv_multiple_records():
    """多记录：按日期升序，较前日与收益率相对前一日计算。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-20": {"cash": 100.0, "warehouse": 200.0},
            "2026-07-21": {"cash": 150.0, "warehouse": 240.0},
            "2026-07-22": {"cash": 120.0, "warehouse": 210.0},
        }
    )
    lines = logic.export_csv().splitlines()
    assert len(lines) == 4
    assert lines[1] == "2026-07-20,¥100.00,¥200.00,—,—"
    # 较前日 = 240 - 200 = 40；收益率 = (240-200)/200*100 = 20.0% → "+20.0%"
    assert lines[2] == "2026-07-21,¥150.00,¥240.00,¥40.00,+20.0%"
    # 较前日 = 210 - 240 = -30；收益率 = -12.5% → "-12.5%"
    assert lines[3] == "2026-07-22,¥120.00,¥210.00,¥-30.00,-12.5%"


def test_export_csv_sorted_order():
    """导出按日期升序排列（输入无序时亦然）。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-22": {"cash": 120.0, "warehouse": 210.0},
            "2026-07-20": {"cash": 100.0, "warehouse": 200.0},
            "2026-07-21": {"cash": 150.0, "warehouse": 240.0},
        }
    )
    dates = [line.split(",")[0] for line in logic.export_csv().splitlines()[1:]]
    assert dates == ["2026-07-20", "2026-07-21", "2026-07-22"]


def test_export_csv_skips_malformed_records():
    """格式异常的记录被跳过，且不参与前日对比。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-20": {"cash": 100.0, "warehouse": 200.0},
            "2026-07-21": {"cash": "abc", "warehouse": 240.0},  # 无效
            "2026-07-22": {"cash": 120.0, "warehouse": 250.0},
        }
    )
    lines = logic.export_csv().splitlines()
    assert len(lines) == 3  # 表头 + 2 条有效记录
    assert lines[1] == "2026-07-20,¥100.00,¥200.00,—,—"
    # 07-22 相对 07-20：较前日 = 250 - 200 = 50；收益率 = 25.0%
    assert lines[2] == "2026-07-22,¥120.00,¥250.00,¥50.00,+25.0%"


def test_export_csv_format_money_unified():
    """金额列统一 format_money：千分位引号包裹 + 消除 float 伪影（O-11）。"""
    logic = ProfitCalculatorLogic(
        {
            "2026-07-20": {"cash": 1000.0, "warehouse": 1234.56},
            "2026-07-21": {"cash": 1000.0, "warehouse": 1234.86},
        }
    )
    lines = logic.export_csv().splitlines()
    # 含千分位逗号的字段被 csv 模块引号包裹，Excel 可正确分列
    assert lines[1] == '2026-07-20,"¥1,000.00","¥1,234.56",—,—'
    # 差值 0.30 而非 0.30000000000000004 类 float 伪影（无逗号 → 不引号）
    assert lines[2] == '2026-07-21,"¥1,000.00","¥1,234.86",¥0.30,+0.0%'

"""
Tests for formatting.py — 金额格式化与输入清洗。
"""

import pytest

from formatting import (
    format_input_value,
    format_money,
    is_valid_money_input,
    parse_money_input,
    unformat_input_value,
)


# ── format_money ──────────────────────────────────────

def test_format_money_int():
    assert format_money(1000) == "¥1,000.00"


def test_format_money_float():
    assert format_money(1234.56) == "¥1,234.56"


def test_format_money_small():
    assert format_money(0.05) == "¥0.05"


def test_format_money_zero():
    assert format_money(0) == "¥0.00"


def test_format_money_negative():
    assert format_money(-500.5) == "¥-500.50"


def test_format_money_none():
    assert format_money(None) == "—"


def test_format_money_large():
    """≥1M 显示为 K，≥100M 显示为 M。"""
    assert format_money(1_000) == "¥1,000.00"         # < 1M：普通格式
    assert format_money(999_999) == "¥999,999.00"     # < 1M
    assert format_money(1_000_000) == "¥1,000.0K"     # = 1M → K
    assert format_money(5_378_100) == "¥5,378.1K"     # 5.4M → K
    assert format_money(99_999_999) == "¥100,000.0K"  # ~100M → K（不进位到 M）
    assert format_money(100_000_000) == "¥100.0M"     # = 100M → M
    assert format_money(419_900_000) == "¥419.9M"     # 419.9M → M
    assert format_money(1_000_000_000) == "¥1,000.0M" # 1B → M
    # 负数
    assert format_money(-5_000_000) == "¥-5,000.0K"
    assert format_money(-200_000_000) == "¥-200.0M"


# ── parse_money_input ────────────────────────────────

def test_parse_plain_number():
    assert parse_money_input("1234.56") == 1234.56


def test_parse_with_comma():
    assert parse_money_input("1,234.56") == 1234.56


def test_parse_with_yuan_symbol():
    assert parse_money_input("¥1,234.56") == 1234.56


def test_parse_with_rmb_symbol():
    assert parse_money_input("￥1,234.56") == 1234.56


def test_parse_with_dollar():
    assert parse_money_input("$1,234.56") == 1234.56


def test_parse_with_spaces():
    assert parse_money_input("  1,234.56  ") == 1234.56


def test_parse_empty_string():
    assert parse_money_input("") is None


def test_parse_whitespace_only():
    assert parse_money_input("   ") is None


def test_parse_integer():
    assert parse_money_input("500") == 500.0


def test_parse_negative():
    assert parse_money_input("-100") == -100.0


def test_parse_negative_with_comma():
    assert parse_money_input("-1,234.56") == -1234.56


def test_parse_multiple_decimal_points():
    with pytest.raises(ValueError):
        parse_money_input("12.34.56")


def test_parse_multiple_minus():
    with pytest.raises(ValueError):
        parse_money_input("--100")


def test_parse_misplaced_minus():
    with pytest.raises(ValueError):
        parse_money_input("100-")


def test_parse_garbage():
    """纯文字被清洗为空字符串，返回 None。"""
    assert parse_money_input("abc") is None


# ── parse_money_input with K/M/B suffix ─────────────

def test_parse_k_uppercase():
    assert parse_money_input("1K") == 1000.0


def test_parse_k_lowercase():
    assert parse_money_input("1k") == 1000.0


def test_parse_k_decimal():
    assert parse_money_input("1.5K") == 1500.0


def test_parse_k_with_comma():
    assert parse_money_input("1,234.56K") == 1234560.0


def test_parse_m_uppercase():
    assert parse_money_input("2M") == 2_000_000.0


def test_parse_m_decimal():
    assert parse_money_input("3.2M") == 3_200_000.0


def test_parse_b_uppercase():
    assert parse_money_input("4B") == 4_000_000_000.0


def test_parse_b_decimal():
    assert parse_money_input("1.25B") == 1_250_000_000.0


def test_parse_k_with_yuan():
    assert parse_money_input("¥1.5K") == 1500.0


def test_parse_m_with_spaces():
    assert parse_money_input("  2.5M  ") == 2_500_000.0


def test_parse_k_negative():
    assert parse_money_input("-1K") == -1000.0


def test_parse_k_suffix_only():
    """纯后缀无数字，返回 None。"""
    assert parse_money_input("K") is None


# ── is_valid_money_input ─────────────────────────────

def test_valid_plain():
    assert is_valid_money_input("100") is True


def test_valid_with_comma():
    assert is_valid_money_input("1,000") is True


def test_valid_empty():
    assert is_valid_money_input("") is True


def test_valid_whitespace():
    assert is_valid_money_input("  ") is True


def test_invalid_text():
    """非空但无法解析为数字的文本应视为非法（而非被清洗为空后通过）。"""
    assert is_valid_money_input("hello") is False

def test_invalid_multiple_dots():
    assert is_valid_money_input("1.2.3") is False


def test_valid_k_suffix():
    assert is_valid_money_input("5K") is True


def test_valid_m_suffix():
    assert is_valid_money_input("10M") is True


def test_valid_b_suffix():
    assert is_valid_money_input("1B") is True


# ── format_input_value ───────────────────────────────

def test_format_input_value_plain():
    assert format_input_value(1234.56) == "¥1,234.56"


def test_format_input_value_int():
    assert format_input_value(1000) == "¥1,000.00"


# ── unformat_input_value ─────────────────────────────

def test_unformat_plain():
    assert unformat_input_value("¥1,234.56") == "1234.56"


def test_unformat_int():
    assert unformat_input_value("¥1,000.00") == "1000"


def test_unformat_empty():
    assert unformat_input_value("") == ""


def test_unformat_round_number():
    assert unformat_input_value("¥500.00") == "500"


def test_unformat_with_spaces():
    assert unformat_input_value("  ¥12,345.67  ") == "12345.67"

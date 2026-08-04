"""Tests for chart_widget.py — 纯函数。"""

from __future__ import annotations

import pytest

from app.chart_widget import adaptive_range


def test_adaptive_range_normal():
    lo, hi = adaptive_range([100, 200, 300])
    assert lo < 100
    assert hi > 300


def test_adaptive_range_single_value():
    lo, hi = adaptive_range([150])
    assert lo < 150
    assert hi > 150


def test_adaptive_range_empty():
    lo, hi = adaptive_range([])
    assert lo == 0.0
    assert hi == 1.0


def test_adaptive_range_negative_values():
    lo, hi = adaptive_range([-300, -200, -100])
    assert lo < -300
    assert hi > -100


def test_adaptive_range_identical_values():
    """rng == 0 分支：5% 边距兜底，最小值 1.0。"""
    lo, hi = adaptive_range([50, 50, 50])
    assert lo < 50
    assert hi > 50
    assert pytest.approx(hi - lo, abs=0.1) == 5.0  # 50 * 0.05 * 2
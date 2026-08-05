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

def test_chart_colors_parseable_by_pyqtgraph():
    """回归：暗色主题 CHART_GRID 曾为 rgba(255,255,255,.05)，pg.mkColor 无法解析。

    复现：pg.mkColor("rgba(255,255,255,.05)") → ValueError: Unable to convert...
    修复：改为 #RRGGBBAA 八位十六进制（#FFFFFF0D，alpha 13≈5%）。
    双主题下所有图表取色键都必须能被 pyqtgraph 解析，防止再混入 QSS-only 的 rgba()。
    """
    import pyqtgraph as pg

    from app.theme import THEMES

    chart_keys = {
        "CHART_WAREHOUSE", "CHART_CASH", "CHART_BG",
        "CHART_AXIS", "CHART_GRID",
    }
    for theme_name, palette in THEMES.items():
        for key in chart_keys:
            pg.mkColor(palette[key])  # 解析失败即抛 ValueError（原 bug）

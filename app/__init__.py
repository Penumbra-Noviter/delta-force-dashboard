"""app 包 — PySide6 UI 组件。"""

from __future__ import annotations

from app.chart_widget import adaptive_range, ChartSeries, ChartState, ChartWidget
from app.input_panel import InputPanel, MoneyLineEdit
from app.main_window import MainWindow
from app.table_widget import PnLBadge, TableWidget
from app.theme import (
    generate_qss,
    get_color,
    get_theme,
    set_theme,
    signal_color,
    summary_style,
    THEMES,
)

__all__ = [
    "adaptive_range",
    "ChartSeries",
    "ChartState",
    "ChartWidget",
    "generate_qss",
    "get_color",
    "get_theme",
    "InputPanel",
    "MainWindow",
    "MoneyLineEdit",
    "PnLBadge",
    "set_theme",
    "signal_color",
    "summary_style",
    "TableWidget",
    "THEMES",
]
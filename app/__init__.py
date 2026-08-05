"""app 包 — PySide6 UI 组件。"""

from __future__ import annotations

from app.chart_widget import adaptive_range, ChartSeries, ChartState, ChartWidget
from app.crafting_page import CraftingPage
from app.gear_page import GearPage
from app.input_panel import InputPanel, MoneyLineEdit
from kkrb_client import CraftingProduct, GearItem, GearScheme, KkrbClient, KkrbError
from app.main_window import MainWindow
from app.registry import AppWidget, WidgetRegistry
from app.sidebar import Sidebar
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
    "AppWidget",
    "ChartSeries",
    "ChartState",
    "ChartWidget",
    "CraftingPage",
    "CraftingProduct",
    "GearItem",
    "GearPage",
    "GearScheme",
    "generate_qss",
    "get_color",
    "get_theme",
    "InputPanel",
    "KkrbClient",
    "KkrbError",
    "MainWindow",
    "MoneyLineEdit",
    "PnLBadge",
    "set_theme",
    "Sidebar",
    "signal_color",
    "summary_style",
    "TableWidget",
    "THEMES",
    "WidgetRegistry",
]
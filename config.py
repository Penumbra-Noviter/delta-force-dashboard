"""
应用配置：路径、日期格式、字体、颜色、主题。
"""

import sys
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────
APP_DIR: Path = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

DATA_FILE = APP_DIR / "data.json"
BACKUP_FILE = APP_DIR / "data.json.bak"
SETTINGS_FILE = APP_DIR / "settings.json"
DATE_FORMAT = "%Y-%m-%d"

# ── 字体 ──────────────────────────────────────────────
FONT_TITLE = ("Microsoft YaHei", 18, "bold")
FONT_LABEL = ("Microsoft YaHei", 11)
FONT_INPUT = ("Microsoft YaHei", 13)
FONT_DATE = ("Microsoft YaHei", 10)
FONT_BUTTON = ("Microsoft YaHei", 12)
FONT_TABLE_HEADER = ("Microsoft YaHei", 10, "bold")
FONT_TABLE_CELL = ("Microsoft YaHei", 10)

WEEK_DAYS = 7

# ── 主题 ──────────────────────────────────────────────
THEMES = {
    "light": {
        "BG": "#ffffff",
        "FG_LABEL": "#555555",
        "FG_MUTED": "#999999",
        "FG_POS": "#27ae60",
        "FG_NEG": "#e74c3c",
        "FG_TODAY": "#2563eb",
        "BTN_BG": "#2563eb",
        "BTN_BG_HOVER": "#1d4ed8",
        "BTN_FG": "#ffffff",
        "BORDER_DEFAULT": "#d1d5db",
        "BORDER_VALID": "#27ae60",
        "BORDER_INVALID": "#e74c3c",
        "SEPARATOR": "#e5e7eb",
        "PLACEHOLDER": "#cccccc",
        "MUTED_BG": "#f3f4f6",
        "PIN_OFF_BG": "#f3f4f6",
        "PIN_ON_BG": "#2563eb",
        "CHART_CASH": "#2563eb",
        "CHART_WAREHOUSE": "#f59e0b",
        "CHART_TOTAL": "#27ae60",
        "CHART_GRID": "#e5e7eb",
        "CHART_BG": "#fafafa",
        "CHART_AXIS": "#6b7280",
        "CHART_TEXT": "#374151",
        "TABLE_TEXT": "#333333",
        "TABLE_TEXT_BOLD": "#1a1a1a",
        "TABLE_ROW_EVEN_BG": "#ffffff",
        "TABLE_ROW_ODD_BG": "#f9fafb",
        "TABLE_ROW_HOVER_BG": "#f3f4f6",
        "TABLE_HEADER_BG": "#f3f4f6",
        "TABLE_HEADER_FG": "#374151",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "#e5e7eb",
        "INPUT_BG": "#ffffff",
        "INPUT_FG": "#1a1a1a",
    },
    "dark": {
        "BG": "#1e1e2e",
        "FG_LABEL": "#cdd6f4",
        "FG_MUTED": "#6c7086",
        "FG_POS": "#a6e3a1",
        "FG_NEG": "#f38ba8",
        "FG_TODAY": "#89b4fa",
        "BTN_BG": "#89b4fa",
        "BTN_BG_HOVER": "#74c7ec",
        "BTN_FG": "#1e1e2e",
        "BORDER_DEFAULT": "#45475a",
        "BORDER_VALID": "#a6e3a1",
        "BORDER_INVALID": "#f38ba8",
        "SEPARATOR": "#313244",
        "PLACEHOLDER": "#585b70",
        "MUTED_BG": "#313244",
        "PIN_OFF_BG": "#313244",
        "PIN_ON_BG": "#89b4fa",
        "CHART_CASH": "#89b4fa",
        "CHART_WAREHOUSE": "#f9e2af",
        "CHART_TOTAL": "#a6e3a1",
        "CHART_GRID": "#45475a",
        "CHART_BG": "#181825",
        "CHART_AXIS": "#a6adc8",
        "CHART_TEXT": "#cdd6f4",
        "TABLE_TEXT": "#cdd6f4",
        "TABLE_TEXT_BOLD": "#ffffff",
        "TABLE_ROW_EVEN_BG": "#1e1e2e",
        "TABLE_ROW_ODD_BG": "#252636",
        "TABLE_ROW_HOVER_BG": "#313244",
        "TABLE_HEADER_BG": "#313244",
        "TABLE_HEADER_FG": "#cdd6f4",
        "CARD_BG": "#181825",
        "CARD_BORDER": "#45475a",
        "INPUT_BG": "#313244",
        "INPUT_FG": "#cdd6f4",
    },
}

# ── 当前主题名称（运行时由 UI 切换） ─────────────────
_current_theme = "light"


def get_theme() -> dict:
    """返回当前主题的配色字典。"""
    return THEMES[_current_theme]


def set_theme(name: str) -> None:
    """切换当前主题（"light" | "dark"）。"""
    global _current_theme
    if name in THEMES:
        _current_theme = name


def get_color(key: str) -> str:
    """获取当前主题下指定颜色值。"""
    return THEMES[_current_theme].get(key, "")

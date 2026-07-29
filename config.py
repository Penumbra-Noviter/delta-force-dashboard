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
# 护眼配色：暖纸白底 + 温润青色（teal）主色调，降低蓝光刺激
# 语义色保留绿涨红跌（国际惯例），青色主色与语义色明确区分
THEMES = {
    "light": {
        "BG": "#faf9f6",            # 暖纸白，替代纯白降低刺眼感
        "FG_LABEL": "#4a5568",       # 软石板灰，对比度 6.8:1
        "FG_MUTED": "#718096",       # slate-500，对比度 4.6:1（达 WCAG AA）
        "FG_POS": "#16a34a",         # 绿涨（green-600）
        "FG_NEG": "#dc2626",         # 红跌（red-600）
        "FG_TODAY": "#0d9488",       # 今日用主色青
        "BTN_BG": "#0d9488",         # teal-600 主色
        "BTN_BG_HOVER": "#0f766e",   # teal-700 悬停加深
        "BTN_FG": "#ffffff",
        "BORDER_DEFAULT": "#d6d3cc",  # 暖灰边框
        "BORDER_VALID": "#16a34a",
        "BORDER_INVALID": "#dc2626",
        "SEPARATOR": "#e7e5e0",      # 暖浅灰分隔线
        "PLACEHOLDER": "#9ca3af",   # gray-400，占位文字豁免 AA
        "MUTED_BG": "#f4f2ed",      # 暖静音底
        "PIN_OFF_BG": "#f4f2ed",
        "PIN_ON_BG": "#0d9488",
        "CHART_CASH": "#0d9488",     # 青色（与主色一致）
        "CHART_WAREHOUSE": "#d97706",# 琥珀金（amber-600，更沉稳）
        "CHART_TOTAL": "#16a34a",
        "CHART_GRID": "#e7e5e0",
        "CHART_BG": "#fdfcf9",       # 图表区微暖底
        "CHART_AXIS": "#6b7280",
        "CHART_TEXT": "#374151",
        "TABLE_TEXT": "#3d4453",
        "TABLE_TEXT_BOLD": "#1a202c",
        "TABLE_ROW_EVEN_BG": "#ffffff",
        "TABLE_ROW_ODD_BG": "#f6f5f1",
        "TABLE_ROW_HOVER_BG": "#f4f2ed",
        "TABLE_ROW_TODAY_BG": "#e6f7f5",  # 今日行浅青底
        "TABLE_HEADER_BG": "#f4f2ed",
        "TABLE_HEADER_FG": "#3d4453",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "#e7e5e0",
        "INPUT_BG": "#ffffff",
        "INPUT_FG": "#1a202c",
        # 操作按钮语义色
        "DANGER_BG": "#fef2f2",
        "DANGER_FG": "#dc2626",
        "DANGER_BORDER": "#fecaca",
        "DANGER_HOVER_BG": "#dc2626",
    },
    "dark": {
        "BG": "#1e1e2e",
        "FG_LABEL": "#cdd6f4",
        "FG_MUTED": "#9399b3",       # 提亮：overlay→subtext，对比度更佳
        "FG_POS": "#a6e3a1",
        "FG_NEG": "#f38ba8",
        "FG_TODAY": "#2dd4bf",       # teal-400，暗底下更亮
        "BTN_BG": "#2dd4bf",         # teal-400
        "BTN_BG_HOVER": "#14b8a6",   # teal-500
        "BTN_FG": "#1e1e2e",         # 深底亮字
        "BORDER_DEFAULT": "#45475a",
        "BORDER_VALID": "#a6e3a1",
        "BORDER_INVALID": "#f38ba8",
        "SEPARATOR": "#313244",
        "PLACEHOLDER": "#7f849c",
        "MUTED_BG": "#313244",
        "PIN_OFF_BG": "#313244",
        "PIN_ON_BG": "#2dd4bf",
        "CHART_CASH": "#2dd4bf",
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
        "TABLE_ROW_TODAY_BG": "#1a3a36",  # 今日行深青底
        "TABLE_HEADER_BG": "#313244",
        "TABLE_HEADER_FG": "#cdd6f4",
        "CARD_BG": "#181825",
        "CARD_BORDER": "#45475a",
        "INPUT_BG": "#313244",
        "INPUT_FG": "#cdd6f4",
        # 操作按钮语义色
        "DANGER_BG": "#3a2222",
        "DANGER_FG": "#f38ba8",
        "DANGER_BORDER": "#5a2a2a",
        "DANGER_HOVER_BG": "#f38ba8",
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

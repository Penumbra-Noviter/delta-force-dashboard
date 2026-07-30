"""
应用配置：路径、日期格式、字体常量。
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

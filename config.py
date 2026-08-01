"""
应用配置：路径、日期格式、数据保留天数。
"""

import sys
from pathlib import Path

# ── 路径 ──────────────────────────────────────────────

# 应用所在目录（打包版为 exe 目录，源码版为项目根）。
# O-22 起仅作为「旧数据源」供一次性迁移使用；运行态数据统一存放于 DATA_DIR。
APP_DIR: Path = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

# 统一数据目录：开发版与打包版共用，exe 任意位置/重建都不丢数据（O-22）。
DATA_DIR: Path = Path.home() / "收益计算器"

DATA_FILE = DATA_DIR / "data.json"
BACKUP_FILE = DATA_DIR / "data.json.bak"
SETTINGS_FILE = DATA_DIR / "settings.json"
LOG_FILE = DATA_DIR / "profit_calculator.log"
DATE_FORMAT = "%Y-%m-%d"

WEEK_DAYS = 7

"""
应用配置：路径、日期格式、数据保留天数。
"""

import sys
from pathlib import Path

__all__ = [
    "DATA_DIR",
    "DATA_FILE",
    "SETTINGS_FILE",
    "DATE_FORMAT",
    "RETENTION_LIMIT",
    "VIEW_DAYS",
]

# ── 路径 ──────────────────────────────────────────────

# 应用所在目录（打包版为 exe 目录，源码版为项目根）。
# O-22 起仅作为「旧数据源」供一次性迁移使用；运行态数据统一存放于 DATA_DIR。
_APP_DIR: Path = (
    Path(sys.executable).parent
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parent
)

# 统一数据目录：开发版与打包版共用，exe 任意位置/重建都不丢数据（O-22）。
DATA_DIR: Path = Path.home() / "Delta Force Dashboard"

# 更名前旧数据目录（2026-08-07 项目更名 Delta Force Dashboard）：一次性迁移源，
# main() 启动时复制（非移动）到 DATA_DIR，O-22 语义——目标已有数据则跳过、旧数据不删。
_LEGACY_DATA_DIR: Path = Path.home() / "收益计算器"

DATA_FILE = DATA_DIR / "data.json"
_BACKUP_FILE = DATA_DIR / "data.json.bak"
SETTINGS_FILE = DATA_DIR / "settings.json"
_LOG_FILE = DATA_DIR / "delta_force_dashboard.log"
DATE_FORMAT = "%Y-%m-%d"

# 视图默认窗口（沿用，启动默认 7）。与 VIEW_DAYS[0] 数值巧合但语义独立。
_WEEK_DAYS = 7

# J 系列（多视图）：保留上限与视图解耦。rotate_weekly 用此常量决定
# 「最多保留 N 条录入」；视图 7/30 切换只从存量里筛窗口（CONSENSUS §7）。
RETENTION_LIMIT = 30

# 可切换的视图窗口选项（J 系列，Consensus §7）
# 第一项是启动默认窗口，与 _WEEK_DAYS 数值巧合但语义独立；
# 第二项恰好等于 RETENTION_LIMIT，但此处是展示窗口的最大值，
# 修改 RETENTION_LIMIT 不需要同步修改此常量。
VIEW_DAYS: tuple[int, int] = (7, 30)

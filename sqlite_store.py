"""
SQLite 数据持久化层：可选后端，实现与 DataStore 相同的 load()/save() 接口。

- 表 ``records``：``date TEXT PRIMARY KEY, cash REAL, warehouse REAL``
- ``load()`` 读取全部行，返回 ``{date: {cash, warehouse}}``
- ``save()`` 使用事务：先 DELETE 全部，再 INSERT 新数据（与 JSON 全量写入语义一致）
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any

from config import SQLITE_FILE

__all__ = ["SQLiteDataStore"]

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS records (
    date TEXT PRIMARY KEY,
    cash REAL NOT NULL,
    warehouse REAL NOT NULL
)
"""


class SQLiteDataStore:
    """
    基于 SQLite 的数据存储，提供与 DataStore 相同的 load()/save() 接口。

    - 使用 ``records`` 表存储日期记录。
    - ``save()`` 使用事务实现全量替换（DELETE + INSERT），语义与 JSON 全量写入一致。
    - 自动创建数据库文件及表结构（首次使用时）。
    """

    def __init__(self, db_path: Path = SQLITE_FILE) -> None:
        self.db_path = db_path
        self._ensure_db()

    # ── 公开接口 ────────────────────────────────────────

    def load(self) -> dict[str, Any]:
        """从 SQLite 读取所有记录，返回 {date: {cash, warehouse}}"""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute("SELECT date, cash, warehouse FROM records ORDER BY date").fetchall()
        except sqlite3.Error as e:
            logger.warning("SQLite 读取失败: %s", e)
            return {}

        result: dict[str, Any] = {}
        for row in rows:
            result[row["date"]] = {
                "cash": row["cash"],
                "warehouse": row["warehouse"],
            }
        return result

    def save(self, data: dict[str, Any]) -> None:
        """将 {date: {cash, warehouse}} 写入 SQLite（全量替换）。

        使用事务：先 DELETE 全部旧数据，再 INSERT 新数据。
        若任一记录缺失 cash/warehouse 字段，跳过该条并记 warning。
        """
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute("DELETE FROM records")
                for date, record in data.items():
                    cash = record.get("cash")
                    warehouse = record.get("warehouse")
                    if cash is None or warehouse is None:
                        logger.warning(
                            "跳过无效记录 %s: 缺少 cash 或 warehouse 字段", date
                        )
                        continue
                    conn.execute(
                        "INSERT INTO records (date, cash, warehouse) VALUES (?, ?, ?)",
                        (date, cash, warehouse),
                    )
                conn.commit()
        except sqlite3.Error as e:
            logger.error("SQLite 写入失败: %s", e)
            raise

    # ── 内部方法 ────────────────────────────────────────

    def _ensure_db(self) -> None:
        """确保数据库文件所在目录存在，并创建表结构。"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute(_CREATE_TABLE_SQL)
                conn.commit()
        except sqlite3.Error as e:
            logger.warning("SQLite 数据库初始化失败: %s", e)
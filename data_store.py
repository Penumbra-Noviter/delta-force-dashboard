"""
数据持久化层：负责 JSON 数据的原子写入、备份恢复与滚动备份。
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

from config import BACKUP_FILE, DATA_FILE

__all__ = [
    "DataStore",
    "migrate_legacy_data",
]

logger = logging.getLogger(__name__)


def migrate_legacy_data(legacy_dir: Path, target_dir: Path) -> None:
    """一次性迁移旧版数据目录到统一数据目录（O-22）。

    - 目标目录已有 ``data.json`` → 视为已迁移，直接返回（新数据权威，绝不覆盖）。
    - legacy 目录无 ``data.json`` → 无需迁移，直接返回。
    - 否则创建目标目录，复制 ``data.json`` + 全部滚动备份 + ``settings.json``。
    - 采用复制而非移动：源文件保留、迁移可逆；失败仅记 warning，不中断启动。
    """
    target_data = target_dir / "data.json"
    if target_data.exists() or not (legacy_dir / "data.json").exists():
        return

    files: list[tuple[Path, Path]] = [(legacy_dir / "data.json", target_data)]
    for bak in sorted(legacy_dir.glob("data.json.bak*")):
        files.append((bak, target_dir / bak.name))
    settings = legacy_dir / "settings.json"
    if settings.exists():
        files.append((settings, target_dir / "settings.json"))

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        for src, dst in files:
            shutil.copy2(src, dst)
    except OSError as e:
        logger.warning("旧数据迁移失败（数据仍在原位置，不影响启动）: %s", e)
        return
    logger.info("已从 %s 迁移数据到 %s", legacy_dir, target_dir)


class DataStore:
    """
    基于本地 JSON 文件的数据存储。

    - 原子写入：先写 .tmp，再 os.replace 覆盖正式文件。
    - 滚动备份：保存时保留最近 N 份历史（data.json.bak.1 为最新）。
    - 损坏恢复：主文件损坏时自动从最近的可用备份恢复。
    """

    def __init__(
        self,
        data_file: Path = DATA_FILE,
        backup_file: Path = BACKUP_FILE,
        max_backups: int = 3,
    ) -> None:
        self.data_file = data_file
        self.backup_file = backup_file
        self.max_backups = max(1, max_backups)

    # ── 公开接口 ────────────────────────────────────────

    def load(self) -> dict[str, Any]:
        """加载数据；主文件损坏时尝试从备份恢复。"""
        data = self._try_load(self.data_file)
        if data is not None:
            return data

        # 从新到旧尝试滚动备份
        for index in range(self.max_backups, 0, -1):
            data = self._try_load(self._backup_path(index))
            if data is not None:
                self._atomic_write(data, self.data_file)
                return data

        # 兼容旧版单一备份文件
        data = self._try_load(self.backup_file)
        if data is not None:
            self._atomic_write(data, self.data_file)
            return data

        return {}

    def save(self, data: dict[str, Any]) -> None:
        """保存数据并维护滚动备份。"""
        self._rotate_backups()
        self._atomic_write(data, self.data_file)

    # ── 内部方法 ────────────────────────────────────────

    def _backup_path(self, index: int) -> Path:
        return Path(f"{self.backup_file}.{index}")

    def _try_load(self, path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None
        # 顶层必须为 dict（形如 {"2026-08-01": {...}}）；合法 JSON 但结构
        # 错误视为损坏，走备份恢复链，避免上层收下错误类型（O-09）
        if not isinstance(data, dict):
            return None
        return data

    def _atomic_write(self, data: dict[str, Any], target: Path) -> None:
        tmp = target.with_suffix(target.suffix + ".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp.replace(target)
        except OSError:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            raise

    def _rotate_backups(self) -> None:
        """滚动备份：bak.2->bak.3, bak.1->bak.2, 当前->bak.1，同时保留 bak。"""
        if not self.data_file.exists():
            return

        # 删除最旧备份
        oldest = self._backup_path(self.max_backups)
        oldest.unlink(missing_ok=True)

        # 依次后移
        for index in range(self.max_backups - 1, 0, -1):
            src = self._backup_path(index)
            dst = self._backup_path(index + 1)
            if src.exists():
                shutil.move(str(src), str(dst))

        # 当前文件复制为最新滚动备份与兼容备份
        newest = self._backup_path(1)
        try:
            shutil.copy2(self.data_file, newest)
            shutil.copy2(self.data_file, self.backup_file)
        except OSError as e:
            logger.warning("备份文件复制失败（不影响主流程）: %s", e)

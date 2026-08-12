"""
数据持久化层：负责 JSON 数据的原子写入、备份恢复与滚动备份。
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any, Generic, TypeVar

from config import DATA_FILE, _BACKUP_FILE as BACKUP_FILE
from json_file import atomic_write_json, try_load_json

T = TypeVar("T", bound=dict)

__all__ = [
    "DataStore",
    "MIGRATED_MARKER_NAME",
    "migrate_legacy_data",
    "log_legacy_cleanup_hint",
]

logger = logging.getLogger(__name__)

# F-02 迁移完成标记：写入目标数据目录，用于提示「旧数据源可手动清理」。
# 幂等——任何使目标目录成为权威数据源的分支都会写它；应用绝不自动删源。
MIGRATED_MARKER_NAME = ".migrated"


def migrate_legacy_data(legacy_dir: Path, target_dir: Path) -> None:
    """一次性迁移旧版数据目录到统一数据目录（O-22）。

    - 目标目录已有 ``data.json`` → 视为已迁移，补写 ``.migrated`` 标记后返回（新数据权威，绝不覆盖）。
    - legacy 目录无 ``data.json`` → 无需迁移，直接返回（不写标记）。
    - 否则创建目标目录，复制 ``data.json`` + 全部滚动备份 + ``settings.json``，成功后写 ``.migrated`` 标记。
    - 采用复制而非移动：源文件保留、迁移可逆；失败仅记 warning，不中断启动。
    - 完成标记（F-02）：任何「目标目录已是权威数据源」的分支都写标记，用于配合
      :func:`log_legacy_cleanup_hint` 提示源清理；脚本绝不自动删源，删除是用户确认后的手动动作。

    注：与 :meth:`account_store.AccountStore.migrate_legacy_to_default` 是两套刻意
    独立的迁移——触发条件（本函数以目标 data.json 存在为已迁移，后者以 accounts/
    目录存在即不迁移）、完成标记（.migrated vs .migrated_v2）、失败语义（本函数仅
    warning 不清理，后者清理半成品以恢复重试触发条件）三处不同，不合并且；
    改动任一侧时需同步审视另一侧。
    """
    target_data = target_dir / "data.json"
    if target_data.exists():
        _write_migrated_marker(target_dir)
        return
    if not (legacy_dir / "data.json").exists():
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
    _write_migrated_marker(target_dir)
    logger.info("已从 %s 迁移数据到 %s", legacy_dir, target_dir)


def _write_migrated_marker(target_dir: Path) -> None:
    """写 ``.migrated`` 完成标记（F-02）。幂等；失败仅记 warning，不影响主流程。"""
    try:
        marker = target_dir / MIGRATED_MARKER_NAME
        marker.write_text(
            "数据已统一至本目录。确认数据健康后，旧数据源可由用户手动清理；"
            "应用不会自动删除。\n",
            encoding="utf-8",
        )
    except OSError as e:
        logger.warning("迁移完成标记写入失败: %s", e)


def log_legacy_cleanup_hint(legacy_dir: Path, target_dir: Path) -> None:
    """迁移完成后，若旧数据源仍残留，提示用户可手动清理（F-02）。

    判定条件：``.migrated`` 标记存在（迁移已完成）且 ``legacy_dir/data.json`` 仍在。
    仅打 info 日志、绝不删除任何文件——源清理必须是用户确认后的手动动作。
    """
    if not (target_dir / MIGRATED_MARKER_NAME).exists():
        return
    if not (legacy_dir / "data.json").exists():
        return
    logger.info(
        "旧数据源可手动清理：%s（数据已迁移至 %s，确认健康后由用户手动删除，应用不自动删源）",
        legacy_dir,
        target_dir,
    )


class DataStore(Generic[T]):
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

    def load(self) -> T:
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

    def save(self, data: T) -> None:
        """保存数据并维护滚动备份。"""
        self._rotate_backups()
        self._atomic_write(data, self.data_file)

    # ── 内部方法 ────────────────────────────────────────

    def _backup_path(self, index: int) -> Path:
        return Path(f"{self.backup_file}.{index}")

    def _try_load(self, path: Path) -> dict[str, Any] | None:
        # 委托 json_file.try_load_json：与原子写对称，加密启用时同样能读回（C7）。
        # 不传 on_error——DataStore 保持既有静默降级语义（O-09 / 共识范围内不加告警）。
        data = try_load_json(path)
        # 顶层必须为 dict（形如 {"2026-08-01": {...}}）；合法 JSON 但结构
        # 错误视为损坏，走备份恢复链，避免上层收下错误类型（O-09）
        if not isinstance(data, dict):
            return None
        return data

    def _atomic_write(self, data: dict[str, Any], target: Path) -> None:
        """内部原子写入：委托 json_file.atomic_write_json（#3 原子写协议合一）。"""
        atomic_write_json(target, data)

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

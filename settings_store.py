"""
设置持久化：SettingsStore 基于 JSON 原子写 seam 的容错读写（D-02）。

容错语义（与 D-02 前 MainWindow._load_settings/_save_settings 行为等价）：
- 读取：文件缺失 → {}（首次运行静默）；解析失败 / 顶层非 dict → warning + {}；
- 写入：原子写失败 → warning，不抛异常（不阻断关窗 / 切换主题）。
"""

from __future__ import annotations

__all__ = ["SettingsStore"]

import logging
from pathlib import Path
from typing import Any

from config import SETTINGS_FILE
from json_file import atomic_write_json, try_load_json

logger = logging.getLogger(__name__)


class SettingsStore:
    """设置文件读写：容错读 + 原子写。

    MainWindow 只负责「编码 / 解码」（窗口状态 ↔ dict），文件 I/O 全部收敛到这里。
    """

    def __init__(self, settings_file: Path = SETTINGS_FILE) -> None:
        self.settings_file = settings_file

    def load(self) -> dict[str, Any]:
        """容错读取设置；任何异常都回退默认 {}（不抛给 UI 层）。

        文件缺失（首次运行）静默返回默认；解析/IO 失败经 on_error 回调记录
        带异常详情的 warning（D-02 前逐字文案「…（使用默认设置）: %s」）。
        """
        data = try_load_json(self.settings_file, on_error=self._on_read_error)
        if data is None:
            return {}
        if not isinstance(data, dict):
            logger.warning("设置文件顶层非 dict（使用默认设置）")
            return {}
        return data

    def _on_read_error(self, e: Exception) -> None:
        """try_load_json 解析/IO 失败回调：恢复 D-02 前的逐字告警（含异常详情）。"""
        logger.warning("设置文件读取失败（使用默认设置）: %s", e)

    def save(self, settings: dict[str, Any]) -> None:
        """原子写入设置；失败仅记录 warning，不抛出。"""
        try:
            atomic_write_json(self.settings_file, settings)
        except OSError as e:
            logger.warning("设置文件写入失败: %s", e)

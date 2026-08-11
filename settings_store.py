"""
设置持久化：SettingsStore 是设置 schema 的唯一所有者（C3-10）。

- 读取：文件缺失 → {}（首次运行静默）；解析失败 / 顶层非 dict → warning + {}；
- 写入：原子写失败 → warning，不抛异常（不阻断关窗 / 切换主题）；
- Schema：DEFAULTS / KNOWN_KEYS 公开常量；update(patch) 以
  「读当前文件原始 dict → 合并 patch（未知键保留）→ 原子写 → 返回新 dict」
  取代全量覆盖写；
- 纯函数：decode_geometry_hex / decode_legacy_geometry / encode_window_state
  为 MainWindow 提供「几何 ↔ hex 字符串 / 旧 Tkinter 格式 ↔ 四元组」编解码，
  不依赖 Qt，任何异常在函数内部消化，不向上抛出。
"""

from __future__ import annotations

__all__ = [
    "SettingsStore",
    "decode_geometry_hex",
    "decode_legacy_geometry",
    "encode_window_state",
]

import logging
import re
from pathlib import Path
from typing import Any

from config import SETTINGS_FILE
from json_file import atomic_write_json, try_load_json

logger = logging.getLogger(__name__)

# ── Schema（C3-10：设置键清单唯一来源，窗口层不得散落裸字符串）──

#: 全部已知设置的默认值（MainWindow 启动读取时以 get(key, default) 兜底）。
DEFAULTS: dict[str, Any] = {
    "geometry": "",
    "pinned": False,
    "theme": "light",
    "animations": True,
}

#: 已知键全集：DEFAULTS 全部键 + 窗口层扩展键（current_account 由 Y-03 写入）。
KNOWN_KEYS: frozenset[str] = frozenset(DEFAULTS) | {"current_account"}


class SettingsStore:
    """设置文件读写：容错读 + 原子写 + schema 合并更新。

    MainWindow 只负责「编码 / 解码」（窗口状态 ↔ dict），文件 I/O 与
    键清单收敛到这里；update() 是窗口层唯一的写入口（C3-10）。
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
        """原子写入设置；失败仅记录 warning，不抛出（update 内部复用）。"""
        try:
            atomic_write_json(self.settings_file, settings)
        except OSError as e:
            logger.warning("设置文件写入失败: %s", e)

    def update(self, patch: dict[str, Any]) -> dict[str, Any]:
        """合并 patch 原子落盘并返回新 dict（C3-10，取代全量覆盖写）。

        读当前文件原始 dict（复用 load() 容错语义：缺失 → {}、损坏 →
        {} + warning）→ 合并 patch（文件既有未知键保留；patch 内新键
        即使非 KNOWN_KEYS 也写入）→ 原子写（失败 warning 不抛）→ 返回合并结果。
        """
        current = self.load()
        current.update(patch)
        self.save(current)
        return current


# ═══════════════════════════════════════════════════════
# 编解码纯函数（候选 3：SettingsCodec）
# ═══════════════════════════════════════════════════════

_LEGACY_GEOMETRY_RE = re.compile(r"(\d+)x(\d+)([+-]\d+)([+-]\d+)")


def decode_geometry_hex(saved: str) -> bytes | None:
    """hex 新格式几何解码：合法 hex 且长度 > 4 字节 → bytes，否则 None。

    新格式为 `bytes(saveGeometry()).hex()`。Qt 合法几何至少 5 字节，
    因此长度 ≤ 4 一律视为无效；空串 / 奇数长度 / 非法字符同样返回 None。
    fromhex 异常在函数内部捕获，不向上抛出。
    """
    try:
        raw = bytes.fromhex(saved)
    except ValueError:
        return None
    if len(raw) > 4:
        return raw
    return None


def decode_legacy_geometry(saved: str) -> tuple[int, int, int, int] | None:
    """旧 Tkinter 格式几何解码："820x880+100+50" → (w, h, x, y)。

    必须含 "+"（旧代码判定门槛）；坐标可带负号
    （如 "820x880-100+50" → (820, 880, -100, 50)）。拆 4 段全为 int
    才返回，空串 / 段数不足 / 含非数字一律 None，不抛出。
    """
    if "+" not in saved:
        return None
    m = _LEGACY_GEOMETRY_RE.fullmatch(saved)
    if m is None:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))


def encode_window_state(geo_bytes: bytes, pinned: bool, theme: str) -> dict[str, Any]:
    """编码窗口状态 dict：geometry 以 hex 字符串落盘（与 decode_geometry_hex 对称）。

    AA-04 公开命名（原 _encode_window_state）：MainWindow 跨模块依赖本
    函数，真实依赖面已超出模块私有边界——公开命名并纳入 __all__ 与声明一致。
    MainWindow 只提供窗口状态字节（saveGeometry），本函数负责「状态 → dict」
    的全部编码；pinned / theme 原样透传。
    """
    return {"geometry": geo_bytes.hex(), "pinned": pinned, "theme": theme}

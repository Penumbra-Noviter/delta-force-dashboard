"""
Tests for json_file.py + settings_store.py — JSON 原子写 seam 与设置持久化（D-02）。

行为等价于 D-02 前的 MainWindow._load_settings/_save_settings：
- 读取：文件缺失 → {}（静默）；解析失败 / 顶层非 dict → warning + {}；
- 写入：原子写失败 → warning，不抛异常。
"""

from __future__ import annotations

import json
import pytest

from json_file import atomic_write_json, try_load_json
from settings_store import (
    SettingsStore,
    decode_geometry_hex,
    decode_legacy_geometry,
    encode_settings,
)


# ── json_file.atomic_write_json ────────────────────────

def test_atomic_write_creates_file(tmp_path):
    path = tmp_path / "settings.json"
    atomic_write_json(path, {"theme": "dark"})
    with open(path, "r", encoding="utf-8") as f:
        assert json.load(f) == {"theme": "dark"}


def test_atomic_write_overwrites(tmp_path):
    path = tmp_path / "settings.json"
    atomic_write_json(path, {"v": 1})
    atomic_write_json(path, {"v": 2})
    with open(path, "r", encoding="utf-8") as f:
        assert json.load(f) == {"v": 2}


def test_atomic_write_failure_raises_and_cleans_tmp(tmp_path):
    """目标目录不存在 → 抛 OSError，且不留 .tmp 残留。"""
    path = tmp_path / "missing_dir" / "settings.json"
    with pytest.raises(OSError):
        atomic_write_json(path, {"v": 1})
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_no_tmp_residue(tmp_path):
    path = tmp_path / "settings.json"
    atomic_write_json(path, {"v": 1})
    assert not list(tmp_path.glob("*.tmp"))


# ── json_file.try_load_json ────────────────────────────

def test_try_load_missing_returns_none(tmp_path):
    assert try_load_json(tmp_path / "nope.json") is None


def test_try_load_valid_returns_value(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"a": 1}', encoding="utf-8")
    assert try_load_json(path) == {"a": 1}


def test_try_load_corrupt_returns_none(tmp_path):
    path = tmp_path / "s.json"
    path.write_text("{ not json", encoding="utf-8")
    assert try_load_json(path) is None


def test_try_load_non_dict_returns_value(tmp_path):
    """顶层非 dict（如 list）也返回解析值，形状校验交由调用方。"""
    path = tmp_path / "s.json"
    path.write_text("[]", encoding="utf-8")
    assert try_load_json(path) == []


def test_try_load_corrupt_calls_on_error(tmp_path):
    """解析失败 → on_error 以实际异常为参数被调用，仍返回 None。"""
    path = tmp_path / "s.json"
    path.write_text("{ not json", encoding="utf-8")
    seen = []
    result = try_load_json(path, on_error=seen.append)
    assert result is None
    assert len(seen) == 1
    assert isinstance(seen[0], (json.JSONDecodeError, OSError))


def test_try_load_missing_does_not_call_on_error(tmp_path):
    """文件缺失是正常状态 → on_error 不被调用。"""
    seen = []
    assert try_load_json(tmp_path / "nope.json", on_error=seen.append) is None
    assert seen == []


# ── SettingsStore.load ─────────────────────────────────

def test_load_missing_returns_empty_no_warning(tmp_path, caplog):
    """首次运行（文件缺失）：静默返回 {}，不告警。"""
    store = SettingsStore(tmp_path / "settings.json")
    with caplog.at_level("WARNING"):
        assert store.load() == {}
    assert not caplog.records


def test_load_valid_returns_dict(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"theme": "dark", "pinned": true}', encoding="utf-8")
    assert SettingsStore(path).load() == {"theme": "dark", "pinned": True}


def test_load_corrupt_logs_warning(tmp_path, caplog):
    path = tmp_path / "settings.json"
    path.write_text("{ not valid json !!!", encoding="utf-8")
    with caplog.at_level("WARNING"):
        result = SettingsStore(path).load()
    assert result == {}
    assert any("设置文件读取失败" in rec.message for rec in caplog.records)


def test_load_corrupt_warning_includes_exception(tmp_path, caplog):
    """读取失败 warning 恢复 D-02 前逐字文案：带异常详情（: %s）。"""
    path = tmp_path / "settings.json"
    path.write_text("{ not valid json !!!", encoding="utf-8")
    with caplog.at_level("WARNING"):
        SettingsStore(path).load()
    messages = [rec.message for rec in caplog.records]
    assert any(
        m.startswith("设置文件读取失败（使用默认设置）:")
        and len(m) > len("设置文件读取失败（使用默认设置）:")
        for m in messages
    )


def test_load_top_level_list_returns_default(tmp_path, caplog):
    """顶层合法 JSON 但非 dict（O-09 语义）。"""
    path = tmp_path / "settings.json"
    path.write_text("[]", encoding="utf-8")
    with caplog.at_level("WARNING"):
        result = SettingsStore(path).load()
    assert result == {}
    assert any("顶层非 dict" in rec.message for rec in caplog.records)


# ── SettingsStore.save ─────────────────────────────────

def test_save_writes_file(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)
    store.save({"theme": "dark", "pinned": True, "geometry": "abc"})
    with open(path, "r", encoding="utf-8") as f:
        assert json.load(f) == {"theme": "dark", "pinned": True, "geometry": "abc"}
    assert store.load() == {"theme": "dark", "pinned": True, "geometry": "abc"}


def test_save_no_tmp_residue(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.save({"v": 1})
    assert not list(tmp_path.glob("*.tmp"))


def test_save_failure_logs_warning_no_raise(tmp_path, caplog):
    """目标目录不存在 → 不抛异常，仅记录 warning。"""
    path = tmp_path / "missing_dir" / "settings.json"
    with caplog.at_level("WARNING"):
        SettingsStore(path).save({"theme": "dark"})
    assert any("设置文件写入失败" in rec.message for rec in caplog.records)


# ── 编解码纯函数（候选 3：SettingsCodec）────────────────

def test_decode_geometry_hex_valid_returns_bytes():
    """合法 hex（偶数长度且解码后 > 4 字节）→ bytes。"""
    saved = "00ff".ljust(10, "0")  # "00ff000000" → 5 字节
    assert decode_geometry_hex(saved) == bytes.fromhex(saved)
    assert decode_geometry_hex("01" * 8) == b"\x01" * 8


def test_decode_geometry_hex_empty_returns_none():
    """空串 → None。"""
    assert decode_geometry_hex("") is None


def test_decode_geometry_hex_bad_hex_returns_none():
    """奇数长度 / 非法字符 → None（异常内部捕获，不抛出）。"""
    assert decode_geometry_hex("abc") is None     # 奇数长度
    assert decode_geometry_hex("zz") is None      # 非法字符
    assert decode_geometry_hex("00gg") is None    # 非法字符
    assert decode_geometry_hex("0x00ff") is None  # 前缀残留


def test_decode_geometry_hex_too_short_returns_none():
    """解码后 ≤ 4 字节（Qt 合法几何下限外）→ None。"""
    assert decode_geometry_hex("00ff") is None       # 2 字节
    assert decode_geometry_hex("000000") is None     # 3 字节
    assert decode_geometry_hex("00000000") is None   # 4 字节


def test_decode_legacy_geometry_positive():
    """"820x880+100+50" → (w, h, x, y)。"""
    assert decode_legacy_geometry("820x880+100+50") == (820, 880, 100, 50)


def test_decode_legacy_geometry_negative_coords():
    """负数坐标（Tkinter 允许 -x/-y）→ 解析为负值。"""
    assert decode_legacy_geometry("820x880-100+50") == (820, 880, -100, 50)


def test_decode_legacy_geometry_without_plus_returns_none():
    """无 "+" 段（旧代码判定门槛）→ None。"""
    assert decode_legacy_geometry("820x880") is None
    assert decode_legacy_geometry("820") is None
    assert decode_legacy_geometry("") is None


def test_decode_legacy_geometry_non_numeric_returns_none():
    """段含非数字 / 段数不足 → None。"""
    assert decode_legacy_geometry("820x88O+100+50") is None   # 非数字段
    assert decode_legacy_geometry("820x880+abc+50") is None   # 非数字段
    assert decode_legacy_geometry("820x880+100+50+60") is None  # 5 段


def test_encode_settings_roundtrip():
    """encode_settings → hex 还原 == 原 bytes（与 decode_geometry_hex 对称）。"""
    geo = b"\x01\x02\x03\x04\x05\x06"
    settings = encode_settings(geo, pinned=True, theme="dark")
    assert settings["geometry"] == geo.hex()
    assert bytes.fromhex(settings["geometry"]) == geo


def test_encode_settings_dict_keys():
    """dict 键值齐全：geometry / pinned / theme 原样透传。"""
    settings = encode_settings(b"\x00" * 5, pinned=False, theme="light")
    assert settings == {"geometry": "0000000000", "pinned": False, "theme": "light"}

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
from settings_store import SettingsStore


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

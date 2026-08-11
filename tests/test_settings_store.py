"""
Tests for json_file.py + settings_store.py — JSON 原子写 seam 与设置持久化（D-02）。

行为等价于 D-02 前的 MainWindow._load_settings/_save_settings：
- 读取：文件缺失 → {}（静默）；解析失败 / 顶层非 dict → warning + {}；
- 写入：原子写失败 → warning，不抛异常。
C3-10：SettingsStore 是设置 schema 唯一所有者——DEFAULTS / KNOWN_KEYS /
update(patch)（读-合并-原子写-返回）；encode_settings 降级为模块私有。
"""

from __future__ import annotations

import json
import pytest

from json_file import atomic_write_json, try_load_json
from settings_store import (
    DEFAULTS,
    KNOWN_KEYS,
    SettingsStore,
    decode_geometry_hex,
    decode_legacy_geometry,
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


def test_update_window_state_roundtrip(tmp_path):
    """update() 的 schema 往返：geometry hex 落盘 → 原子写 → 回读解码还原（对称性）。"""
    geo = b"\x01\x02\x03\x04\x05\x06"
    store = SettingsStore(tmp_path / "settings.json")
    result = store.update({"geometry": geo.hex(), "pinned": True, "theme": "dark"})
    assert result == {"geometry": geo.hex(), "pinned": True, "theme": "dark"}
    saved = store.load()
    assert saved["pinned"] is True and saved["theme"] == "dark"
    assert bytes.fromhex(saved["geometry"]) == geo


# ── C3-10. Schema 所有者（DEFAULTS / KNOWN_KEYS / update）──


def test_schema_constants_relationship():
    """KNOWN_KEYS 含 DEFAULTS 全部键 + current_account（共识值）。"""
    assert DEFAULTS == {
        "geometry": "",
        "pinned": False,
        "theme": "light",
        "animations": True,
    }
    assert set(DEFAULTS) <= set(KNOWN_KEYS)
    assert "current_account" in KNOWN_KEYS
    assert "geometry" in KNOWN_KEYS and "animations" in KNOWN_KEYS


def test_update_merges_patch_and_persists(tmp_path):
    """update 合并 patch 原子落盘并返回新 dict；文件既有未知键保留（验收 3）。"""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"custom": 1}), encoding="utf-8")
    store = SettingsStore(path)

    result = store.update({"theme": "dark"})

    assert result == {"custom": 1, "theme": "dark"}
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "custom": 1,
        "theme": "dark",
    }
    # patch 内新键即使非 KNOWN_KEYS 也应写入
    store.update({"future_key": True})
    assert json.loads(path.read_text(encoding="utf-8"))["future_key"] is True


def test_update_missing_file_starts_from_empty(tmp_path):
    """文件缺失（首次运行）→ update 从 {} 合并，仅落 patch。"""
    store = SettingsStore(tmp_path / "settings.json")
    result = store.update({"theme": "dark"})
    assert result == {"theme": "dark"}
    assert json.loads((tmp_path / "settings.json").read_text(encoding="utf-8")) == {
        "theme": "dark"
    }


def test_update_corrupt_file_falls_back_empty_with_warning(tmp_path, caplog):
    """损坏文件 → update 走 load 容错（{} + warning），仍落 patch。"""
    path = tmp_path / "settings.json"
    path.write_text("{ not json", encoding="utf-8")
    with caplog.at_level("WARNING"):
        result = SettingsStore(path).update({"theme": "dark"})
    assert result == {"theme": "dark"}
    assert any("设置文件读取失败" in r.message for r in caplog.records)
    assert json.loads(path.read_text(encoding="utf-8")) == {"theme": "dark"}


def test_update_write_failure_logs_warning_no_raise(tmp_path, caplog):
    """目录不存在 → update 写失败 warning 不抛（与 save 一致，验收 4）。"""
    store = SettingsStore(tmp_path / "missing_dir" / "settings.json")
    with caplog.at_level("WARNING"):
        result = store.update({"theme": "dark"})
    assert result == {"theme": "dark"}  # 返回合并结果，写失败不阻断
    assert any("设置文件写入失败" in r.message for r in caplog.records)


def test_encode_settings_not_public():
    """encode_settings 不再公开：不在 __all__，模块无该属性（验收 5）。"""
    import settings_store as ss

    assert "encode_settings" not in ss.__all__
    assert not hasattr(ss, "encode_settings")
    assert hasattr(ss, "_encode_window_state")  # 私有化后的名称存在


# ── C3-11. AST 守卫：main_window 设置键访问收敛到模块常量 ──


def test_main_window_has_no_bare_settings_keys():
    """C3-11 AST：main_window.py 无裸字符串设置键（读取/写入均经 _KEY_* 模块常量）。

    只扫「设置键访问」形态：.get("<键>") 调用与 ["<键>"] 下标（含赋值左值）；
    docstring/注释文字（非访问形态）不匹配。键清单与 KNOWN_KEYS 对齐。
    """
    import ast
    import inspect

    import app.main_window as mw

    setting_keys = {"geometry", "pinned", "theme", "animations", "current_account"}
    tree = ast.parse(inspect.getsource(mw))
    violations: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value in setting_keys
        ):
            violations.append(f"L{node.lineno}: .get({node.args[0].value!r})")
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in setting_keys
        ):
            violations.append(f"L{node.lineno}: [{node.slice.value!r}] 下标")
    assert violations == [], f"main_window 含裸字符串设置键：{violations}"

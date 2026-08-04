"""Tests for json_file.py — JSON 原子写 seam 与加密支持（R-07）。"""

from __future__ import annotations

import json
import pytest
from cryptography.fernet import Fernet, InvalidToken

from json_file import atomic_write_json, set_encryption_key, try_load_json


# ── fixtures ────────────────────────────────────────────


@pytest.fixture(autouse=True)
def cleanup_encryption():
    """每个测试后清理加密密钥，避免全局状态影响其他测试。"""
    yield
    set_encryption_key(None)


# ── 加密解密 ────────────────────────────────────────────


def test_encryption_roundtrip(tmp_path):
    """加密写入后能解密读取，且文件内容非明文。"""
    key = Fernet.generate_key()
    set_encryption_key(key)
    path = tmp_path / "secret.json"
    data = {"hello": "world", "nested": {"a": 1}}
    atomic_write_json(path, data)

    # 文件内容应非明文（已加密）
    raw = path.read_bytes()
    assert b"hello" not in raw

    # 读取时应能解密
    loaded = try_load_json(path)
    assert loaded == data


def test_encryption_wrong_key_fails(tmp_path):
    """错误密钥读取失败（InvalidToken）。"""
    key1 = Fernet.generate_key()
    key2 = Fernet.generate_key()
    set_encryption_key(key1)
    path = tmp_path / "secret.json"
    atomic_write_json(path, {"msg": "secret"})

    # 切换密钥后读取应失败
    set_encryption_key(key2)
    with pytest.raises(InvalidToken):
        try_load_json(path)


def test_no_encryption_by_default(tmp_path):
    """默认不加密，文件仍是纯文本 JSON。"""
    set_encryption_key(None)
    path = tmp_path / "plain.json"
    data = {"plain": "text"}
    atomic_write_json(path, data)

    # 文件内容应为纯文本 JSON
    with open(path, "r", encoding="utf-8") as f:
        assert json.load(f) == data

    # 同时 try_load_json 也应正常读取
    assert try_load_json(path) == data
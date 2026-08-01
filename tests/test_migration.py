"""
Tests for migrate_legacy_data — 旧数据一次性迁移到统一目录（O-22）。
"""

from __future__ import annotations

import json
from pathlib import Path

from data_store import migrate_legacy_data


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_no_legacy_data_is_noop(tmp_path):
    """legacy 无 data.json：不创建目标目录、不做任何操作。"""
    target = tmp_path / "target"
    migrate_legacy_data(tmp_path / "legacy", target)
    assert not target.exists()


def test_target_has_data_skips_and_keeps_target(tmp_path):
    """目标已有 data.json：跳过迁移，目标内容不被覆盖。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"old": 1})

    target = tmp_path / "target"
    target.mkdir()
    _write_json(target / "data.json", {"new": 2})

    migrate_legacy_data(legacy, target)

    assert json.loads((target / "data.json").read_text(encoding="utf-8")) == {"new": 2}


def test_migrates_data_and_backups_and_settings(tmp_path):
    """目标为空：迁移 data.json + 全部滚动备份 + settings.json，并创建目标目录。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"date": "2026-08-01"})
    _write_json(legacy / "data.json.bak", {"bak": 0})
    _write_json(legacy / "data.json.bak.1", {"bak1": 1})
    _write_json(legacy / "data.json.bak.2", {"bak2": 2})
    _write_json(legacy / "data.json.bak.3", {"bak3": 3})
    _write_json(legacy / "settings.json", {"theme": "dark"})

    target = tmp_path / "target"
    migrate_legacy_data(legacy, target)

    assert (target / "data.json").exists()
    assert (target / "data.json.bak").exists()
    for i in range(1, 4):
        assert (target / f"data.json.bak.{i}").exists()
    assert (target / "settings.json").exists()
    assert json.loads((target / "settings.json").read_text(encoding="utf-8")) == {
        "theme": "dark"
    }


def test_migrate_is_non_destructive(tmp_path):
    """复制而非移动：迁移后源文件仍保留。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"keep": True})

    migrate_legacy_data(legacy, tmp_path / "target")

    assert (legacy / "data.json").exists()


def test_migrate_without_settings(tmp_path):
    """legacy 无 settings.json：仍迁移 data.json，目标不产生 settings。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"v": 1})

    target = tmp_path / "target"
    migrate_legacy_data(legacy, target)

    assert (target / "data.json").exists()
    assert not (target / "settings.json").exists()


def test_migrate_logs_message(tmp_path, caplog):
    """成功迁移时记录 info 日志。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"v": 1})

    with caplog.at_level("INFO"):
        migrate_legacy_data(legacy, tmp_path / "target")

    assert any(
        "已从" in rec.message and "迁移数据到" in rec.message
        for rec in caplog.records
    )

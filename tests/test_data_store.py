"""
Tests for data_store.py — 数据持久化层。
"""

import json
import tempfile
from pathlib import Path

import pytest

from data_store import DataStore


# ── Fixtures ─────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def make_store(tmp_dir: Path, max_backups: int = 3) -> DataStore:
    return DataStore(
        data_file=tmp_dir / "data.json",
        backup_file=tmp_dir / "data.json.bak",
        max_backups=max_backups,
    )


# ── Load fresh ───────────────────────────────────────

def test_load_empty(tmp_dir):
    store = make_store(tmp_dir)
    assert store.load() == {}


# ── Save & Load round-trip ───────────────────────────

def test_save_and_load(tmp_dir):
    store = make_store(tmp_dir)
    record = {"2026-07-20": {"cash": 100.0, "warehouse": 200.0}}
    store.save(record)
    assert store.load() == record


def test_save_overwrite(tmp_dir):
    store = make_store(tmp_dir)
    store.save({"2026-07-19": {"cash": 10.0, "warehouse": 20.0}})
    store.save({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    result = store.load()
    assert "2026-07-19" not in result
    assert result["2026-07-20"]["cash"] == 100.0


# ── File I/O integrity ───────────────────────────────

def test_data_file_created(tmp_dir):
    store = make_store(tmp_dir)
    store.save({"key": "value"})
    assert (tmp_dir / "data.json").exists()


def test_data_file_is_valid_json(tmp_dir):
    store = make_store(tmp_dir)
    store.save({"key": "value"})
    with open(tmp_dir / "data.json", "r", encoding="utf-8") as f:
        assert json.load(f) == {"key": "value"}


# ── Backup rotation ──────────────────────────────────

def test_backup_created_on_save(tmp_dir):
    """第一次保存无旧文件可备份；第二次保存时会将第一次的数据写入滚动备份。"""
    store = make_store(tmp_dir)
    store.save({"v": 1})       # 创建 data.json，尚无备份
    store.save({"v": 2})       # 将 v=1 备份为 .bak.1 / .bak
    assert (tmp_dir / "data.json.bak.1").exists()
    assert (tmp_dir / "data.json.bak").exists()


def test_backup_rotation(tmp_dir):
    store = make_store(tmp_dir, max_backups=3)
    # 依次保存 5 次，验证只有 3 份滚动备份 + 旧版兼容备份
    for i in range(5):
        store.save({"v": i})

    # .bak.1 应包含最新一次保存前的版本（v=3）
    for idx in range(1, 4):
        path = tmp_dir / f"data.json.bak.{idx}"
        assert path.exists(), f"Expected {path} to exist"

    # 不应有 .bak.4
    assert not (tmp_dir / "data.json.bak.4").exists()


def test_backup_numbering(tmp_dir):
    """验证 bak.1 是最新备份（刚写入前被备份的状态）。"""
    store = make_store(tmp_dir, max_backups=3)

    store.save({"step": 1})
    store.save({"step": 2})

    # bak.1 应包含 step=1 的数据（因为 save({"step":2}) 前备份了 step=1）
    with open(tmp_dir / "data.json.bak.1", "r", encoding="utf-8") as f:
        assert json.load(f) == {"step": 1}


# ── Recovery from backup ─────────────────────────────

def test_recover_from_corrupt_main(tmp_dir):
    """主文件损坏时，应从最近备份恢复。"""
    store = make_store(tmp_dir, max_backups=2)

    # 先写两条数据，让第一次的数据进入滚动备份
    store.save({"ok": True})
    store.save({"v": 2})

    # 破坏主文件
    tmp_dir.joinpath("data.json").write_text("this is not json", encoding="utf-8")

    # 再次加载，应该从 .bak（上次写的 v=2）恢复
    data = store.load()
    assert data is not None and len(data) > 0


def test_recover_from_rolling_backup(tmp_dir):
    """主文件和 bak 都损坏时，回退到滚动备份。"""
    store = make_store(tmp_dir, max_backups=2)

    store.save({"v": 1})
    store.save({"v": 2})

    # 破坏主文件和 .bak
    tmp_dir.joinpath("data.json").write_text("corrupt", encoding="utf-8")
    tmp_dir.joinpath("data.json.bak").write_text("corrupt", encoding="utf-8")

    # 仍应从 .bak.1 恢复（v=1）
    data = store.load()
    assert "v" in data


def test_recover_when_all_corrupt(tmp_dir):
    """全部损坏时返回空字典。"""
    store = make_store(tmp_dir)
    tmp_dir.joinpath("data.json").write_text("bad", encoding="utf-8")
    assert store.load() == {}


# ── No data file ─────────────────────────────────────

def test_no_data_file_returns_empty(tmp_dir):
    store = make_store(tmp_dir)
    assert store.load() == {}


# ── Atomic write: no .tmp residue ────────────────────

def test_no_tmp_file_left(tmp_dir):
    store = make_store(tmp_dir)
    store.save({"x": "y"})
    tmp_files = list(tmp_dir.glob("*.tmp"))
    assert len(tmp_files) == 0


# ── Empty save ───────────────────────────────────────

def test_save_empty_dict(tmp_dir):
    store = make_store(tmp_dir)
    store.save({})
    assert store.load() == {}


# ── Special characters ───────────────────────────────

def test_unicode_in_data(tmp_dir):
    store = make_store(tmp_dir)
    store.save({"日期": "测试", "value": "¥1,234"})
    data = store.load()
    assert data["日期"] == "测试"

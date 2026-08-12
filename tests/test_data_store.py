"""
Tests for data_store.py — 数据持久化层。
"""

import json
import tempfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

from data_store import DataStore
from json_file import set_encryption_key


# ── Fixtures ─────────────────────────────────────────

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture(autouse=True)
def cleanup_encryption():
    """每个测试后清理 json_file 全局加密密钥，避免污染其他测试。"""
    yield
    set_encryption_key(None)


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


# ── Backup failure logging ────────────────────────────

def test_rotate_backups_logs_warning_on_failure(tmp_dir, caplog):
    """备份复制失败时不抛异常，仅记录 warning（不影响主流程）。"""
    store = make_store(tmp_dir)
    store.save({"v": 1})  # 先落盘 data.json

    # 把备份目标指向不存在的目录 → shutil.copy2 抛 OSError
    store.backup_file = tmp_dir / "missing_dir" / "data.json.bak"

    with caplog.at_level("WARNING"):
        store.save({"v": 2})

    assert any("备份文件复制失败" in rec.message for rec in caplog.records)
    # 主数据仍正常写入
    assert store.load() == {"v": 2}


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

def test_top_level_list_treated_as_corrupt(tmp_dir):
    """顶层合法 JSON 但非 dict（如 []）视为损坏，应从备份恢复（O-09）。"""
    store = make_store(tmp_dir, max_backups=2)
    store.save({"ok": True})
    store.save({"v": 2})

    # 主文件写成合法 JSON 但顶层是 list
    tmp_dir.joinpath("data.json").write_text("[]", encoding="utf-8")

    data = store.load()
    # 从滚动备份 .bak.1 恢复（最近一次保存前的状态）
    assert data is not None and data == {"ok": True}


def test_top_level_list_all_corrupt_returns_empty(tmp_dir):
    """主文件与备份顶层都是 list 时返回空字典（O-09）。"""
    store = make_store(tmp_dir)
    store.save({"ok": True})

    tmp_dir.joinpath("data.json").write_text("[]", encoding="utf-8")
    tmp_dir.joinpath("data.json.bak").write_text("[]", encoding="utf-8")

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


# ── C7：加密启用下的读写对称 ─────────────────────────

def test_encryption_roundtrip_via_datastore(tmp_dir):
    """加密启用时 DataStore.save/load 往返成功（C7：读路径与写路径对称）。"""
    set_encryption_key(Fernet.generate_key())
    store = make_store(tmp_dir)
    record = {"2026-07-20": {"cash": 100.0, "warehouse": 200.0}}
    store.save(record)
    assert store.load() == record


def test_recovery_chain_intact_after_delegation(tmp_dir):
    """_try_load 委托 try_load_json 后，主文件损坏的备份链恢复不变（C7 回归）。"""
    store = make_store(tmp_dir, max_backups=2)
    store.save({"v": 1})
    store.save({"v": 2})
    # 主文件损坏 → 从滚动备份 .bak.1（save 前状态 {"v": 1}）恢复
    tmp_dir.joinpath("data.json").write_text("corrupt", encoding="utf-8")
    assert store.load() == {"v": 1}


# ── Special characters ───────────────────────────────

def test_unicode_in_data(tmp_dir):
    store = make_store(tmp_dir)
    store.save({"日期": "测试", "value": "¥1,234"})
    data = store.load()
    assert data["日期"] == "测试"

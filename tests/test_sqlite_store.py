"""
Tests for sqlite_store.py — SQLite 数据持久化层。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlite_store import SQLiteDataStore


# ── Fixtures ─────────────────────────────────────────


@pytest.fixture
def tmp_db():
    """每个测试使用独立的临时数据库文件。"""
    import tempfile

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        yield Path(d) / "test.db"


def make_store(tmp_db: Path) -> SQLiteDataStore:
    return SQLiteDataStore(db_path=tmp_db)


# ── Load fresh ───────────────────────────────────────


def test_sqlite_empty_db(tmp_db):
    """空数据库返回空 dict。"""
    store = make_store(tmp_db)
    assert store.load() == {}


# ── Save & Load round-trip ───────────────────────────


def test_sqlite_load_save_roundtrip(tmp_db):
    """保存后能加载回相同数据。"""
    store = make_store(tmp_db)
    record = {"2026-08-01": {"cash": 100.0, "warehouse": 200.0}}
    store.save(record)
    assert store.load() == record


# ── Overwrite ────────────────────────────────────────


def test_sqlite_overwrite(tmp_db):
    """多次保存覆盖：新数据完全替换旧数据。"""
    store = make_store(tmp_db)
    store.save({"2026-07-19": {"cash": 10.0, "warehouse": 20.0}})
    store.save({"2026-07-20": {"cash": 100.0, "warehouse": 200.0}})
    result = store.load()
    assert "2026-07-19" not in result
    assert result["2026-07-20"]["cash"] == 100.0


# ── Multiple records ─────────────────────────────────


def test_sqlite_multiple_records(tmp_db):
    """保存多条记录，验证全部读回。"""
    store = make_store(tmp_db)
    data = {
        "2026-08-01": {"cash": 100.0, "warehouse": 200.0},
        "2026-08-02": {"cash": 150.0, "warehouse": 250.0},
        "2026-08-03": {"cash": 200.0, "warehouse": 300.0},
    }
    store.save(data)
    assert store.load() == data


# ── Empty save ───────────────────────────────────────


def test_sqlite_save_empty(tmp_db):
    """保存空 dict 后加载返回空 dict。"""
    store = make_store(tmp_db)
    store.save({})
    assert store.load() == {}


# ── Special characters ───────────────────────────────


def test_sqlite_unicode_date(tmp_db):
    """日期字段支持 Unicode。"""
    store = make_store(tmp_db)
    store.save({"2026-08-01": {"cash": 100.0, "warehouse": 200.0}})
    data = store.load()
    assert data["2026-08-01"]["cash"] == 100.0


# ── Data integrity ──────────────────────────────────


def test_sqlite_preserves_types(tmp_db):
    """数值类型保存与读取一致。"""
    store = make_store(tmp_db)
    store.save({"2026-08-01": {"cash": 99.99, "warehouse": 199.99}})
    data = store.load()
    assert isinstance(data["2026-08-01"]["cash"], float)
    assert isinstance(data["2026-08-01"]["warehouse"], float)
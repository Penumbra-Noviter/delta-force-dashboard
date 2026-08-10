"""
Tests for account_store — 多账号存储层（Y 系列）。

业务层测试只验证「文件系统上的真实效果」（tmp_path 显式注入），
绝不触碰真实用户目录；每账号 DataStore 的原子写 / 损坏恢复 / 滚动备份
继承自 data_store（此处仅验证路径注入与继承链路）。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from account_store import (
    DEFAULT_ACCOUNT_NAME,
    AccountStore,
)

__all__ = []


@pytest.fixture
def store(tmp_path) -> AccountStore:
    """tmp_path 隔离的 AccountStore（零真实用户目录触碰）。"""
    return AccountStore(tmp_path / "accounts")


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# ── list_accounts：目录扫描（目录名 = 账号名）──────────────


def test_list_accounts_empty_when_dir_missing(tmp_path):
    """accounts 目录缺失 → 返回 []（不创建目录）。"""
    store = AccountStore(tmp_path / "nope")
    assert store.list_accounts() == []
    assert not (tmp_path / "nope").exists()


def test_list_accounts_empty_when_dir_empty(tmp_path):
    """accounts 目录存在但为空 → 返回 []。"""
    store = AccountStore(tmp_path / "accounts")
    store.accounts_dir.mkdir()
    assert store.list_accounts() == []


def test_list_accounts_returns_dir_names_sorted(tmp_path):
    """目录名即账号名：非空目录返回账号名列表（稳定排序）。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account("主账号")
    store.create_account("小号")
    assert store.list_accounts() == ["主账号", "小号"]


# ── create_account：新建账号（H5 空库起步）─────────────────


def test_create_account_creates_empty_dir(tmp_path):
    """新建成功：返回 None，账号目录创建且从空数据开始（无 data.json）。"""
    store = AccountStore(tmp_path / "accounts")
    assert store.create_account("小号") is None
    account_dir = tmp_path / "accounts" / "小号"
    assert account_dir.is_dir()
    assert not (account_dir / "data.json").exists()  # H5：空库，首次 load 为 {}


def test_create_account_duplicate_rejected(tmp_path):
    """重名 → 拒绝，返回可读原因，不产生额外目录。"""
    store = AccountStore(tmp_path / "accounts")
    assert store.create_account("小号") is None
    reason = store.create_account("小号")
    assert isinstance(reason, str) and "已存在" in reason
    assert len(store.list_accounts()) == 1


@pytest.mark.parametrize(
    "name",
    ["", "   ", "a/b", "a\\b", "a:b", "a*b", 'a"b', "a<b", "a>b", "a|b", " a", "a ", ".a", "a."],
)
def test_create_account_rejects_invalid_names(tmp_path, name):
    """非法名（空 / 禁用字符 / 首尾空格或点）→ 拒绝、可读原因、零目录产生。"""
    store = AccountStore(tmp_path / "accounts")
    reason = store.create_account(name)
    assert isinstance(reason, str) and reason
    assert store.list_accounts() == []
    assert not (tmp_path / "accounts").exists() or not list((tmp_path / "accounts").iterdir())


def test_create_account_rejects_non_string(tmp_path):
    """非文本输入（None）→ 拒绝并可读原因，不产生目录（防御守卫）。"""
    store = AccountStore(tmp_path / "accounts")
    reason = store.create_account(None)  # type: ignore[arg-type]
    assert isinstance(reason, str) and "文本" in reason
    assert store.list_accounts() == []


def test_create_account_accepts_chinese_and_spaces(tmp_path):
    """合法名（中文 / 空格在中间）→ 成功。"""
    store = AccountStore(tmp_path / "accounts")
    assert store.create_account("我的 2 号本") is None
    assert (tmp_path / "accounts" / "我的 2 号本").is_dir()


# ── resolve_account：兜底回退（决策 3 / H3）────────────────


def test_resolve_falls_back_to_default_when_current_missing(tmp_path):
    """current 为 None → 回退主账号，且自动创建主账号目录（空数据）。"""
    store = AccountStore(tmp_path / "accounts")
    assert store.resolve_account(None) == DEFAULT_ACCOUNT_NAME
    assert (tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME).is_dir()
    assert not (tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME / "data.json").exists()


def test_resolve_falls_back_to_default_when_not_string(tmp_path):
    """current 非字符串（如 int）→ 回退主账号。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account("主账号")
    assert store.resolve_account(123) == DEFAULT_ACCOUNT_NAME


def test_resolve_falls_back_when_current_dir_missing(tmp_path):
    """current 指向不存在目录 → 回退主账号（主账号已有则不重建）。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account(DEFAULT_ACCOUNT_NAME)
    store.create_account("小号")
    assert store.resolve_account("已删除账号") == DEFAULT_ACCOUNT_NAME
    assert store.list_accounts() == [DEFAULT_ACCOUNT_NAME, "小号"]


def test_resolve_keeps_valid_current(tmp_path):
    """current 有效（目录存在）→ 原样返回，不跳变。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account("小号")
    assert store.resolve_account("小号") == "小号"


def test_fresh_environment_first_run(tmp_path):
    """全新环境首次运行：无 accounts 无数据 → 列表为空、解析兜底建主账号空库。"""
    store = AccountStore(tmp_path / "accounts")
    assert store.list_accounts() == []          # 无迁移、无账号
    assert store.resolve_account(None) == DEFAULT_ACCOUNT_NAME  # 自动建主账号
    default_dir = tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME
    assert default_dir.is_dir()
    assert store.new_store(DEFAULT_ACCOUNT_NAME).load() == {}  # 空库自建（H3/H5）


# ── DataStore 路径注入：原子写 / 损坏恢复 / 滚动备份继承 ────


def test_new_store_points_at_account_files(tmp_path):
    """new_store(name) 的 DataStore 指向该账号目录下的 data.json/bak。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account("小号")
    ds = store.new_store("小号")
    assert ds.data_file == tmp_path / "accounts" / "小号" / "data.json"
    assert ds.backup_file == tmp_path / "accounts" / "小号" / "data.json.bak"


def test_new_store_save_load_roundtrip(tmp_path):
    """保存 → 数据落在该账号目录文件；另一账号文件不受影响（账号隔离）。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account("主账号")
    store.create_account("小号")

    ds_a = store.new_store("主账号")
    ds_a.save({"2026-08-01": {"cash": 1.0, "warehouse": 2.0}})
    ds_b = store.new_store("小号")

    assert (tmp_path / "accounts" / "主账号" / "data.json").exists()
    assert not (tmp_path / "accounts" / "小号" / "data.json").exists()
    assert ds_b.load() == {}  # 空库起步（H5）
    assert ds_a.load() == {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}


def test_new_store_recovers_from_corrupt_data(tmp_path):
    """损坏恢复继承：账号 data.json 损坏 → 从该账号滚动备份恢复。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account("小号")
    ds = store.new_store("小号")
    ds.save({"2026-08-01": {"cash": 1.0, "warehouse": 2.0}})
    ds.save({"2026-08-01": {"cash": 2.0, "warehouse": 3.0}})  # 二次保存产生备份

    data_file = tmp_path / "accounts" / "小号" / "data.json"
    data_file.write_text("{corrupt", encoding="utf-8")  # 模拟损坏

    # DataStore 契约：备份 = 保存前版本，损坏后从最近备份恢复
    assert ds.load() == {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}
    # 恢复链路写回正式文件（DataStore 契约）
    assert json.loads(data_file.read_text(encoding="utf-8")) == {
        "2026-08-01": {"cash": 1.0, "warehouse": 2.0}
    }


def test_new_store_rotates_backups(tmp_path):
    """滚动备份继承：多次保存后该账号目录保留 data.json.bak 系列。"""
    store = AccountStore(tmp_path / "accounts")
    store.create_account("小号")
    ds = store.new_store("小号")
    for i in range(4):
        ds.save({"2026-08-01": {"cash": float(i), "warehouse": float(i)}})

    account_dir = tmp_path / "accounts" / "小号"
    assert (account_dir / "data.json.bak").exists()
    for i in range(1, 4):
        assert (account_dir / f"data.json.bak.{i}").exists()

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
    MIGRATED_V2_MARKER_NAME,
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


@pytest.mark.parametrize(
    "name",
    ["abc\x00def", "a\x1f b", "制表\t符", "换行\n名"],
)
def test_create_account_rejects_control_characters(tmp_path, name):
    """含控制字符（ord < 32，如 NUL/tab/换行）→ 拒绝、可读原因、零目录（F1）。"""
    store = AccountStore(tmp_path / "accounts")
    reason = store.create_account(name)
    assert isinstance(reason, str) and reason
    assert store.list_accounts() == []
    assert not (tmp_path / "accounts").exists() or not list((tmp_path / "accounts").iterdir())


def test_create_account_rejects_overlong_name(tmp_path):
    """超过 64 字符 → 拒绝、可读原因、零目录（F1 长度上限）。"""
    store = AccountStore(tmp_path / "accounts")
    reason = store.create_account("长" * 65)
    assert isinstance(reason, str) and "64" in reason
    assert store.list_accounts() == []


def test_create_account_accepts_name_at_length_limit(tmp_path):
    """恰好 64 字符 → 合法（长度上限边界，F1）。"""
    store = AccountStore(tmp_path / "accounts")
    assert store.create_account("号" * 64) is None
    assert (tmp_path / "accounts" / ("号" * 64)).is_dir()


def test_create_account_mkdir_oserror_returns_reason(tmp_path, monkeypatch):
    """mkdir 失败（OSError）→ 返回可读原因、不抛异常、不产生目录（F1）。"""
    from pathlib import Path

    def _boom(self, *a, **kw):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "mkdir", _boom)
    store = AccountStore(tmp_path / "accounts")
    reason = store.create_account("小号")
    assert isinstance(reason, str) and ("创建" in reason or "失败" in reason)
    assert store.list_accounts() == []


def test_ensure_default_account_mkdir_oserror_warns(tmp_path, monkeypatch, caplog):
    """_ensure_default_account mkdir 失败 → warning 日志 + 仍返回主账号名（F2）。"""
    from pathlib import Path

    def _boom(self, *a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "mkdir", _boom)
    store = AccountStore(tmp_path / "accounts")
    with caplog.at_level("WARNING"):
        name = store.resolve_account(None)
    assert name == DEFAULT_ACCOUNT_NAME  # 兜底仍返回主账号，启动路径不崩溃
    assert any("创建失败" in rec.message for rec in caplog.records)


def test_resolve_rejects_illegal_existing_dir_name(tmp_path):
    """目录存在但目录名非法（点开头）→ 拒绝并回退主账号（F3）。"""
    store = AccountStore(tmp_path / "accounts")
    (store.accounts_dir / ".dot").mkdir(parents=True)
    assert store.resolve_account(".dot") == DEFAULT_ACCOUNT_NAME
    assert (store.accounts_dir / DEFAULT_ACCOUNT_NAME).is_dir()


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


# ── migrate_legacy_to_default：v2 旧数据迁移（Y-02）────────
#
# 触发条件（决策 2）：accounts/ 不存在 **且** data_dir/data.json 存在 →
# 复制 data.json + 全部 data.json.bak* 到 accounts/主账号/，写 accounts/.migrated_v2。
# 复制非移动、永不自动删源（O-22 铁律）；data_dir 显式注入，零真实用户目录。


def test_migrate_copies_data_and_backups_to_default(tmp_path):
    """触发条件满足：data.json + 全部滚动备份复制到主账号，写 .migrated_v2 标记。"""
    _write_json(tmp_path / "data.json", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}})
    _write_json(tmp_path / "data.json.bak", {"bak": 0})
    _write_json(tmp_path / "data.json.bak.1", {"bak1": 1})
    _write_json(tmp_path / "data.json.bak.2", {"bak2": 2})

    store = AccountStore(tmp_path / "accounts")
    store.migrate_legacy_to_default(tmp_path)

    default_dir = tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME
    assert json.loads((default_dir / "data.json").read_text(encoding="utf-8")) == {
        "2026-08-01": {"cash": 1.0, "warehouse": 2.0}
    }
    assert json.loads((default_dir / "data.json.bak").read_text(encoding="utf-8")) == {
        "bak": 0
    }
    assert json.loads(
        (default_dir / "data.json.bak.1").read_text(encoding="utf-8")
    ) == {"bak1": 1}
    assert json.loads(
        (default_dir / "data.json.bak.2").read_text(encoding="utf-8")
    ) == {"bak2": 2}
    assert (tmp_path / "accounts" / MIGRATED_V2_MARKER_NAME).exists()


def test_migrate_preserves_source_files(tmp_path):
    """复制非移动：迁移后源 data.json 与全部备份保留且内容不变。"""
    _write_json(tmp_path / "data.json", {"v": 1})
    _write_json(tmp_path / "data.json.bak.1", {"bak1": 1})

    AccountStore(tmp_path / "accounts").migrate_legacy_to_default(tmp_path)

    assert json.loads((tmp_path / "data.json").read_text(encoding="utf-8")) == {"v": 1}
    assert json.loads((tmp_path / "data.json.bak.1").read_text(encoding="utf-8")) == {
        "bak1": 1
    }


def test_migrate_skips_when_accounts_exists_empty(tmp_path):
    """accounts/ 已存在但为空 → 一律不迁移：不建主账号、无 marker、源保留。"""
    _write_json(tmp_path / "data.json", {"v": 1})
    accounts_dir = tmp_path / "accounts"
    accounts_dir.mkdir()

    AccountStore(accounts_dir).migrate_legacy_to_default(tmp_path)

    assert not (accounts_dir / DEFAULT_ACCOUNT_NAME).exists()
    assert not (accounts_dir / MIGRATED_V2_MARKER_NAME).exists()
    assert (tmp_path / "data.json").exists()  # 源保留


def test_migrate_skips_when_accounts_exists_and_does_not_overwrite(tmp_path):
    """accounts/ 已有账号目录 → 不迁移、不覆盖任何已有账号数据。"""
    _write_json(tmp_path / "data.json", {"old": 1})
    store = AccountStore(tmp_path / "accounts")
    store.create_account("小号")
    store.new_store("小号").save({"2026-08-02": {"cash": 9.0, "warehouse": 9.0}})

    store.migrate_legacy_to_default(tmp_path)

    assert not (tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME).exists()
    assert json.loads(
        (tmp_path / "accounts" / "小号" / "data.json").read_text(encoding="utf-8")
    ) == {"2026-08-02": {"cash": 9.0, "warehouse": 9.0}}
    assert (tmp_path / "data.json").exists()  # 源保留


def test_migrate_idempotent_when_marker_present(tmp_path):
    """marker 存在 → 跳过：二次运行不重复复制、目标数据不被覆盖（幂等）。"""
    _write_json(tmp_path / "data.json", {"v": 1})
    store = AccountStore(tmp_path / "accounts")
    store.migrate_legacy_to_default(tmp_path)
    assert (tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME / "data.json").exists()

    # 篡改源与目标：二次运行不得覆盖目标已有数据
    _write_json(tmp_path / "data.json", {"v": "改过了"})
    _write_json(tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME / "data.json", {"kept": 2})

    store.migrate_legacy_to_default(tmp_path)

    assert json.loads(
        (tmp_path / "accounts" / DEFAULT_ACCOUNT_NAME / "data.json").read_text(
            encoding="utf-8"
        )
    ) == {"kept": 2}
    assert json.loads((tmp_path / "data.json").read_text(encoding="utf-8")) == {
        "v": "改过了"
    }


def test_migrate_noop_on_fresh_environment(tmp_path):
    """全新环境（无 accounts、无旧 data.json）→ 无迁移、无 marker、无目录产生。"""
    store = AccountStore(tmp_path / "accounts")
    store.migrate_legacy_to_default(tmp_path)

    assert store.list_accounts() == []
    assert not (tmp_path / "accounts").exists()
    assert not (tmp_path / "accounts" / MIGRATED_V2_MARKER_NAME).exists()


def test_migrate_noop_without_legacy_data(tmp_path):
    """data_dir 存在但无 data.json（如空安装残留目录）→ 无迁移、无 marker。"""
    (tmp_path / "unused.txt").write_text("x", encoding="utf-8")

    store = AccountStore(tmp_path / "accounts")
    store.migrate_legacy_to_default(tmp_path)

    assert not (tmp_path / "accounts").exists()


def test_migrate_oserror_warns_not_raises(tmp_path, monkeypatch, caplog):
    """迁移中途 OSError → warning 日志、不抛异常、不写 marker、源保留。"""
    import shutil

    _write_json(tmp_path / "data.json", {"v": 1})

    def _boom(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copy2", _boom)

    with caplog.at_level("WARNING"):
        AccountStore(tmp_path / "accounts").migrate_legacy_to_default(tmp_path)

    assert any("迁移失败" in rec.message for rec in caplog.records)
    assert not (tmp_path / "accounts" / MIGRATED_V2_MARKER_NAME).exists()
    assert (tmp_path / "data.json").exists()  # 源不动


def test_migrate_logs_info_on_success(tmp_path, caplog):
    """成功迁移记录 info 日志（可观测）。"""
    _write_json(tmp_path / "data.json", {"v": 1})

    with caplog.at_level("INFO"):
        AccountStore(tmp_path / "accounts").migrate_legacy_to_default(tmp_path)

    assert any("主账号" in rec.message and "迁移" in rec.message for rec in caplog.records)


# ── main() 启动接线：v2 迁移顺序（Y-02 验收标准 7）────────
#
# O-22 旧目录迁移先执行（填充统一目录 data.json），v2 迁移在其后、
# MainWindow 构造之前。AST 静态断言防顺序回归（沿用 test_migration 先例）。


def _main_ast():
    import ast as ast_mod
    import inspect

    import main as main_mod

    source = inspect.getsource(main_mod)
    tree = ast_mod.parse(source)
    funcs = [
        n for n in tree.body if isinstance(n, ast_mod.FunctionDef) and n.name == "main"
    ]
    assert len(funcs) == 1
    return funcs[0]


def _call_lineno(node, name):
    """返回函数体内第一个调用名匹配（Attribute.attr 或 Name.id）的行号。"""
    import ast as ast_mod

    for child in ast_mod.walk(node):
        if not isinstance(child, ast_mod.Call):
            continue
        func = child.func
        if isinstance(func, ast_mod.Attribute) and func.attr == name:
            return child.lineno
        if isinstance(func, ast_mod.Name) and func.id == name:
            return child.lineno
    raise AssertionError(f"main() 中未找到 {name}(...) 调用")


def test_main_wires_v2_migration_after_o22_before_window():
    """v2 迁移在 O-22 migrate_legacy_data 之后、MainWindow 构造之前。"""
    main_fn = _main_ast()
    o22 = _call_lineno(main_fn, "migrate_legacy_data")
    v2 = _call_lineno(main_fn, "migrate_legacy_to_default")
    window = _call_lineno(main_fn, "MainWindow")
    assert o22 < v2 < window, (
        f"顺序必须为 O-22（L{o22}）→ v2（L{v2}）→ MainWindow（L{window}）"
    )

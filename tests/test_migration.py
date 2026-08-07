"""
Tests for migrate_legacy_data — 旧数据一次性迁移到统一目录（O-22）。

另含 main() 启动顺序回归（DATA_DIR 先建再开日志）——同一 O-22 数据目录主题。
"""

from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import main as main_mod
from data_store import MIGRATED_MARKER_NAME, log_legacy_cleanup_hint, migrate_legacy_data


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


def test_successful_migration_writes_marker(tmp_path):
    """成功迁移后，目标目录写入 .migrated 完成标记（F-02）。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"v": 1})

    target = tmp_path / "target"
    migrate_legacy_data(legacy, target)

    assert (target / MIGRATED_MARKER_NAME).exists()


def test_marker_written_when_target_already_has_data(tmp_path):
    """目标已有 data.json（视为已权威）：补写标记，便于提示旧源清理（F-02）。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"old": 1})

    target = tmp_path / "target"
    target.mkdir()
    _write_json(target / "data.json", {"new": 2})

    migrate_legacy_data(legacy, target)

    assert (target / MIGRATED_MARKER_NAME).exists()
    assert json.loads((target / "data.json").read_text(encoding="utf-8")) == {"new": 2}


def test_rerun_keeps_marker_and_data(tmp_path):
    """二次调用（目标已有 data.json 跳过迁移）：标记仍在、数据不被覆盖——幂等。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"v": 1})

    target = tmp_path / "target"
    migrate_legacy_data(legacy, target)
    migrate_legacy_data(legacy, target)

    assert (target / MIGRATED_MARKER_NAME).exists()
    assert json.loads((target / "data.json").read_text(encoding="utf-8")) == {"v": 1}


def test_no_legacy_data_writes_no_marker(tmp_path):
    """legacy 无 data.json：不写标记、不建目标目录。"""
    target = tmp_path / "target"
    migrate_legacy_data(tmp_path / "legacy", target)
    assert not target.exists()


def test_cleanup_hint_logs_when_marker_and_legacy_present(tmp_path, caplog):
    """标记存在且旧源 data.json 仍在：打 info 日志提示可手动清理（F-02）。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"v": 1})

    target = tmp_path / "target"
    migrate_legacy_data(legacy, target)

    with caplog.at_level("INFO"):
        log_legacy_cleanup_hint(legacy, target)

    assert any("旧数据源可手动清理" in rec.message for rec in caplog.records)


def test_cleanup_hint_silent_without_marker(tmp_path, caplog):
    """无标记（全新安装无迁移）：不打提示。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"v": 1})

    target = tmp_path / "target"
    target.mkdir()

    with caplog.at_level("INFO"):
        log_legacy_cleanup_hint(legacy, target)

    assert not any("旧数据源可手动清理" in rec.message for rec in caplog.records)


def test_cleanup_hint_silent_when_legacy_cleaned(tmp_path, caplog):
    """标记存在但旧源已删除（用户已手动清理）：不再提示。"""
    legacy = tmp_path / "legacy"
    legacy.mkdir()
    _write_json(legacy / "data.json", {"v": 1})

    target = tmp_path / "target"
    migrate_legacy_data(legacy, target)

    (legacy / "data.json").unlink()  # 模拟用户手动删除旧源

    with caplog.at_level("INFO"):
        log_legacy_cleanup_hint(legacy, target)

    assert not any("旧数据源可手动清理" in rec.message for rec in caplog.records)


# ── main() 启动顺序回归 ───────────────────────────────────
#
# O-22 把日志路径改挂 DATA_DIR 后，曾出现「空启动即崩」：
# main() 先构造 RotatingFileHandler（打开 LOG_FILE），再执行迁移——
# 而目录创建仅发生在迁移逻辑内，空启动（无旧数据、无 ~/Delta Force Dashboard）
# 时迁移提前返回、目录从未创建 → FileNotFoundError。
# 修复：main() 第一行显式 DATA_DIR.mkdir(parents=True, exist_ok=True)。
# 本组用 AST 静态断言「mkdir 必须先于 RotatingFileHandler」，防复发。


def _main_ast() -> ast.FunctionDef:
    source = inspect.getsource(main_mod)
    tree = ast.parse(source)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
    assert len(funcs) == 1, f"main.py 应恰有一个 main()，实际 {len(funcs)}"
    return funcs[0]


def _call_lineno(node: ast.FunctionDef, name: str) -> int:
    """返回函数体内第一个 `.name(...)`（Attribute）或 `name(...)`（Name）调用行号。"""
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute) and func.attr == name:
            return child.lineno
        if isinstance(func, ast.Name) and func.id == name:
            return child.lineno
    raise AssertionError(f"main() 中未找到 {name}(...) 调用")


def test_main_creates_data_dir_before_log_handler():
    """DATA_DIR.mkdir 必须在 RotatingFileHandler 之前执行。"""
    main_fn = _main_ast()
    mkdir_lineno = _call_lineno(main_fn, "mkdir")
    handler_lineno = _call_lineno(main_fn, "RotatingFileHandler")
    assert mkdir_lineno < handler_lineno, (
        f"DATA_DIR.mkdir（L{mkdir_lineno}）必须先于 RotatingFileHandler（L{handler_lineno}）"
        "——否则空启动时日志目录不存在，RotatingFileHandler 打开 LOG_FILE 抛 FileNotFoundError"
    )

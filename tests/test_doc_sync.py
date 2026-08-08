"""
F-01 冒烟测试：`scripts/doc_sync.py --check` 通过即 CODE_WIKI 基线同步。

只加 1 个冒烟测试（F-01 规模悖论边界）：工具脚本不堆测试数量，
用 --check 校验整条同步链路（pytest 收集 → AST 提取 → 文档比对）跑通即可。
tests_total 专项断言并入同一用例：头部横幅/属性表/依赖表的测试总数必须等于
pytest 收集总和——新增独立测试函数会改变收集总数，反噬本文件维护的基线。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

__all__ = ["test_doc_sync_check_passes"]

ROOT = Path(__file__).resolve().parent.parent


def _load_doc_sync():
    """以模块方式加载 scripts/doc_sync.py（scripts/ 无 __init__.py 包）。"""
    spec = importlib.util.spec_from_file_location(
        "doc_sync", ROOT / "scripts" / "doc_sync.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_doc_sync_check_passes() -> None:
    """doc_sync --check 必须通过：CODE_WIKI 机械标记与代码/测试数同步。"""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "doc_sync.py"), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (
        "CODE_WIKI 机械标记漂移（测试数/模块行数/方法签名不同步）。"
        f"\n请运行: python scripts/doc_sync.py\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )

    # tests_total 专项回归（2026-08-08 漂移现场：头部横幅/属性表/依赖表
    # 手工叙述测试数曾写 300/292 而实际 293，不受 tests: 逐文件标记保护；
    # --check 已比对 tests_total 内容，此处再显式断言文档标记 = 收集总数）。
    doc_sync = _load_doc_sync()
    counts = doc_sync.collect_test_counts(ROOT)
    total = str(sum(counts.values()))
    text = (ROOT / "CODE_WIKI.md").read_text(encoding="utf-8")
    totals = {
        content
        for kind, key, content, _, _ in doc_sync.scan_markers(text)
        if kind == "tests_total"
    }
    assert totals, "CODE_WIKI 缺少 tests_total 标记（头部横幅/属性表/依赖表测试数）"
    assert all(c == total for c in totals), (
        f"tests_total 标记与 pytest 收集总数不一致: 标记={sorted(totals)} 实际={total}"
        f"\n请运行: python scripts/doc_sync.py"
    )

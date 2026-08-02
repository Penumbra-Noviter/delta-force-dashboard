"""
F-01 冒烟测试：`scripts/doc_sync.py --check` 通过即 CODE_WIKI 基线同步。

只加 1 个冒烟测试（F-01 规模悖论边界）：工具脚本不堆测试数量，
用 --check 校验整条同步链路（pytest 收集 → AST 提取 → 文档比对）跑通即可。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__all__ = ["test_doc_sync_check_passes"]

ROOT = Path(__file__).resolve().parent.parent


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

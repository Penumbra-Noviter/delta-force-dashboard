"""
多账号存储层（Y 系列）：账号目录布局、账号名校验、账号解析与兜底。

布局约定（ADR-0005）：``accounts/<账号名>/data.json``，目录名即账号名，
不引入 accounts.json 元数据文件；每账号复用 ``DataStore(data_file,
backup_file)`` 路径注入，原子写 / 损坏恢复 / 滚动备份全部继承。

UI 层不得直接拼装账号路径——所有账号文件系统操作收敛到本模块。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config import DATA_DIR
from data_store import DataStore

__all__ = [
    "AccountStore",
    "DEFAULT_ACCOUNT_NAME",
    "ACCOUNTS_DIR_NAME",
    "validate_account_name",
]

logger = logging.getLogger(__name__)

# 默认账号：首次升级/兜底回退落点（H1 共识）。
DEFAULT_ACCOUNT_NAME = "主账号"
# 账号根目录名（位于统一数据目录 DATA_DIR 下）。
ACCOUNTS_DIR_NAME = "accounts"

# H1：Windows 目录名禁用字符（目录名即账号名，必须 sanitize）。
_FORBIDDEN_CHARS = set('\\/:*?"<>|')


def validate_account_name(name: str) -> str | None:
    """校验账号名：合法返回 None，否则返回可读拒绝原因。

    拒绝规则（H1）：非文本、空名（空串/纯空白）、含 ``\\ / : * ? " < > |``、
    首尾为空格或点。中文 / 字母 / 数字 / 中间空格均合法。
    """
    if not isinstance(name, str):
        return "账号名必须是文本"
    if not name.strip():
        return "账号名不能为空"
    if any(ch in _FORBIDDEN_CHARS for ch in name):
        return "账号名不能包含 \\ / : * ? \" < > | 字符"
    if name != name.strip():
        return "账号名首尾不能有空格"
    if name.startswith(".") or name.endswith("."):
        return "账号名首尾不能是点"
    return None


class AccountStore:
    """账号目录管理：列出 / 新建 / 解析当前账号 + DataStore 路径注入。

    所有操作只针对 ``accounts_dir``（测试显式注入 tmp_path，生产默认
    ``DATA_DIR/accounts``），零真实用户目录触碰由注入保证。
    """

    def __init__(self, accounts_dir: Path = DATA_DIR / ACCOUNTS_DIR_NAME) -> None:
        self.accounts_dir = Path(accounts_dir)

    # ── 公开接口 ────────────────────────────────────────

    def list_accounts(self) -> list[str]:
        """扫描 accounts 目录返回账号名列表（目录名 = 账号名，稳定排序）。

        目录缺失或为空 → ``[]``（不创建目录）。
        """
        if not self.accounts_dir.is_dir():
            return []
        return sorted(
            entry.name
            for entry in self.accounts_dir.iterdir()
            if entry.is_dir()
        )

    def create_account(self, name: str) -> str | None:
        """新建账号：成功返回 None，拒绝返回可读原因（不产生任何目录）。

        新账号从空数据开始（H5）：只创建目录，不写 data.json，
        首次 ``DataStore.load()`` 自然得到空库 ``{}``。
        """
        reason = validate_account_name(name)
        if reason is not None:
            return reason
        if name in self.list_accounts():
            return f"账号「{name}」已存在"
        (self.accounts_dir / name).mkdir(parents=True, exist_ok=True)
        logger.info("已创建账号：%s", name)
        return None

    def resolve_account(self, current: Any) -> str:
        """解析当前账号：返回目录存在且合法的账号名，并保证目录存在。

        兜底规则（决策 3）：current 缺失 / 非字符串 / 指向不存在目录 →
        回退「主账号」；accounts/ 为空或主账号目录缺失 → 自动创建
        「主账号」目录（空数据，H3）。
        """
        if isinstance(current, str) and current and (self.accounts_dir / current).is_dir():
            return current
        return self._ensure_default_account()

    # ── DataStore 路径注入 ──────────────────────────────

    def account_dir(self, name: str) -> Path:
        """账号目录路径（业务层唯一拼装点，UI 禁止直接拼装）。"""
        return self.accounts_dir / name

    def new_store(self, name: str) -> DataStore:
        """以账号路径注入构造 DataStore（原子写/损坏恢复/滚动备份全继承）。"""
        account_dir = self.account_dir(name)
        return DataStore(account_dir / "data.json", account_dir / "data.json.bak")

    # ── 内部方法 ────────────────────────────────────────

    def _ensure_default_account(self) -> str:
        """确保默认账号目录存在（幂等），返回「主账号」。"""
        default_dir = self.accounts_dir / DEFAULT_ACCOUNT_NAME
        if not default_dir.is_dir():
            default_dir.mkdir(parents=True, exist_ok=True)
            logger.info("已创建默认账号目录：%s", DEFAULT_ACCOUNT_NAME)
        return DEFAULT_ACCOUNT_NAME

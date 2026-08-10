"""
多账号存储层（Y 系列）：账号目录布局、账号名校验、账号解析与兜底。

布局约定（ADR-0005）：``accounts/<账号名>/data.json``，目录名即账号名，
不引入 accounts.json 元数据文件；每账号复用 ``DataStore(data_file,
backup_file)`` 路径注入，原子写 / 损坏恢复 / 滚动备份全部继承。

UI 层不得直接拼装账号路径——所有账号文件系统操作收敛到本模块。
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from config import DATA_DIR
from data_store import DataStore

__all__ = [
    "AccountStore",
    "DEFAULT_ACCOUNT_NAME",
    "ACCOUNTS_DIR_NAME",
    "MIGRATED_V2_MARKER_NAME",
    "validate_account_name",
]

logger = logging.getLogger(__name__)

# 默认账号：首次升级/兜底回退落点（H1 共识）。
DEFAULT_ACCOUNT_NAME = "主账号"
# 账号根目录名（位于统一数据目录 DATA_DIR 下）。
ACCOUNTS_DIR_NAME = "accounts"
# v2 迁移完成标记：写在 accounts/ 下，存在即跳过（幂等，ADR-0005）。
MIGRATED_V2_MARKER_NAME = ".migrated_v2"

# H1：Windows 目录名禁用字符（目录名即账号名，必须 sanitize）。
_FORBIDDEN_CHARS = set('\\/:*?"<>|')
# F1 评审修复：账号名长度上限（保守值，远小于 Windows 255 字符单目录名上限）。
MAX_ACCOUNT_NAME_LEN = 64


def validate_account_name(name: str) -> str | None:
    """校验账号名：合法返回 None，否则返回可读拒绝原因。

    拒绝规则（H1 + F1 评审修复）：非文本、空名（空串/纯空白）、
    含控制字符（ord < 32，如 NUL / tab / 换行）、超过 64 字符、
    含 ``\\ / : * ? " < > |``、首尾为空格或点。
    中文 / 字母 / 数字 / 中间空格均合法。
    """
    if not isinstance(name, str):
        return "账号名必须是文本"
    if not name.strip():
        return "账号名不能为空"
    if any(ord(ch) < 32 for ch in name):
        return "账号名不能包含控制字符"
    if len(name) > MAX_ACCOUNT_NAME_LEN:
        return f"账号名过长（最多 {MAX_ACCOUNT_NAME_LEN} 字符）"
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
        mkdir 失败（F1 评审修复：权限/磁盘 OSError）→ 记录 warning
        并返回可读原因，不向 UI 抛异常。
        """
        reason = validate_account_name(name)
        if reason is not None:
            return reason
        if name in self.list_accounts():
            return f"账号「{name}」已存在"
        try:
            (self.accounts_dir / name).mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("账号目录创建失败：%s（%s）", name, e)
            return f"账号目录创建失败：{e}"
        logger.info("已创建账号：%s", name)
        return None

    def resolve_account(self, current: Any) -> str:
        """解析当前账号：返回目录存在且合法的账号名，并保证目录存在。

        兜底规则（决策 3）：current 缺失 / 非字符串 / 指向不存在目录 →
        回退「主账号」；accounts/ 为空或主账号目录缺失 → 自动创建
        「主账号」目录（空数据，H3）。F3 评审修复：目录存在但目录名
        非法（如手工创建的点开头目录）同样回退，不直接采用。
        """
        if (
            isinstance(current, str)
            and current
            and validate_account_name(current) is None
            and (self.accounts_dir / current).is_dir()
        ):
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

    def migrate_legacy_to_default(self, data_dir: Path | None = None) -> None:
        """v2 旧数据迁移：统一目录 data.json → ``accounts/主账号/``（复制非移动）。

        触发条件（决策 2 / ADR-0005）：``accounts/`` 不存在 **且** 旧
        ``data_dir/data.json`` 存在 → 复制 data.json + 全部 ``data.json.bak*``
        到 ``accounts/主账号/``，完成后写 ``accounts/.migrated_v2`` 标记。

        - ``accounts/`` 已存在（含为空）→ 一律不迁移、不覆盖任何已有账号目录；
          marker 存在 → 幂等跳过，二次运行不重复复制。
        - 复制非移动：源文件保留，任何路径下绝不自动删除源文件（O-22 铁律）。
        - 迁移失败（OSError）→ warning 日志、不中断启动；不写 marker。
        - ``data_dir`` 缺省为 ``accounts_dir`` 的父目录（生产 = DATA_DIR），
          测试显式注入 tmp_path，零真实用户目录触碰。
        """
        accounts_dir = self.accounts_dir
        if (accounts_dir / MIGRATED_V2_MARKER_NAME).exists():
            return  # 迁移已完成（幂等）
        if accounts_dir.exists():
            return  # accounts/ 已存在（含为空）→ 一律不迁移
        legacy_dir = Path(data_dir) if data_dir is not None else accounts_dir.parent
        src_data = legacy_dir / "data.json"
        if not src_data.exists():
            return  # 无旧数据（全新环境）→ 无迁移、无 marker

        default_dir = accounts_dir / DEFAULT_ACCOUNT_NAME
        files: list[tuple[Path, Path]] = [(src_data, default_dir / "data.json")]
        for bak in sorted(legacy_dir.glob("data.json.bak*")):
            files.append((bak, default_dir / bak.name))

        try:
            default_dir.mkdir(parents=True, exist_ok=True)
            for src, dst in files:
                shutil.copy2(src, dst)
        except OSError as e:
            logger.warning("v2 旧数据迁移失败（数据仍在原位置，不影响启动）: %s", e)
            return
        self._write_v2_marker(accounts_dir)
        logger.info("已迁移旧数据到默认账号「%s」：%s", DEFAULT_ACCOUNT_NAME, default_dir)

    # ── 内部方法 ────────────────────────────────────────

    def _write_v2_marker(self, accounts_dir: Path) -> None:
        """写 ``.migrated_v2`` 完成标记（幂等；失败仅 warning，不影响主流程）。"""
        try:
            (accounts_dir / MIGRATED_V2_MARKER_NAME).write_text(
                "旧数据已迁移至 accounts/主账号/（v2）。源文件保留，"
                "应用不会自动删除。\n",
                encoding="utf-8",
            )
        except OSError as e:
            logger.warning("v2 迁移完成标记写入失败: %s", e)

    def _ensure_default_account(self) -> str:
        """确保默认账号目录存在（幂等），返回「主账号」。

        mkdir 失败（F2 评审修复：权限/磁盘 OSError）→ warning 日志、
        仍返回主账号名——启动路径的解析兜底不因目录创建失败而崩溃。
        """
        default_dir = self.accounts_dir / DEFAULT_ACCOUNT_NAME
        if not default_dir.is_dir():
            try:
                default_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning("默认账号目录创建失败: %s", e)
            else:
                logger.info("已创建默认账号目录：%s", DEFAULT_ACCOUNT_NAME)
        return DEFAULT_ACCOUNT_NAME

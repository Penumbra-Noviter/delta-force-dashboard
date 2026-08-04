"""
领域信号枚举：业务层返回语义信号，UI 层映射为主题颜色。

共享词汇的底部叶子（零依赖，可被任何层安全导入）：
- `RateSignal` 由 calculator 的 format_rate / format_signed_money / format_summary 返回，
  theme 据此做「信号 → 主题色」映射（D-01 收敛点）；
- `PnLSignal` 由 calculator 的 get_pnl_label 返回，table_widget 据此映射盈亏标签颜色。

信号只表达语义（方向 / 有无数据），不含任何颜色值——颜色映射永远留在 UI 层。
"""

from __future__ import annotations

from enum import Enum

__all__ = ["RateSignal", "PnLSignal"]


class RateSignal(Enum):
    """收益率信号枚举——UI 层根据信号映射颜色。"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    NONE = "none"


class PnLSignal(Enum):
    """盈亏信号枚举——UI 层根据信号映射颜色。"""
    PROFIT = "profit"
    LOSS = "loss"
    NEUTRAL = "neutral"
    NONE = "none"

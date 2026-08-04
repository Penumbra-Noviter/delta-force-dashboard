"""
展示文本生成：领域值 → 展示文本 + 语义信号。

与 calculator.py 解耦（架构评审候选 1/6），存放纯展示层函数：
- 格式化展示文本的纯函数（format_* 系列）
- 盈亏标签
- 窗口汇总文本（参数化版 #6：format_window_text 替代 format_summary + format_cash_summary）

依赖：formatting.py（format_money/format_short_date）+ signals.py（RateSignal/PnLSignal）+ config.py（常量）
"""

from __future__ import annotations

from config import RETENTION_LIMIT, _WEEK_DAYS as WEEK_DAYS
from formatting import format_money, format_short_date
from signals import PnLSignal, RateSignal

__all__ = [
    "format_rate",
    "format_signed_money",
    "format_window_text",
    "format_saved_indicator",
    "get_pnl_label",
]


def format_rate(rate: float | None) -> tuple[str, RateSignal]:
    """
    根据收益率返回 (格式化字符串, 信号) 二元组。
    UI 层应将信号映射为当前主题颜色。
    """
    if rate is None:
        return "—", RateSignal.NONE
    if rate > 0:
        return f"+{rate:.1f}%", RateSignal.POSITIVE
    if rate < 0:
        return f"{rate:.1f}%", RateSignal.NEGATIVE
    return "0.0%", RateSignal.NEUTRAL


def format_signed_money(value: float | None) -> tuple[str, RateSignal]:
    """根据带符号金额返回 (格式化字符串, 信号) 二元组。

    带符号金额（较前日差值、总盈亏）的统一展示入口：
    - None → "—"（NONE）
    - 正数 → "+¥…"（POSITIVE）
    - 负数 → "¥-…"（NEGATIVE，format_money 自带负号）
    - 零 → "¥0.00"（NEUTRAL，无 + 前缀）

    UI 层应将信号映射为当前主题颜色（见 app.theme.signal_color）。
    """
    if value is None:
        return "—", RateSignal.NONE
    if value > 0:
        return f"+{format_money(value)}", RateSignal.POSITIVE
    if value < 0:
        return format_money(value), RateSignal.NEGATIVE
    return format_money(0.0), RateSignal.NEUTRAL


def format_window_text(
    count: int,
    total: float | None,
    label: str,
    days: int = WEEK_DAYS,
) -> tuple[str, RateSignal]:
    """汇总标签展示文本的纯函数：按记录数与总变化返回 (文本, 信号)。

    参数化版 #6（替代 format_summary 与 format_cash_summary）：
    label = "总盈亏" 或 "现金总变化"，由调用方注入。

    与 summary() 语义对齐（录入条数基准）：
    - count == 0（total 为 None）：`最近N条{label}：数据不足`，信号 NONE；
    - count == 1：`最近N条{label}：¥X（仅 1 条记录）`，信号 NONE；
    - count >= 2：复用 format_signed_money（带符号、趋势信号）。

    UI 层把信号映射为当前主题颜色（app.theme.signal_color），
    弱化/常规字号等纯样式留 UI（D-07）。
    """
    prefix = f"最近{days}条{label}："
    if total is None:
        return f"{prefix}数据不足", RateSignal.NONE
    if count == 1:
        return f"{prefix}{format_money(total)}（仅 1 条记录）", RateSignal.NONE
    total_text, total_signal = format_signed_money(total)
    return f"{prefix}{total_text}", total_signal


def format_saved_indicator(
    save_date: str,
    warehouse: float,
    today: str,
    deleted: list[str],
    keep_days: int = RETENTION_LIMIT,
) -> str:
    """保存成功状态栏文本的纯函数（今日/历史日期 + 轮转清理提示）。

    - 保存日期为今日 → `✓ 今日已保存 — 仓库总收益 ¥X`；
    - 历史日期（编辑）→ `✓ MM-DD 已更新 — 仓库总收益 ¥X`；
    - 触发轮转删除（deleted 非空）追加「已保留最近 N 条记录，
      自动清理 M 条较早记录」（O-14/O-17 文案）。
    """
    if save_date == today:
        indicator = f"✓ 今日已保存 — 仓库总收益 {format_money(warehouse)}"
    else:
        indicator = (
            f"✓ {format_short_date(save_date)} 已更新 — "
            f"仓库总收益 {format_money(warehouse)}"
        )
    if deleted:
        indicator += (
            f"（已保留最近 {keep_days} 条记录，"
            f"自动清理 {len(deleted)} 条较早记录）"
        )
    return indicator


def get_pnl_label(
    prev_warehouse: float | None, current_warehouse: float
) -> tuple[str, PnLSignal]:
    """
    根据前后日仓库价值判断盈亏，返回 (标签, 信号) 二元组。
    UI 层应将信号映射为当前主题颜色。
    """
    if prev_warehouse is None:
        return "—", PnLSignal.NONE
    if current_warehouse > prev_warehouse:
        return "盈", PnLSignal.PROFIT
    if current_warehouse < prev_warehouse:
        return "亏", PnLSignal.LOSS
    return "—", PnLSignal.NEUTRAL
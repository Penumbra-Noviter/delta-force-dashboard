"""
业务逻辑：日期记录、最近历史查询、收益差值计算。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from config import DATE_FORMAT, get_color
from formatting import format_money

__all__ = [
    "DayRecord",
    "ProfitCalculatorLogic",
]


@dataclass(frozen=True)
class DayRecord:
    """单日现金与仓库价值记录。

    现金是仓库价值的组成部分（现金 ⊆ 仓库），总收益 = 仓库价值。
    """

    cash: float
    warehouse: float
    date: str

    @property
    def total(self) -> float:
        """总收益 = 仓库价值（已包含现金）。"""
        return self.warehouse


class ProfitCalculatorLogic:
    """处理数据查询、历史对比与差值展示。"""

    def __init__(self, data: dict) -> None:
        self.data = data

    def get_record(self, date_str: str) -> Optional[DayRecord]:
        """读取某一天的记录；字段缺失或格式异常时返回 None。"""
        raw = self.data.get(date_str)
        if not isinstance(raw, dict):
            return None
        try:
            return DayRecord(
                cash=float(raw["cash"]),
                warehouse=float(raw["warehouse"]),
                date=date_str,
            )
        except (KeyError, ValueError, TypeError):
            return None

    def save_record(self, date_str: str, cash: float, warehouse: float) -> DayRecord:
        """保存某日记录并返回对应模型。"""
        self.data[date_str] = {"cash": cash, "warehouse": warehouse}
        return DayRecord(cash=cash, warehouse=warehouse, date=date_str)

    def last_record_before(
        self, date_str: str, max_days: int = 365
    ) -> Optional[tuple[str, DayRecord]]:
        """查找给定日期之前最近一次有完整数据的日期。"""
        try:
            current = datetime.strptime(date_str, DATE_FORMAT)
        except ValueError:
            return None

        for _ in range(max_days):
            current -= timedelta(days=1)
            check_str = current.strftime(DATE_FORMAT)
            record = self.get_record(check_str)
            if record is not None:
                return check_str, record
        return None

    def get_weekly_records(
        self, end_date: str, days: int = 7
    ) -> list[tuple[str, "DayRecord | None"]]:
        """
        获取以 end_date 为截止日期的最近 N 天记录。

        返回按日期升序排列的 (date_str, DayRecord | None) 列表，
        None 表示该日无数据。
        """
        try:
            end = datetime.strptime(end_date, DATE_FORMAT)
        except ValueError:
            return []

        results: list[tuple[str, "DayRecord | None"]] = []
        for i in range(days - 1, -1, -1):
            d = end - timedelta(days=i)
            date_str = d.strftime(DATE_FORMAT)
            record = self.get_record(date_str)
            results.append((date_str, record))
        return results

    @staticmethod
    def calculate_rate(
        prev_warehouse: float | None, current_warehouse: float
    ) -> float | None:
        """计算较前日收益率百分比。无前日数据或前值为零时返回 None。"""
        if prev_warehouse is None or prev_warehouse == 0:
            return None
        return (current_warehouse - prev_warehouse) / prev_warehouse * 100

    @staticmethod
    def format_rate(rate: float | None) -> tuple[str, str]:
        """
        根据收益率返回 (格式化字符串, 颜色) 二元组。
        rate 为 None 时返回 ("—", muted_color)。
        """
        if rate is None:
            return "—", get_color("FG_MUTED")
        if rate > 0:
            return f"+{rate:.1f}%", get_color("FG_POS")
        if rate < 0:
            return f"{rate:.1f}%", get_color("FG_NEG")
        return "0.0%", get_color("FG_MUTED")

    @staticmethod
    def get_pnl_label(
        prev_warehouse: float | None, current_warehouse: float
    ) -> tuple[str, str]:
        """
        根据前后日仓库价值判断盈亏，返回 (标签, 背景色) 二元组。
        - 盈 → ("盈", green_bg)  绿底
        - 亏 → ("亏", red_bg)  红底
        - — → ("—", muted_bg)    灰底
        """
        if prev_warehouse is None:
            return "—", get_color("FG_MUTED")
        if current_warehouse > prev_warehouse:
            return "盈", get_color("FG_POS")
        if current_warehouse < prev_warehouse:
            return "亏", get_color("FG_NEG")
        return "—", get_color("FG_MUTED")

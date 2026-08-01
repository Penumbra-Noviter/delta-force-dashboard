"""
业务逻辑：日期记录、最近历史查询、收益差值计算。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from config import DATE_FORMAT, WEEK_DAYS

__all__ = [
    "DayRecord",
    "ProfitCalculatorLogic",
    "RateSignal",
    "PnLSignal",
]


logger = logging.getLogger(__name__)


class RateSignal(Enum):
    """收益率信号枚举——UI 层根据信号映射颜色。"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    NONE = "none"


class PnLSignal(Enum):
    """盈亏信号枚举——UI 层根据信号映射颜色。"""
    盈 = "profit"
    亏 = "loss"
    平 = "neutral"
    无 = "none"


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
        """保存某日记录并返回对应模型。

        业务层不强制「现金 ⊆ 仓库」不变式（允许保留已录入的异常数据并继续展示），
        仅对违反不变式的写入记录 warning——拦截由 UI 层 save_today 负责（O-08）。
        """
        if cash > warehouse:
            logger.warning(
                "记录违反不变式（现金 %.2f > 仓库 %.2f，date=%s）",
                cash,
                warehouse,
                date_str,
            )
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

    @staticmethod
    def get_pnl_label(
        prev_warehouse: float | None, current_warehouse: float
    ) -> tuple[str, PnLSignal]:
        """
        根据前后日仓库价值判断盈亏，返回 (标签, 信号) 二元组。
        UI 层应将信号映射为当前主题颜色。
        """
        if prev_warehouse is None:
            return "—", PnLSignal.无
        if current_warehouse > prev_warehouse:
            return "盈", PnLSignal.盈
        if current_warehouse < prev_warehouse:
            return "亏", PnLSignal.亏
        return "—", PnLSignal.平

    def delete_record(self, date_str: str) -> bool:
        """删除某日记录；不存在时返回 False。"""
        if date_str in self.data:
            del self.data[date_str]
            return True
        return False

    def rotate_weekly(self, days: int = WEEK_DAYS) -> None:
        """7 日保留策略：数据超过 days 天时删除最旧记录，保持最多 days 条。"""
        if len(self.data) <= days:
            return
        sorted_dates = sorted(self.data.keys())
        for old_date in sorted_dates[: len(sorted_dates) - days]:
            del self.data[old_date]

    def summary(
        self, end_date: str, days: int = WEEK_DAYS
    ) -> tuple[int, float | None]:
        """计算截至 end_date 的最近 days 天窗口总盈亏。

        返回 (记录数, 总盈亏金额)：
        - 记录数 >= 2：总盈亏 = 末日仓库值 − 首日仓库值；
        - 记录数 == 1：总盈亏为该日仓库值（无对比对象，供视图提示「仅 1 条记录」）；
        - 记录数 == 0：总盈亏为 None。
        """
        records = [
            r for _, r in self.get_weekly_records(end_date, days) if r is not None
        ]
        if not records:
            return 0, None
        if len(records) == 1:
            return 1, records[0].warehouse
        return len(records), records[-1].warehouse - records[0].warehouse

    def export_csv(self) -> str:
        """生成 CSV 导出文本（列：日期/现金/仓库/较前日/收益率）。

        纯函数：只读 self.data，无副作用、不触碰 UI。记录按日期升序排列；
        「较前日」与「收益率」相对前一有记录日期计算，语义与表格/图表一致
        （较前日 = 当日仓库值 − 前一日仓库值，总收益 = 仓库价值已含现金）；
        无前日数据时对应单元格为 "—"。
        """
        lines = ["日期,现金,仓库,较前日,收益率"]
        prev_warehouse: float | None = None
        for date_str in sorted(self.data):
            record = self.get_record(date_str)
            if record is None:
                continue
            diff = (
                "—"
                if prev_warehouse is None
                else str(record.warehouse - prev_warehouse)
            )
            rate = self.calculate_rate(prev_warehouse, record.warehouse)
            rate_text, _ = self.format_rate(rate)
            lines.append(
                f"{date_str},{record.cash},{record.warehouse},{diff},{rate_text}"
            )
            prev_warehouse = record.warehouse
        return "\n".join(lines) + "\n"

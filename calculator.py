"""
业务逻辑：日期记录、最近历史查询、收益差值计算。
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from config import DATE_FORMAT, RETENTION_LIMIT, WEEK_DAYS
from formatting import format_money, format_short_date
from signals import PnLSignal, RateSignal

__all__ = [
    "DayRecord",
    "ProfitCalculatorLogic",
]


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DayRecord:
    """单日现金与仓库价值记录。

    现金是仓库价值的组成部分（现金 ⊆ 仓库），总收益 = 仓库价值。
    """

    cash: float
    warehouse: float
    date: str


class ProfitCalculatorLogic:
    """处理数据查询、历史对比与差值展示。"""

    def __init__(self, data: dict) -> None:
        """绑定数据：接受磁盘形态裸 dict 或已解析的 dict[str, DayRecord]。

        解析收敛到此处一次性完成（ADR-0001）：损坏/非法条目在加载时跳过，
        语义与原先 get_record 对非法条目返回 None 一致。
        """
        self.data: dict[str, DayRecord] = {}
        for date_str, raw in data.items():
            record = self._parse_record(date_str, raw)
            if record is not None:
                self.data[date_str] = record
            else:
                # 丢弃的条目不再随 serialize() 写回——下次保存会从磁盘清除（自愈），
                # 记 warning 使该行为可观测（O-01：不允许静默）。
                logger.warning("跳过损坏/非法记录（%s）", date_str)

    @staticmethod
    def _parse_record(date_str: str, raw: object) -> DayRecord | None:
        """把单条裸 dict 解析为 DayRecord；已是 DayRecord 直接返回，损坏/非法返回 None。"""
        if isinstance(raw, DayRecord):
            return raw
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

    def get_record(self, date_str: str) -> DayRecord | None:
        """读取某一天的记录；不存在时返回 None（非法条目已由加载时解析过滤）。"""
        return self.data.get(date_str)

    def save_record(self, date_str: str, cash: float, warehouse: float) -> DayRecord:
        """保存某日记录并返回对应模型。

        业务层不强制「现金 ⊆ 仓库」不变式（允许保留已录入的异常数据并继续展示），
        仅对违反不变式的写入记录 warning——拦截由 UI 层 save_today 负责（O-08）。
        存储前统一把现金/仓库四舍五入到 2 位小数（round 为银行家舍入），
        保证磁盘与视图金额一致。
        """
        rounded_cash = round(cash, 2)
        rounded_warehouse = round(warehouse, 2)
        if not self.is_cash_under_warehouse(rounded_cash, rounded_warehouse):
            logger.warning(
                "记录违反不变式（现金 %.2f > 仓库 %.2f，date=%s）",
                rounded_cash,
                rounded_warehouse,
                date_str,
            )
        record = DayRecord(
            cash=rounded_cash, warehouse=rounded_warehouse, date=date_str
        )
        self.data[date_str] = record
        return record

    @staticmethod
    def is_cash_under_warehouse(cash: float, warehouse: float) -> bool:
        """不变式判定：现金 ⊆ 仓库（仓库价值已含现金）。

        返回 True 表示不变式成立（cash ≤ warehouse），False 表示违反。
        唯一所有者（D-05）：save_record 告警 / save_today 拦截 / 输入框红框
        三处共用此判定，不再各自内联比较字面量。
        """
        return cash <= warehouse

    def serialize(self) -> dict[str, dict[str, float]]:
        """转换为磁盘持久化形态的裸 dict（`{"日期": {"cash": ..., "warehouse": ...}}`）。

        返回新 dict，与内部 data 断共享（ADR-0001）：调用方对返回值的修改
        不会影响只读的 logic 数据。
        """
        return {
            date_str: {"cash": record.cash, "warehouse": record.warehouse}
            for date_str, record in self.data.items()
        }

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

    def recent_records(self, days: int = WEEK_DAYS) -> list[tuple[str, "DayRecord"]]:
        """返回最近 days 条实际录入记录（按日期升序）。

        与 rotate_weekly 的保留语义一致：以「录入条数」而非日历天数为基准。
        间断录入（假期/出差）跨越多日时，仍展示最近 days 条录入记录，
        不因日历窗口丢弃仍保留在 data 中的老记录；无效/缺失字段的记录被跳过。
        """
        records: list[tuple[str, "DayRecord"]] = []
        for date_str in sorted(self.data):
            record = self.get_record(date_str)
            if record is not None:
                records.append((date_str, record))
        return records[-days:]

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

    @staticmethod
    def format_summary(
        count: int, total: float | None, days: int = WEEK_DAYS
    ) -> tuple[str, RateSignal]:
        """汇总标签展示文本的纯函数：按记录数与总盈亏返回 (文本, 信号)。

        与 summary() 语义对齐（录入条数基准）：
        - count == 0（total 为 None）：`最近N条总盈亏：数据不足`，信号 NONE；
        - count == 1：`最近N条总盈亏：¥X（仅 1 条记录）`，信号 NONE
          （仓库值非趋势，不加 + 前缀）；
        - count >= 2：复用 format_signed_money（带符号、趋势信号）。

        UI 层把信号映射为当前主题颜色（app.theme.signal_color），
        弱化/常规字号等纯样式留 UI（D-07）。
        """
        prefix = f"最近{days}条总盈亏："
        if total is None:
            return f"{prefix}数据不足", RateSignal.NONE
        if count == 1:
            return f"{prefix}{format_money(total)}（仅 1 条记录）", RateSignal.NONE
        total_text, total_signal = ProfitCalculatorLogic.format_signed_money(total)
        return f"{prefix}{total_text}", total_signal

    def cash_summary(self, days: int = WEEK_DAYS) -> tuple[int, float | None]:
        """计算最近 days 条实际录入记录的现金总变化。

        与 summary() 完全镜像、基于记录现金（cash）而非仓库值（warehouse）：
        反映窗口内「可支配现金」的净增减。

        返回 (记录数, 现金变化金额)：
        - 记录数 >= 2：现金变化 = 最新记录现金 − 最旧记录现金；
        - 记录数 == 1：现金变化为该条现金值（无对比对象，供视图提示「仅 1 条记录」）；
        - 记录数 == 0：现金变化为 None。
        """
        records = self.recent_records(days)
        if not records:
            return 0, None
        if len(records) == 1:
            return 1, records[0][1].cash
        return len(records), records[-1][1].cash - records[0][1].cash

    @staticmethod
    def format_cash_summary(
        count: int, total_delta: float | None, days: int = WEEK_DAYS
    ) -> tuple[str, RateSignal]:
        """现金汇总标签展示文本的纯函数：按记录数与现金变化返回 (文本, 信号)。

        与 format_summary() 完全镜像（录入条数基准；D-07 文本/样式分离）：
        - count == 0（total_delta 为 None）：`最近N条现金总变化：数据不足`，信号 NONE；
        - count == 1：`最近N条现金总变化：¥X（仅 1 条记录）`，信号 NONE
          （现金值非趋势，不加 + 前缀）；
        - count >= 2：复用 format_signed_money（带符号、趋势信号）。

        UI 层把信号映射为当前主题颜色（app.theme.signal_color）。
        """
        prefix = f"最近{days}条现金总变化："
        if total_delta is None:
            return f"{prefix}数据不足", RateSignal.NONE
        if count == 1:
            return f"{prefix}{format_money(total_delta)}（仅 1 条记录）", RateSignal.NONE
        total_text, total_signal = ProfitCalculatorLogic.format_signed_money(total_delta)
        return f"{prefix}{total_text}", total_signal

    @staticmethod
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

    def rotate_weekly(self, days: int = RETENTION_LIMIT) -> list[str]:
        """保留最近 days 条实际录入记录：数据条数超过 days 时删除最旧记录。

        以「录入条数」而非日历天数为基准（与 recent_records / summary 一致）：
        间断录入时，只要记录条数未超上限，较早日期的记录仍会保留。

        默认保留上限 = RETENTION_LIMIT（30，J 系列：存储与视图解耦，
        RETENTION_LIMIT 决定「最多保留」；视图 7/30 是独立筛窗，不影响存储）。
        满上限不删、超上限才删最旧（excess=len-days）。

        返回被删除的日期列表（升序）；删除时记录 info 日志，
        通常在调用方（save_today）在状态栏向用户提示（O-14）。
        """
        if len(self.data) <= days:
            return []
        sorted_dates = sorted(self.data.keys())
        deleted = sorted_dates[: len(sorted_dates) - days]
        for old_date in deleted:
            del self.data[old_date]
            logger.info("保留策略删除最旧记录（保留最近 %d 条）: %s", days, old_date)
        return deleted

    def summary(self, days: int = WEEK_DAYS) -> tuple[int, float | None]:
        """计算最近 days 条实际录入记录的总盈亏。

        与 recent_records / rotate_weekly 一致，以「录入条数」而非日历天数为基准。

        返回 (记录数, 总盈亏金额)：
        - 记录数 >= 2：总盈亏 = 最新记录仓库值 − 最旧记录仓库值；
        - 记录数 == 1：总盈亏为该条仓库值（无对比对象，供视图提示「仅 1 条记录」）；
        - 记录数 == 0：总盈亏为 None。
        """
        records = self.recent_records(days)
        if not records:
            return 0, None
        if len(records) == 1:
            return 1, records[0][1].warehouse
        return len(records), records[-1][1].warehouse - records[0][1].warehouse

    def export_csv(self) -> str:
        """生成 CSV 导出文本（列：日期/现金/仓库/较前日/收益率）。

        纯函数：只读 self.data，无副作用、不触碰 UI。记录按日期升序排列；
        「较前日」与「收益率」相对前一有记录日期计算，语义与表格/图表一致
        （较前日 = 当日仓库值 − 前一日仓库值，总收益 = 仓库价值已含现金）；
        无前日数据时对应单元格为 "—"。
        金额列统一走 format_money（含千分位与 K/M 缩写），与界面显示一致（O-11）；
        含逗号的字段经 csv 模块引号包裹，保证 Excel 正确分列。
        已知取舍（O-16 拍板：保持现状）：≥1e6 金额被缩写为 K/M、丢失全值精度，且金额单元格
        在 Excel 中为文本不可直接求和；如需机器可读全值应改用 CSV 专用纯数值格式。
        """
        buffer = io.StringIO()
        writer = csv.writer(buffer, lineterminator="\n")
        writer.writerow(["日期", "现金", "仓库", "较前日", "收益率"])
        prev_warehouse: float | None = None
        for date_str in sorted(self.data):
            record = self.get_record(date_str)
            if record is None:
                continue
            diff = (
                "—"
                if prev_warehouse is None
                else format_money(record.warehouse - prev_warehouse)
            )
            rate = self.calculate_rate(prev_warehouse, record.warehouse)
            rate_text, _ = self.format_rate(rate)
            writer.writerow(
                [
                    date_str,
                    format_money(record.cash),
                    format_money(record.warehouse),
                    diff,
                    rate_text,
                ]
            )
            prev_warehouse = record.warehouse
        return buffer.getvalue()

"""
业务逻辑：日期记录、最近历史查询、收益差值计算。
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
import calendar
from datetime import datetime, timedelta
from typing import Optional

from config import DATE_FORMAT, RETENTION_LIMIT, _WEEK_DAYS as WEEK_DAYS
from formatting import format_money

__all__ = [
    "BaseRecord",
    "DayRecord",
    "ProfitCalculatorLogic",
]


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BaseRecord:
    """基础记录：日期。所有记录类型的基类。"""

    date: str


@dataclass(frozen=True)
class DayRecord(BaseRecord):
    """单日现金与仓库价值记录。

    现金是仓库价值的组成部分（现金 ⊆ 仓库），总收益 = 仓库价值。
    """

    cash: float
    warehouse: float


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

    def _window_delta(self, days: int, attr: str) -> tuple[int, float | None]:
        """内部 helper：按字段名计算最近 days 条记录的窗口变化量。

        summary（warehouse）与 cash_summary（cash）的共享实现（#6 参数化）。
        """
        records = self.recent_records(days)
        if not records:
            return 0, None
        if len(records) == 1:
            return 1, getattr(records[0][1], attr)
        return len(records), getattr(records[-1][1], attr) - getattr(records[0][1], attr)

    def summary(self, days: int = WEEK_DAYS) -> tuple[int, float | None]:
        """计算最近 days 条实际录入记录的总盈亏（仓库值变化）。

        与 recent_records / rotate_weekly 一致，以「录入条数」而非日历天数为基准。

        返回 (记录数, 总盈亏金额)：
        - 记录数 >= 2：总盈亏 = 最新记录仓库值 − 最旧记录仓库值；
        - 记录数 == 1：总盈亏为该条仓库值（无对比对象，供视图提示「仅 1 条记录」）；
        - 记录数 == 0：总盈亏为 None。
        """
        return self._window_delta(days, "warehouse")

    def cash_summary(self, days: int = WEEK_DAYS) -> tuple[int, float | None]:
        """计算最近 days 条实际录入记录的现金总变化。

        与 summary() 镜像、基于记录现金（cash）而非仓库值（warehouse）：
        反映窗口内「可支配现金」的净增减。

        返回 (记录数, 现金变化金额)：
        - 记录数 >= 2：现金变化 = 最新记录现金 − 最旧记录现金；
        - 记录数 == 1：现金变化为该条现金值（无对比对象，供视图提示「仅 1 条记录」）；
        - 记录数 == 0：现金变化为 None。
        """
        return self._window_delta(days, "cash")

    def reuse_candidate(self, today: str) -> tuple[str, DayRecord, bool] | None:
        """查找今日可复用的候选记录。

        返回 (date_str, record, is_today_fallback) 三元组：
        - 今日已有记录 → 返回今日记录，is_today_fallback=False
        - 今日无记录但昨日有 → 返回昨日记录，is_today_fallback=False
        - 今日无记录且昨日也无 → 返回最近一条记录，is_today_fallback=True
        - 完全无数据 → None
        """
        today_record = self.get_record(today)
        if today_record is not None:
            return (today, today_record, False)

        result = self.last_record_before(today)
        if result is None:
            return None

        date_str, record = result
        try:
            yesterday = (
                datetime.strptime(today, DATE_FORMAT) - timedelta(days=1)
            ).strftime(DATE_FORMAT)
            is_today_fallback = date_str != yesterday
        except ValueError:
            is_today_fallback = True

        return (date_str, record, is_today_fallback)

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

        return self._window_delta(days, "warehouse")

    @staticmethod
    def import_csv(text: str) -> dict[str, dict[str, float]]:
        """从 CSV 文本解析数据，返回 {date: {cash, warehouse}} 格式的 dict。

        CSV 格式与 export_csv 输出一致：
        列顺序：日期,现金,仓库,较前日,收益率
        较前日和收益率列在导入时忽略（它们是由仓库值计算得出的派生列）。
        第一行为表头，跳过。
        金额列支持纯数字格式（含小数点）。
        日期列格式为 YYYY-MM-DD。

        返回空 dict 表示无数据。
        """
        reader = csv.reader(io.StringIO(text))
        data: dict[str, dict[str, float]] = {}
        for ri, row in enumerate(reader):
            if ri == 0:  # 跳过表头
                continue
            if len(row) < 3:
                continue
            date_str = row[0].strip()
            try:
                # 兼容 export_csv 可能含 ¥ 前缀与千分位逗号的可视化格式
                cash = float(row[1].replace("¥", "").replace(",", ""))
                warehouse = float(row[2].replace("¥", "").replace(",", ""))
            except (ValueError, IndexError):
                continue
            data[date_str] = {"cash": cash, "warehouse": warehouse}
        return data

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
            if rate is None:
                rate_text = "—"
            elif rate > 0:
                rate_text = f"+{rate:.1f}%"
            elif rate < 0:
                rate_text = f"{rate:.1f}%"
            else:
                rate_text = "0.0%"
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

    def summary_by_period(self, period: str) -> dict[str, dict]:
        """按时间周期（周/月/季/年）分组汇总。

        period 参数："week" | "month" | "quarter" | "year"

        返回 dict[str, dict]，key 为周期标识：
        - week: "2026-W30"
        - month: "2026-07"
        - quarter: "2026-Q3"
        - year: "2026"

        value 包含以下字段：
        - start_date: 周期内最早记录日期
        - end_date: 周期内最晚记录日期
        - opening_warehouse: 期初仓库值（最早记录）
        - closing_warehouse: 期末仓库值（最晚记录）
        - warehouse_change: 仓库变化（期末 - 期初）
        - opening_cash: 期初现金
        - closing_cash: 期末现金
        - cash_change: 现金变化
        - record_count: 记录条数

        无数据时返回空 dict。
        """
        if not self.data:
            return {}

        sorted_dates = sorted(self.data)
        groups: dict[str, list[DayRecord]] = {}

        for date_str in sorted_dates:
            record = self.data[date_str]
            dt = datetime.strptime(date_str, DATE_FORMAT)

            if period == "week":
                iso_year, iso_week, _ = dt.isocalendar()
                key = f"{iso_year}-W{iso_week:02d}"
            elif period == "month":
                key = dt.strftime("%Y-%m")
            elif period == "quarter":
                q = (dt.month - 1) // 3 + 1
                key = f"{dt.year}-Q{q}"
            elif period == "year":
                key = dt.strftime("%Y")
            else:
                raise ValueError(f"Unknown period: {period!r}")

            groups.setdefault(key, []).append(record)

        result: dict[str, dict] = {}
        for key, records in groups.items():
            first = records[0]
            last = records[-1]
            result[key] = {
                "start_date": first.date,
                "end_date": last.date,
                "opening_warehouse": first.warehouse,
                "closing_warehouse": last.warehouse,
                "warehouse_change": last.warehouse - first.warehouse,
                "opening_cash": first.cash,
                "closing_cash": last.cash,
                "cash_change": last.cash - first.cash,
                "record_count": len(records),
            }

        return result

    def generate_report(self, days: int = 7) -> str:
        """生成 HTML 格式报告，包含日期范围、汇总统计、数据表格。

        Args:
            days: 包含最近多少条记录（默认 7）。

        Returns:
            完整 HTML 字符串（自包含内联 CSS，无需外部文件）。
        """
        records = self.recent_records(days)
        if not records:
            return _build_empty_report()

        count, total_profit = self.summary(days)
        _, cash_change = self.cash_summary(days)

        # 日期范围
        start_date = records[0][0]
        end_date = records[-1][0]

        # 计算收益率
        first_warehouse = records[0][1].warehouse
        last_warehouse = records[-1][1].warehouse
        if first_warehouse != 0:
            overall_rate = (last_warehouse - first_warehouse) / first_warehouse * 100
        else:
            overall_rate = None

        # 生成表格行
        table_rows = ""
        prev_warehouse: float | None = None
        for date_str, record in records:
            diff = (
                "—"
                if prev_warehouse is None
                else format_money(record.warehouse - prev_warehouse)
            )
            rate = self.calculate_rate(prev_warehouse, record.warehouse)
            if rate is None:
                rate_text = "—"
            elif rate > 0:
                rate_text = f"+{rate:.1f}%"
            elif rate < 0:
                rate_text = f"{rate:.1f}%"
            else:
                rate_text = "0.0%"
            table_rows += (
                f"<tr>"
                f"<td>{date_str}</td>"
                f"<td>{format_money(record.cash)}</td>"
                f"<td>{format_money(record.warehouse)}</td>"
                f"<td>{diff}</td>"
                f"<td>{rate_text}</td>"
                f"</tr>\n"
            )
            prev_warehouse = record.warehouse

        total_profit_str = format_money(total_profit)
        cash_change_str = format_money(cash_change)
        rate_str = (
            "—"
            if overall_rate is None
            else f"{overall_rate:+.1f}%"
        )

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>收益报告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #333; background: #f5f7fa; padding: 20px; }}
.container {{ max-width: 900px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); padding: 24px; }}
h1 {{ font-size: 22px; color: #1a1a2e; margin-bottom: 4px; }}
.date-range {{ font-size: 14px; color: #888; margin-bottom: 20px; }}
.summary {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
.summary-card {{ flex: 1; min-width: 140px; background: #f0f4f8; border-radius: 6px; padding: 14px 16px; }}
.summary-card .label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
.summary-card .value {{ font-size: 20px; font-weight: 600; color: #1a1a2e; margin-top: 4px; }}
.summary-card .value.positive {{ color: #16a34a; }}
.summary-card .value.negative {{ color: #dc2626; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ background: #f0f4f8; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #888; padding: 10px 12px; text-align: right; }}
th:first-child {{ text-align: left; }}
td {{ padding: 10px 12px; border-bottom: 1px solid #eee; text-align: right; font-size: 14px; }}
td:first-child {{ text-align: left; font-family: "SF Mono", "Cascadia Code", "Consolas", monospace; font-size: 13px; color: #666; }}
tr:last-child td {{ border-bottom: none; }}
.positive {{ color: #16a34a; }}
.negative {{ color: #dc2626; }}
.footer {{ text-align: center; font-size: 11px; color: #bbb; margin-top: 20px; padding-top: 16px; border-top: 1px solid #eee; }}
@media (max-width: 600px) {{
.container {{ padding: 16px; }}
.summary {{ flex-direction: column; }}
.summary-card {{ min-width: auto; }}
}}
</style>
</head>
<body>
<div class="container">
<h1>收益报告</h1>
<p class="date-range">{start_date} ~ {end_date}（共 {count} 条记录）</p>
<div class="summary">
<div class="summary-card">
<div class="label">总盈亏</div>
<div class="value {('positive' if total_profit is not None and total_profit >= 0 else 'negative') if total_profit is not None else ''}">{total_profit_str}</div>
</div>
<div class="summary-card">
<div class="label">现金总变化</div>
<div class="value {('positive' if cash_change is not None and cash_change >= 0 else 'negative') if cash_change is not None else ''}">{cash_change_str}</div>
</div>
<div class="summary-card">
<div class="label">收益率</div>
<div class="value {('positive' if overall_rate is not None and overall_rate >= 0 else 'negative') if overall_rate is not None else ''}">{rate_str}</div>
</div>
</div>
<table>
<thead>
<tr><th>日期</th><th>现金</th><th>仓库</th><th>较前日</th><th>收益率</th></tr>
</thead>
<tbody>
{table_rows}</tbody>
</table>
<div class="footer">Profit Calculator &mdash; 自动生成报告</div>
</div>
</body>
</html>"""
        return html

    def export_html(self, path: str, days: int = 7) -> None:
        """将 HTML 报告写入文件。

        Args:
            path: 输出文件路径。
            days: 包含最近多少条记录（默认 7）。
        """
        html = self.generate_report(days)
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)


def _build_empty_report() -> str:
    """生成空数据报告的 HTML。"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>收益报告</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; color: #333; background: #f5f7fa; padding: 20px; }
.container { max-width: 900px; margin: 0 auto; background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.1); padding: 24px; text-align: center; }
h1 { font-size: 22px; color: #1a1a2e; margin-bottom: 8px; }
p { font-size: 14px; color: #888; }
.footer { text-align: center; font-size: 11px; color: #bbb; margin-top: 20px; padding-top: 16px; border-top: 1px solid #eee; }
</style>
</head>
<body>
<div class="container">
<h1>收益报告</h1>
<p>暂无数据，请先录入记录。</p>
<div class="footer">Profit Calculator &mdash; 自动生成报告</div>
</div>
</body>
</html>"""

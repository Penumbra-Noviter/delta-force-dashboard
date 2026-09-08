"""KPI 双磁贴渲染收敛（C4 块 2）：从 MainWindow 纠缠方法抽离为独立类。

KpiPresenter 注入 4 个 labels，对外三个出口：
- update(logic, view_n)：文本 + count-up 动画 + 样式全量渲染；
- apply_theme_styles(logic, view_n)：仅重算 signal 换色（C1-08 语义，
  不动文本/动画）；
- reset()：账号切换归零（Y-05——切换后数字直落终态，不做跨账号滚动动画）。

signal 判定走本模块私有 `_window_signal`（C2 深化）：它取
`presentation.format_window_text` 的信号分量，是本模块唯一耦合该元组形状
的地方——update 与 apply_theme_styles 共用它，两处判定不漂移（AA-01）。
此前该判定住在 `app.main_window._kpi_signal`，为绕 main_window ↔ 本模块
的循环导入而调用期延迟解析；归位后跨模块 import 与循环依赖一并消失。
"""

from __future__ import annotations

__all__ = ["KpiPresenter"]

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QLabel

from app.motion import animate_value, finish, stop
from app.theme import summary_style
from presentation import format_signed_money, format_window_text
from signals import RateSignal

if TYPE_CHECKING:
    # 仅类型标注用（零运行期 import；calculator 零 app 依赖，无循环导入）。
    from calculator import ProfitCalculatorLogic


def _window_signal(
    count: int, total: float | None, label: str, days: int
) -> RateSignal:
    """窗口汇总的信号分量（AA-01 单一来源，C2 归位于真正的消费者内部）。

    判定规则归 `presentation.format_window_text`（无数据/仅 1 条 → NONE，
    正/负/零 → POSITIVE/NEGATIVE/NEUTRAL）；本函数只把「取信号分量」这件事
    收成一行，update 与 apply_theme_styles 共用——presentation 的返回形状
    若变，只改这里一处。纯函数：同输入必同输出，可安全双调用。
    """
    return format_window_text(count, total, label, days)[1]


class KpiPresenter(QObject):
    """KPI 双磁贴（总盈亏 / 现金总变化）渲染器。

    count-up 动画的宿主是各磁贴 label 本身（C1 深化）：在途句柄归
    app.motion 的注册表，本类不再持有动画对象。

    Args:
        summary_label: 总盈亏磁贴大数字行。
        summary_caption: 总盈亏磁贴说明行。
        cash_summary_label: 现金总变化磁贴大数字行。
        cash_summary_caption: 现金总变化磁贴说明行。

    前置条件：4 个 label 必须互异——在途动画以 label 为注册表键
    （motion 侧），重复注入同一 label 会使两个磁贴共用一条在途动画。
    """

    def __init__(
        self,
        summary_label: QLabel,
        summary_caption: QLabel,
        cash_summary_label: QLabel,
        cash_summary_caption: QLabel,
    ) -> None:
        super().__init__()
        self._summary_label = summary_label
        self._summary_caption = summary_caption
        self._cash_summary_label = cash_summary_label
        self._cash_summary_caption = cash_summary_caption
        # W-01：count-up 上一帧数值（None = 尚未渲染过/数据不足）
        self._last_summary_total: float | None = None
        self._last_cash_delta: float | None = None

    def update(self, logic: ProfitCalculatorLogic, view_n: int) -> None:
        """双磁贴全量渲染（说明 + 大数字 + count-up + 信号色样式）。

        Args:
            logic: ProfitCalculatorLogic（summary / cash_summary 数据源，
                录入条数基准，随视图窗口联动）。
            view_n: 当前视图条数（7 / 30），决定汇总窗口与文本前缀。
        """
        count, total = logic.summary(view_n)
        self._last_summary_total = self._update_tile(
            count, total, "总盈亏", view_n,
            self._summary_caption, self._summary_label, self._last_summary_total,
        )
        cash_count, cash_delta = logic.cash_summary(view_n)
        self._last_cash_delta = self._update_tile(
            cash_count, cash_delta, "现金总变化", view_n,
            self._cash_summary_caption, self._cash_summary_label,
            self._last_cash_delta,
        )

    def apply_theme_styles(self, logic: ProfitCalculatorLogic, view_n: int) -> None:
        """仅重算两磁贴 signal 并重应用 summary_style（C1-08 E1）。

        纯内存读（logic.summary / cash_summary，零 I/O）；不动数值文本、
        不触发 count-up 动画——主题切换只换色。

        Args:
            logic: ProfitCalculatorLogic 数据源。
            view_n: 当前视图条数（7 / 30）。
        """
        count, total = logic.summary(view_n)
        self._summary_label.setStyleSheet(
            summary_style(_window_signal(count, total, "总盈亏", view_n))
        )
        cash_count, cash_delta = logic.cash_summary(view_n)
        self._cash_summary_label.setStyleSheet(
            summary_style(_window_signal(cash_count, cash_delta, "现金总变化", view_n))
        )

    def reset(self) -> None:
        """账号切换归零（Y-05）：清空上一帧数值并停掉在途动画。

        切换是数据源更换，随后的 update 数字直接落终态——不做
        「旧账号数值滚动到新账号数值」的误导动画。

        C1 深化：在途动画的丢弃与回收归 motion.stop（零帧、出表、
        deleteLater 一步不落）；本类只报「哪两个磁贴要归零」。
        """
        stop(self._summary_label)
        stop(self._cash_summary_label)
        self._last_summary_total = None
        self._last_cash_delta = None

    @staticmethod
    def _split_kpi_text(text: str) -> tuple[str, str]:
        """拆分汇总文本为 (说明, 数值)：`最近7条总盈亏：+¥41.0M` → 两段。

        U-01 磁贴化：说明行（小字）与数值行（大字）分居两个 QLabel；
        无分隔符时整体作说明，数值留空。
        """
        if "：" in text:
            caption, value = text.split("：", 1)
            return caption, value
        return text, ""

    def _update_tile(
        self,
        count: int,
        total: float | None,
        name: str,
        view_n: int,
        caption_label: QLabel,
        label: QLabel,
        last: float | None,
    ) -> float | None:
        """单磁贴全量渲染：文本拆分 + count-up 落值 + 信号色样式落地。

        Args:
            count / total: logic 汇总结果。
            name: 磁贴名（"总盈亏" / "现金总变化"）。
            view_n: 视图条数（文本前缀与 signal 判定共用）。
            caption_label: 说明行。
            label: 数值行。
            last: 上一帧数值（动画起点；None = 直落终态）。

        Returns:
            本次 total（调用方回存为下一帧的 last）。
        """
        signal = _window_signal(count, total, name, view_n)
        text, _ = format_window_text(count, total, name, view_n)
        caption, value = self._split_kpi_text(text)
        caption_label.setText(caption)
        self._set_kpi_value(label, value, last, total)
        label.setStyleSheet(summary_style(signal))
        return total

    def _set_kpi_value(
        self, label: QLabel, value: str, old: float | None, new: float | None
    ) -> None:
        """KPI 磁贴数字落值：数值变化时 count-up 滚动（W-01），否则直接设置。

        动画复用 format_signed_money 逐帧格式化，终态与直接设置完全一致。

        C4-债2 per-tile 独立动画（A1 根治）：在途动画以本磁贴 label 为
        注册表键（motion 侧），跨磁贴零触碰（双磁贴同帧动画互不截断）。

        C4-债2 落终路径 + C1 深化：任何落值入口先对本次磁贴 label 调
        ``motion.finish`` 优雅落终（旧动画终值先写到位），再按三条件
        （old != new 且均非 None 且 value != "数据不足"）决定是否播新
        count-up；不播则直落 setText（同调用内覆盖落终终帧，F1 终态不被
        残留帧改写）。

        C4-债3/5 的引用环雷区（finished 闭包捕获宿主 → 窗口销毁后迟到
        valueChanged 帧写已销毁 label → access violation）由 motion 统一
        处置：动画以 label 为 Qt parent（label 亡则动画亡），finished
        处理器 weakref 取宿主 + identity 检查。本类不再持有动画对象。
        """
        finish(label)
        if (
            old is not None
            and new is not None
            and old != new
            and value != "数据不足"
        ):
            if not animate_value(
                label,
                old,
                new,
                lambda v: label.setText(format_signed_money(v)[0]),
                duration_ms=300,
            ):
                label.setText(value)  # 动效关闭：直接落终态
        else:
            label.setText(value)

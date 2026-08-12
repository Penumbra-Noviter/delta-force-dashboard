"""KPI 双磁贴渲染收敛（C4 块 2）：从 MainWindow 纠缠方法抽离为独立类。

KpiPresenter 注入 4 个 labels，对外三个出口：
- update(logic, view_n)：文本 + count-up 动画 + 样式全量渲染；
- apply_theme_styles(logic, view_n)：仅重算 signal 换色（C1-08 语义，
  不动文本/动画）；
- reset()：账号切换归零（Y-05——切换后数字直落终态，不做跨账号滚动动画）。

signal 判定仍走 app.main_window._kpi_signal（AA-01 单一来源，函数本体
留在 main_window 不动）；因 main_window 模块加载期引用本模块，本模块
对 _kpi_signal 采用调用期延迟解析，规避循环导入。
"""

from __future__ import annotations

__all__ = ["KpiPresenter"]

from PySide6.QtCore import QAbstractAnimation, QObject
from PySide6.QtWidgets import QLabel

from app.motion import animate_value
from app.theme import summary_style
from presentation import format_signed_money, format_window_text
from signals import RateSignal


def _kpi_signal(
    count: int, total: float | None, label: str, days: int
) -> RateSignal:
    """延迟解析 app.main_window._kpi_signal（AA-01 单一来源）。

    main_window 在模块加载期 import 本模块（KpiPresenter 构造），此刻其
    模块内 _kpi_signal 尚未定义，不能在模块顶层 from-import；调用发生在
    main_window 完整加载之后（MainWindow.__init__ → presenter.update），
    此处调用期导入安全。
    """
    from app.main_window import _kpi_signal as impl

    return impl(count, total, label, days)


class KpiPresenter(QObject):
    """KPI 双磁贴（总盈亏 / 现金总变化）渲染器。

    继承 QObject：animate_value 的动画对象以 self 为 Qt parent（防 GC），
    与旧 MainWindow 持有动画的语义一致。

    Args:
        summary_label: 总盈亏磁贴大数字行。
        summary_caption: 总盈亏磁贴说明行。
        cash_summary_label: 现金总变化磁贴大数字行。
        cash_summary_caption: 现金总变化磁贴说明行。
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
        # C4-债2 per-tile 独立动画槽：label → 在途动画，键恒为动画目标磁贴。
        # 动画对象挂 presenter 防 GC；自然结束的 Stopped entry 残留不清理
        # （有界 0 ≤ len ≤ 2，Q2 定案——下次同磁贴落值 / reset 时回收）。
        self._countup_anims: dict[QLabel, QAbstractAnimation] = {}

    def update(self, logic, view_n: int) -> None:
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

    def apply_theme_styles(self, logic, view_n: int) -> None:
        """仅重算两磁贴 signal 并重应用 summary_style（C1-08 E1）。

        纯内存读（logic.summary / cash_summary，零 I/O）；不动数值文本、
        不触发 count-up 动画——主题切换只换色。

        Args:
            logic: ProfitCalculatorLogic 数据源。
            view_n: 当前视图条数（7 / 30）。
        """
        count, total = logic.summary(view_n)
        self._summary_label.setStyleSheet(
            summary_style(_kpi_signal(count, total, "总盈亏", view_n))
        )
        cash_count, cash_delta = logic.cash_summary(view_n)
        self._cash_summary_label.setStyleSheet(
            summary_style(_kpi_signal(cash_count, cash_delta, "现金总变化", view_n))
        )

    def reset(self) -> None:
        """账号切换归零（Y-05）：清空上一帧数值并停掉在途动画。

        切换是数据源更换，随后的 update 数字直接落终态——不做
        「旧账号数值滚动到新账号数值」的误导动画。
        """
        for anim in self._countup_anims.values():
            anim.stop()
        self._countup_anims.clear()
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
        signal = _kpi_signal(count, total, name, view_n)
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

        动画复用 format_signed_money 逐帧格式化，终态与直接设置完全一致；
        动画对象挂 presenter 防 GC。

        C4-债2 per-tile 独立动画槽（A1 根治）：任何落值入口（动画分支或
        直落分支）先按本次磁贴 label 弹出旧动画并统一 setCurrentTime(duration())
        优雅落终——同磁贴重触发与直落共用同一落终路径，跨磁贴零触碰
        （双磁贴同帧动画互不截断）。动画触发三条件（old != new 且均非
        None 且 value != "数据不足"）满足时新动画写入本磁贴键位，否则
        直落 setText（同调用内覆盖落终终帧，F1 终态不被残留帧改写）。
        """
        prev = self._countup_anims.pop(label, None)
        if prev is not None:
            prev.setCurrentTime(prev.duration())
        if (
            old is not None
            and new is not None
            and old != new
            and value != "数据不足"
        ):
            anim = animate_value(
                self,
                old,
                new,
                lambda v: label.setText(format_signed_money(v)[0]),
                duration_ms=300,
            )
            if anim is not None:
                self._countup_anims[label] = anim
        else:
            label.setText(value)

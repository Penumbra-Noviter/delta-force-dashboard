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

import weakref
from typing import TYPE_CHECKING

from PySide6.QtCore import QAbstractAnimation, QObject
from PySide6.QtWidgets import QLabel

from app.motion import animate_value
from app.theme import summary_style
from presentation import format_signed_money, format_window_text
from signals import RateSignal

if TYPE_CHECKING:
    # 仅类型标注用（零运行期 import；calculator 零 app 依赖，无循环导入）。
    from calculator import ProfitCalculatorLogic


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

    前置条件：4 个 label 必须互异——per-tile 动画槽以 label 为键
    （_countup_anims），重复注入同一 label 会使多槽位共享一个键位、
    动画寻址失效。
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
        # 自然结束 → finished → entry 移除 + deleteLater（C4-债3）——dict
        # 与 Qt children 双双有界（0 ≤ len ≤ 2）。
        self._countup_anims: dict[QLabel, QAbstractAnimation] = {}

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

        C4-债3：在途动画显式 stop + deleteLater 回收（stop 不发 finished
        → deleteLater 必须显式）。引用环由 finished 闭包的 weakref 持有
        破除（见 _set_kpi_value docstring 雷区说明）——本方法负责显式
        回收：不调 reset 直接销毁 presenter 的路径（如测试 fixture 之外
        的持有者）会留下 Stopped 动画静默泄漏（有环但无触发路径，不崩）。
        """
        for anim in self._countup_anims.values():
            anim.stop()
            anim.deleteLater()  # stop 不发 finished → 必须显式回收
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

        C4-债3 生命周期收敛：新动画连接 finished → _pop_countup_anim——
        自然结束 → finished → entry 移除 + deleteLater。落终路径（pop +
        setCurrentTime(duration()) 同步触发 finished）时 entry 已弹出 →
        handler no-op，旧动画由本入口显式 deleteLater 回收（两次 pop
        安全）。

        引用环雷区：finished 闭包捕获 presenter 会形成引用环（动画 ←
        信号连接 ← 闭包 ← presenter）——若窗口销毁（未 reset）时环不破，
        presenter 与在途动画存活，动画迟到 valueChanged 帧会写已销毁的
        label（access violation）。闭包以 weakref 持有 presenter 破环：
        presenter 失去唯一强引用（窗口 GC）即随 C++ 树销毁、动画随父
        销毁、连接随对象销毁，无迟到触发；直接持有 presenter 的路径
        （测试 fixture）仍必须先 stop 在途动画（reset）再冲刷 deleteLater
        ——reset 显式回收是 children 归零的唯一通道，stop 不发 finished
        → deleteLater 必须显式。Stopped 动画静默泄漏不崩。
        """
        prev = self._countup_anims.pop(label, None)
        if prev is not None:
            prev.setCurrentTime(prev.duration())
            # C4-债3：落终路径 finished 同步触发时 entry 已被 pop →
            # handler no-op，此处显式回收旧动画（自然结束路径由
            # _pop_countup_anim 回收）。
            prev.deleteLater()
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
                # C4-债3：自然结束 → finished → 回收链（entry 移除 + deleteLater）。
                # 闭包以 weakref 持有 presenter 破引用环（见 docstring 雷区说明）
                # ——窗口销毁时 presenter 失强引用即随 C++ 树销毁，动画与连接
                # 随之消亡，无迟到触发。
                owner = weakref.ref(self)

                def _on_finished() -> None:
                    presenter = owner()
                    if presenter is not None:
                        presenter._pop_countup_anim(label, anim)

                anim.finished.connect(_on_finished)
        else:
            label.setText(value)

    def _pop_countup_anim(self, label: QLabel, anim: QAbstractAnimation) -> None:
        """finished 后回收动画：从在途映射移除 entry + deleteLater。

        identity 检查（``get(label) is anim``）保证同步/异步 finished 均无
        竞争：落终路径下 finished 同步触发时 entry 已被弹出 → no-op；
        若槽内已是更新的动画（同磁贴再触发后旧动画迟到 finish）→ 不误删
        新 entry。
        """
        if self._countup_anims.get(label) is anim:
            self._countup_anims.pop(label, None)
            anim.deleteLater()

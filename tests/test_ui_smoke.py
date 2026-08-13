"""
C5 迁移：verify_all.py 的 UI 烟测并入 pytest（offscreen）。

verify_all.py 原第 1~3、12 节为纯逻辑叶子测试，已被 tests/test_calculator.py、
tests/test_formatting.py、tests/test_data_store.py 覆盖，不在此迁移。
本文件承接原第 4~11、13~14 节 UI 烟测（verify_all 共 14 节）：
- 启动/渲染、保存、编辑、删除（mock 确认框）、主题切换、窗口置顶、
  设置持久化、几何恢复、输入校验联动、快捷键绑定。
- 所有 MainWindow 构造注入临时 store/logic，不触碰真实 data.json / settings.json
  （参照 tests/test_input_panel.py 的 main_window + settings_guard 模式）。

迁移原则（C5）：C4 已造真 seam，测试尽可能走公开 API 与公开信号
（fill_values / set_edit_mode / delete_requested / theme_btn.click 等），
不再调用私有 _start_edit；仅校验非法输入（fill_values 只接受数值）等
无公开 seam 处仍直取输入框。
- 失焦格式化 / 聚焦反格式化 / 失焦立即校验已随 D-04 收敛到
  tests/test_input_panel.py 的 shown_panel 真实焦点链路。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFileDialog, QMessageBox

from calculator import ProfitCalculatorLogic
from config import DATE_FORMAT
from data_store import DataStore

__all__ = []


# ── 样本数据（与 verify_all.make_sample_data 等价）──────


def make_sample_data() -> dict:
    """创建 6 天样本数据（相对今天生成，含两天间断缺口）。

    原 verify_all 用固定日期（2026-07-20~27）；迁移后改为相对今天生成，
    避免样本日与墙钟耦合导致断言必然失败（时间耦合回归）。
    """
    today = datetime.now()
    offsets = (7, 6, 5, 3, 2, 0)  # 与原 6 天间隔（含两天缺口）一致
    values = [
        (54360000.0, 419900000.0),  # 最旧
        (52340000.0, 419800000.0),
        (58155000.0, 427400000.0),
        (80088000.0, 447900000.0),
        (82514000.0, 450200000.0),
        (88541000.0, 460900000.0),  # 今天
    ]
    return {
        (today - timedelta(days=off)).strftime(DATE_FORMAT): {
            "cash": cash,
            "warehouse": warehouse,
        }
        for off, (cash, warehouse) in zip(offsets, values)
    }


# ── fixtures（qapp / settings_guard 见 tests/conftest.py）──


@pytest.fixture
def sample_window(qapp, settings_guard, tmp_path):
    """带样本数据的 MainWindow（不触碰真实 data.json / settings.json）。

    C2-03：构造注入 stub client——利润页懒加载/预加载零真实网络
    （不再依赖 offscreen 哨兵）。
    """
    from app.main_window import MainWindow
    from tests.conftest import make_stub_client

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
        client=make_stub_client(),
    )
    yield win
    win.close()


# ── 4. UI 启动 & 渲染 ────────────────────────────────────


def test_ui_initialization(sample_window):
    """UI 启动无 crash + 基础渲染。"""
    win = sample_window

    # 基本属性
    assert win.windowTitle() == "Delta Force Dashboard"
    # 最小窗口随布局收紧（O 系列后下调）：图表封顶 + 表格获得更多纵向空间
    assert win.minimumWidth() >= 560 and win.minimumHeight() >= 650

    # 子组件存在
    assert hasattr(win, "input_panel")
    assert hasattr(win, "table")
    assert hasattr(win, "chart")

    # 输入面板
    ip = win.input_panel
    assert hasattr(ip, "cash_entry")
    assert hasattr(ip, "warehouse_entry")
    assert hasattr(ip, "save_btn")

    # 表格列数 = 7
    assert win.table.columnCount() == 7

    # 初始有样本数据（recent_records 返回全部实际录入记录，无空位占位）
    records = win.logic.recent_records(7)
    present = [d for d, _ in records]
    assert len(present) > 0

    # 表格 / 图表 draw 无 crash
    win.table.draw(records, win.today)
    win.chart.draw(records)

    # 7 列表头名称（双栏同构，使用左表验证）
    headers = [
        win.table._left_table.horizontalHeaderItem(i).text() for i in range(7)
    ]
    expected = ["日期", "现金", "仓库（总收益）", "较前日", "收益率", "盈亏", "操作"]
    assert headers == expected

    # 盈亏标签单元格
    pnl_widget = win.table._left_table.cellWidget(0, 5)
    assert pnl_widget is not None


def test_kpi_tile_splits_caption_and_value(qapp):
    """U-01：汇总文本拆为「说明行 + 数值行」，磁贴数字为大字号信号色。

    C4 块 2：文本拆分语义随 _split_kpi_text 收敛到 KpiPresenter，直测 presenter。
    """
    from signals import RateSignal

    from PySide6.QtWidgets import QLabel

    from app.kpi_presenter import KpiPresenter
    from app.theme import get_color, summary_style

    presenter = KpiPresenter(QLabel(), QLabel(), QLabel(), QLabel())

    caption, value = presenter._split_kpi_text("最近7条总盈亏：+¥41.0M")
    assert caption == "最近7条总盈亏"
    assert value == "+¥41.0M"
    # 无分隔符（兜底）→ 整体作说明，数值留空
    assert presenter._split_kpi_text("数据不足") == ("数据不足", "")

    # 磁贴数字样式：正常态 22px 信号色；数据不足态 16px 灰字
    style = summary_style(RateSignal.POSITIVE)
    assert "font-size: 22px" in style
    assert get_color("FG_POS") in style
    none_style = summary_style(RateSignal.NONE)
    assert "font-size: 16px" in none_style


def test_u02_type_scale(sample_window):
    """U-02：按钮两级（primary 13 / secondary 11）、页面标题分层、图表弹性翻转。"""
    from app.theme import generate_qss

    win = sample_window
    qss = generate_qss("light")

    # 按钮两级：全局默认（secondary）11px；primary 13px/600（saveBtn/queryBtn）
    assert "font-size: 11px" in qss
    assert "font-size: 13px" in qss
    btn_block = qss.split(
        "QPushButton#themeBtn, QPushButton#pinBtn, QPushButton#exportBtn"
    )[1][:400]
    assert "font-size: 11px" in btn_block  # 底部三按钮不再 10px 游离档

    # 页面标题独立档位（16px），与应用名 titleLabel（18px）分层
    assert "QLabel#pageTitleLabel" in qss
    assert "font-size: 16px" in qss

    # 图表高度随屏幕自适应档位（U-09 方案 A）：与窗口实际使用的区间一致
    assert win.chart.minimumHeight() == win._chart_min_h
    assert win.chart.maximumHeight() == win._chart_max_h

    # 表格固定行高 26px（30 天 15+15 行全量展示的关键参数）
    assert win.table._left_table.rowHeight(0) == 26


def test_startup_preloads_both_profit_pages(qapp, settings_guard, tmp_path):
    """U-10：启动 500ms 定时器后制造产物 + 兑换利润均后台预加载（点击零卡顿）。

    C2-03：构造注入带数据的 stub client——预加载走真实后台线程，
    线程内立即返回伪造数据，零真实网络。
    """
    import time

    from PySide6.QtTest import QTest

    from app.main_window import MainWindow
    from calculator import ProfitCalculatorLogic
    from data_store import DataStore
    from kkrb_client import AmmoPackageItem, CraftingProduct
    from tests.conftest import make_stub_client

    win = MainWindow(
        store=DataStore(tmp_path / "d.json", tmp_path / "d.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
        client=make_stub_client(
            ov_impl=lambda: [CraftingProduct("技术中心", "复合弓", 100, 200, "晚上8点")],
            ammo_impl=lambda: [
                AmmoPackageItem("3级子弹自选包", "5.7mm", 3, 40, 100, 4000, 500)
            ],
        ),
    )
    win.show()

    # 轮询等待两个页面预加载完成（固定 qWait 时长与后台线程调度存在竞态）
    def wait_loaded(page, timeout_ms: int = 5000) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            QTest.qWait(50)
            qapp.processEvents()
            if page.is_loaded:
                return True
        return False

    assert wait_loaded(win.profit_page.crafting_page)
    assert wait_loaded(win.profit_page.exchange_page)
    win.close()


def test_page_switch_loop_no_crash(sample_window):
    """U-11 回归：点利润 → 切回记账 → 再点利润 反复 20 次不崩溃。

    用户报告此操作序列闪退（根因：切页淡入的 QGraphicsOpacityEffect 挂
    QStackedWidget 页面，快速 hide/show 触发 Qt 崩溃路径——已移除切页动画）。
    """
    from PySide6.QtTest import QTest

    win = sample_window
    win.show()
    QTest.qWait(100)

    for i in range(20):
        win.sidebar.set_current_index(1)  # 利润
        QTest.qWait(30)
        win.sidebar.set_current_index(0)  # 记账
        QTest.qWait(30)
    QTest.qWait(200)
    # 存活即通过（崩溃会直接终止进程）；再确认页面仍可切换
    win.sidebar.set_current_index(1)
    QTest.qWait(50)
    assert win._stack.currentIndex() == 1


def test_w01_kpi_countup(qapp):
    """W-01：KPI 数值变化时 count-up 动画触发，结束后落新值；数值未变直接设置。

    C4 块 2：count-up 逻辑随 _set_kpi_value 收敛到 KpiPresenter，直测 presenter。
    """
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QFrame, QLabel

    from app import motion
    from app.kpi_presenter import KpiPresenter
    from presentation import format_signed_money

    class _Logic:
        """单磁贴可编程 logic（总盈亏侧驱动动画，现金侧不干扰）。"""

        def __init__(self, total: float) -> None:
            self._total = total

        def summary(self, view_n: int) -> tuple[int, float]:
            return 2, self._total

        def cash_summary(self, view_n: int) -> tuple[int, float]:
            return 2, self._total

    presenter = KpiPresenter(QLabel(), QLabel(), QLabel(), QLabel())
    label = presenter._summary_label

    logic = _Logic(100.0)
    presenter.update(logic, 7)  # 首帧（last=None）直落终态
    assert label.text() == format_signed_money(100.0)[0]

    # 数值变化（100 → 200）→ 动画触发，结束后文本 == 新值格式化
    logic._total = 200.0
    presenter.update(logic, 7)
    assert label in presenter._countup_anims
    QTest.qWait(400)
    assert label.text() == format_signed_money(200.0)[0]

    # 数值未变 → 直接设置，文本保持终态
    presenter.update(logic, 7)
    assert label.text() == format_signed_money(200.0)[0]

    # 动效关闭 → animate_value 直接落终态
    motion.set_animations_enabled(False)
    try:
        seen: list[float] = []
        anim = motion.animate_value(QFrame(), 10.0, 20.0, seen.append)
        assert anim is None
        assert seen == [20.0]
    finally:
        motion.set_animations_enabled(True)


def test_w04_chart_hover_markers(sample_window):
    """W-04：图表创建后 hover 高亮标记就位（仓库/现金各一，13px 大圆点）。"""
    win = sample_window
    records = win.logic.recent_records(7)
    win.chart.draw(records)

    assert len(win.chart._hover_markers) == 2
    for marker in win.chart._hover_markers:
        assert marker.opts["size"] == 13
        assert marker.opts["symbol"] == "o"

    # 主题切换标记描边色更新不崩（apply_theme 路径覆盖）
    win._toggle_theme()
    win._toggle_theme()


def test_window_preset_screen_adaptive(qapp):
    """U-09 方案 A：屏幕可用高度 → (窗口宽, 窗口高, 图表区间) 两档自适应。"""
    from app.main_window import MainWindow

    assert MainWindow._window_preset(1200) == (820, 1020, 160, 240)  # 1080p 大档
    assert MainWindow._window_preset(1000) == (820, 1020, 160, 240)  # 边界含 1000
    assert MainWindow._window_preset(999) == (820, 920, 140, 150)    # 小屏紧凑档
    assert MainWindow._window_preset(0) == (820, 920, 140, 150)      # 无屏幕兜底


def test_u04_sidebar_selection_pill(sample_window):
    """U-04：侧边栏 130px；选中态为浅底 pill + 3px accent 指示条（非实心色块）。"""
    win = sample_window
    assert win.sidebar.width() == 130

    style = win.sidebar.styleSheet()
    # 选中态：浅底 pill + border-left 指示条（transparent 占位保证零位移）
    assert "border-left: 3px solid transparent" in style
    assert "border-left: 3px solid" in style.split("::item:selected")[1][:200]
    # 不再整条实心 BTN_BG 填充（旧样式已移除）
    assert "item:selected" in style


def test_ic_emoji_free_and_icon_single_source(sample_window):
    """IC 系列（ADR-0006）：app/ 零彩色 emoji 字面量；图标收敛 icons.ICONS。

    原 U-05 守卫（ui_text.EMOJI 单一来源 + 字体族）随 ui_text.py 退役迁移：
    - 彩色 emoji / emoji 变体选择符（FE0F）禁止散落（图标已 SVG 化）；
    - BMP 文本符号（✓ U+2713 / ⚠ U+26A0 / ⟳ U+27F3）允许（文案语义，
      presentation.py 同款，ADR-0006 边界）；
    - 图标装配断言：导航双态 icon + 按钮 icon 非空（apply_theme 已跑）。
    """
    import pathlib
    import re

    win = sample_window

    # 文案层：导航/按钮为纯文本（图标走 QIcon，不拼进文案）
    assert win.sidebar.NAV_ITEMS == ["记账", "利润", "密码门"]
    assert win.sidebar.pin_btn.text() == "置顶"
    assert win.sidebar.new_account_btn.text() == "新建账号"
    assert win.sidebar.account_title.text() == "账号"
    assert win.sidebar.theme_btn.text() in ("暗色", "亮色")

    # 图标装配（sample_window 构造已触发 apply_theme，C1-08 启动期一次）
    for item in win.sidebar._nav_items:
        assert not item.icon().isNull()
    assert not win.sidebar.pin_btn.icon().isNull()
    assert not win.sidebar.new_account_btn.icon().isNull()
    assert not win.sidebar.theme_btn.icon().isNull()

    # app 源码零彩色 emoji / FE0F 变体字面量
    # （BMP 文本符号 ✓⚠⟳ 不在范围——文案语义，保留）
    literal = re.compile(r"[\U0001F000-\U0001FAFF\uFE0F]")
    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    for py in app_dir.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        assert not literal.search(text), f"{py.name} 含 emoji 字面量"


def test_u06_motion_feedback(sample_window):
    """U-06：曲线绘制动画触发 + fade_in_widget 契约（effect 移除、竞态安全）。

    注：页面切换淡入已移除（QStackedWidget + QGraphicsOpacityEffect 快速切页
    崩溃风险，U-11）；曲线与保存指示动画保留。
    """
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QFrame

    from app.motion import fade_in_widget

    win = sample_window
    win.show()
    QTest.qWait(50)

    # 曲线绘制动画：draw 后启动，完成后 opacity 归 1
    records = win.logic.recent_records(7)
    win.chart.draw(records)
    assert win.chart._draw_anim is not None
    QTest.qWait(400)
    if win.chart._warehouse_curve is not None:
        assert win.chart._warehouse_curve.opacity() == 1.0

    # fade_in_widget 契约：结束后移除 QGraphicsOpacityEffect 且 property 清空
    box = QFrame()
    fade_in_widget(box, duration_ms=50)
    QTest.qWait(120)
    assert box.graphicsEffect() is None
    assert box.property("_fade_anim") is None


def test_u06_fade_in_widget_consecutive_contract(qapp):
    """C4-债6：连续 fade 契约保持——在途二次 fade 停旧覆盖新，排水后清零。

    诚实声明：本测为契约保持而非红绿反证——同调用内 setProperty 覆盖使
    「stop 后 property 残留已删指针」在外部不可观察（读路径要么旧指针要么
    新动画），在途销毁路径当前亦不崩；修复前后行为等价。修复为防御性/
    一致性加固（C4-债3/5 定案：weakref 破环 + stop 后同步清 property），
    本测锁定可观察契约：在途二次触发 → 排水后 effect/property 清零、无崩溃。
    """
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QFrame

    from app import motion
    from app.motion import fade_in_widget

    prev = motion.animations_enabled()
    motion.set_animations_enabled(True)
    try:
        box = QFrame()
        fade_in_widget(box, 50)
        QTest.qWait(20)  # 在途
        fade_in_widget(box, 50)  # stop 旧动画 + 覆盖新动画
        QTest.qWait(150)  # 排水：新动画自然结束 + DWS 自删 + finished 清理
        assert box.property("_fade_anim") is None
        assert box.graphicsEffect() is None
        # 存活即通过（在途连续触发无崩溃）
    finally:
        motion.set_animations_enabled(prev)


def test_u06_fade_in_widget_zero_duration_guard(qapp):
    """C4-债9：fade_in_widget duration_ms<=0 护栏（反证锚点 0 + Falsify 负值边界）。

    修复前 duration_ms 直接透传 setDuration：duration=0 时 QPropertyAnimation
    start 即 Stopped、finished 不触发，DWS 已删 C++ 对象但 _fade_anim property
    残留悬空 wrapper——对返回值调任何方法抛 RuntimeError（红）；max(1, ...)
    护栏后返回有效动画对象，排水后 property/graphicsEffect 收敛 None 无崩溃
    （绿）。时长 1ms 的动画极快自然结束，不断言具体状态值，只断言语义
    「有效动画 + 最终收敛」。
    """
    from PySide6.QtCore import QAbstractAnimation
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QFrame

    from app import motion
    from app.motion import fade_in_widget

    prev = motion.animations_enabled()
    motion.set_animations_enabled(True)
    try:
        for duration in (0, -1):
            box = QFrame()
            anim = fade_in_widget(box, duration_ms=duration)
            # 修复前此行抛 RuntimeError（start 即 Stopped + finished 不触发 +
            # DWS 已删 C++ 对象）；护栏后为有效动画（启动瞬间 Running/Stopped
            # 均合法，不按时序断言）
            assert anim is not None
            assert anim.state() in (
                QAbstractAnimation.State.Running,
                QAbstractAnimation.State.Stopped,
            )
            assert box.property("_fade_anim") is not None
            QTest.qWait(200)  # 排水：1ms 动画极快自然结束 + DWS 自删 + finished 清理
            assert box.property("_fade_anim") is None
            assert box.graphicsEffect() is None
    finally:
        motion.set_animations_enabled(prev)


def test_u06_draw_anim_bounded_lifecycle(sample_window):
    """C4-债4 AC-1：15 次连续 draw → qWait(400) → chart 零 QVariantAnimation 残留。

    旧实现每次 draw 覆盖 _draw_anim 不回收旧动画，16 次 draw 残留 16 个动画
    子对象（反证锚点）；修复后 stop + deleteLater + finished 自回收，归零。
    必须按 QVariantAnimation 类型过滤——chart 有 PlotWidget 等常驻子控件。
    """
    from PySide6.QtCore import QVariantAnimation
    from PySide6.QtTest import QTest

    from app.chart_widget import ChartWidget

    win = sample_window
    records = win.logic.recent_records(7)
    # 用全新 ChartWidget：MainWindow 构造期已 draw 过一次（旧实现遗留永不
    # 回收），计数锚点（16 / 2）须在无历史残留的 chart 上复现，且不随构造
    # 时机漂移
    chart = ChartWidget()
    chart.draw(records)
    for _ in range(15):
        chart.draw(records)
    QTest.qWait(400)
    assert sum(
        isinstance(c, QVariantAnimation) for c in chart.children()
    ) == 0
    # U-5：动画自然结束后句柄复位 None（不再残留 Stopped 动画引用）
    assert chart._draw_anim is None


def test_u06_draw_anim_race_single_running(sample_window):
    """C4-债4 AC-2：动画半程二次 draw → 立即 Running 动画数 == 1。

    旧实现旧动画不 stop，二次 draw 后同目标两条动画竞争写 opacity
    （可见 0.88→0.20 抖动）；修复后旧动画被 stop（零帧零 finished），
    只余新动画 Running（现状=2、修复=1，不依赖采样时序）。
    """
    from PySide6.QtCore import QAbstractAnimation, QVariantAnimation
    from PySide6.QtTest import QTest

    from app.chart_widget import ChartWidget

    win = sample_window
    records = win.logic.recent_records(7)
    chart = ChartWidget()  # 同 AC-1：全新 chart 复现锚点，不随构造时机漂移
    chart.draw(records)
    QTest.qWait(100)  # 动画半程（200ms 时长）
    chart.draw(records)
    running = sum(
        isinstance(c, QVariantAnimation)
        and c.state() == QAbstractAnimation.State.Running
        for c in chart.children()
    )
    assert running == 1
    # 排水等待：断言已完成，qWait 让在途动画自然结束、deleteLater 全部处理，
    # 避免 chart 局部变量随测试结束被 Python GC 时残留待删动画子对象
    # （PySide6 会延迟双重删除导致后续事件循环 abort）
    QTest.qWait(400)


def test_u06_draw_anim_final_state_and_switch_off(sample_window):
    """C4-债4 AC-3/AC-4：动画结束 opacity==1.0；关闭动效时零动画对象 + 句柄 None。

    AC-4 用全新 ChartWidget 验证——sample_window 的 chart 在 MainWindow 构造期
    已被 draw 过（旧实现遗留动画永不回收），「无动画对象」须在无历史残留的
    chart 上断言才能证明该次 draw 本身零产生。
    """
    from PySide6.QtCore import QVariantAnimation
    from PySide6.QtTest import QTest

    from app import motion
    from app.chart_widget import ChartWidget

    win = sample_window
    records = win.logic.recent_records(7)

    # AC-4：全局动效关闭 → draw 仍立即完整显示，零动画对象、句柄 None
    chart = ChartWidget()
    motion.set_animations_enabled(False)
    try:
        chart.draw(records)
        assert chart._draw_anim is None
        assert sum(
            isinstance(c, QVariantAnimation) for c in chart.children()
        ) == 0
        if chart._warehouse_curve is not None:
            assert chart._warehouse_curve.opacity() == 1.0
    finally:
        motion.set_animations_enabled(True)

    # AC-3：启用路径动画结束 → opacity 归 1（0→1 揭示 200ms 语义不变）
    win.chart.draw(records)
    QTest.qWait(400)
    if win.chart._warehouse_curve is not None:
        assert win.chart._warehouse_curve.opacity() == 1.0


def test_u06_clear_all_stops_running_draw_anim(sample_window):
    """C4-债5 AC-1：动画半程 _clear_all → 在途动画停止、句柄复位 None。

    旧实现 _clear_all 不停止在途 _draw_anim（依赖 ≤200ms 自然回收 + 闭包
    判空），清空后句柄仍指向 Running 动画（反证锚点）；加固后先 stop +
    deleteLater + 句柄复位，清空立即收敛（stop 零帧零 finished——on_finished
    不被触发，句柄必须手动复位）。
    """
    from PySide6.QtCore import QAbstractAnimation
    from PySide6.QtTest import QTest

    from app import motion
    from app.chart_widget import ChartWidget

    win = sample_window
    records = win.logic.recent_records(7)
    # C4-债8：环境态自持——本用例依赖动效开启（Running 断言），显式置开 +
    # try/finally 恢复（同 test_u06_motion_global_switch 惯例；关闭态下
    # _draw_anim 为 None，Running 断言会 AttributeError，历史红证）。
    prev = motion.animations_enabled()
    motion.set_animations_enabled(True)
    try:
        chart = ChartWidget()  # 同 AC-1：全新 chart 复现锚点，不随构造时机漂移
        chart.draw(records)
        QTest.qWait(100)  # 动画半程（200ms 时长）；Running 断言自证半程成立
        assert chart._draw_anim.state() == QAbstractAnimation.State.Running
        chart._clear_all()
        assert getattr(chart, "_draw_anim", None) is None  # 句柄复位
        # 排水等待：stop 后无在途回调 + deleteLater 全部处理，避免 chart 随
        # 测试结束被 Python GC 时残留待删动画子对象（延迟双重删除 abort）
        QTest.qWait(400)
    finally:
        motion.set_animations_enabled(prev)


def test_u06_motion_global_switch(qapp):
    """U-06：全局动效开关关闭时 fade_in 不设 effect、属性动画直接落终态。"""
    from PySide6.QtWidgets import QFrame

    from app import motion

    motion.set_animations_enabled(False)
    try:
        box = QFrame()
        assert motion.fade_in_widget(box, duration_ms=50) is None
        assert box.graphicsEffect() is None  # 不挂 effect，功能完整

        seen: list[float] = []
        anim = motion.animate_property(QFrame(), seen.append, duration_ms=50)
        assert anim is None
        assert seen == [1.0]  # 终态即时可达
    finally:
        motion.set_animations_enabled(True)


def test_u07_ui_minor_fixes(sample_window):
    """U-07 小修断言：日期对齐、状态 pill、按钮焦点 outline、QStatusBar 死样式删除。"""
    from PySide6.QtCore import Qt

    from app.theme import generate_qss

    win = sample_window

    # 日期标签与标题同侧左对齐（消除轴线错位）
    align = win._date_label.alignment()
    assert align & Qt.AlignmentFlag.AlignLeft

    # 「今日未录入」升级为状态 pill：QSS 含背景/边框/padding（非裸文字）
    qss_light = generate_qss("light")
    assert "QLabel#todayStatusLabel" in qss_light
    assert "background-color" in qss_light.split("QLabel#todayStatusLabel")[1][:300]
    assert "border-radius: 9px" in qss_light

    # QPushButton 焦点态可见（outline 不占布局，QLineEdit 已有 2px 边框环）
    assert "QPushButton:focus" in qss_light
    assert "outline" in qss_light

    # QStatusBar 死样式已删除（从未使用）
    assert "QStatusBar" not in generate_qss("dark")


# ── 5. 保存今日数据 ──────────────────────────────────────


def test_save_today_writes_data_and_indicator(sample_window):
    """填值保存 → 数据写入 + 指示器文案。"""
    win = sample_window

    win.input_panel.fill_values(90000000, 470000000)
    win.save_today()

    today_rec = win.logic.get_record(win.today)
    assert today_rec is not None
    assert today_rec.cash == 90000000.0
    assert today_rec.warehouse == 470000000.0

    indicator_text = win.input_panel.saved_indicator.text()
    assert "✓" in indicator_text and "470.0M" in indicator_text


# ── 6. 编辑模式 ──────────────────────────────────────────


def test_edit_mode_buttons_and_save(sample_window):
    """编辑模式：按钮文字 / 取消可见性 / 编辑保存。"""
    win = sample_window

    # 编辑最旧一条历史记录（≠ today，走编辑写入路径）
    dates = sorted(win.logic.data)
    edit_date = dates[0]
    rec = win.logic.get_record(edit_date)
    assert rec is not None

    win.input_panel.set_edit_mode(edit_date, rec.cash, rec.warehouse)
    assert win.input_panel.get_editing_date() == edit_date
    assert "更新数据" in win.input_panel.save_btn.text()
    assert not win.input_panel.cancel_edit_btn.isHidden()

    # 取消编辑
    win.input_panel.cancel_edit()
    assert win.input_panel.get_editing_date() is None
    assert win.input_panel.save_btn.text() == "保存今日数据"
    assert not win.input_panel.cancel_edit_btn.isVisible()

    # 再编辑一次，修改值并保存
    win.input_panel.set_edit_mode(edit_date, rec.cash, rec.warehouse)
    win.input_panel.fill_values(83000000, 451000000)
    win.save_today()

    updated = win.logic.get_record(edit_date)
    assert updated is not None
    assert updated.cash == 83000000.0
    assert updated.warehouse == 451000000.0

    # 保存后退出编辑模式
    assert not win.input_panel.is_editing()


def test_close_while_editing_asks_confirmation(sample_window, monkeypatch):
    """编辑态关窗：弹确认框，No 拦截 / Yes 允许（O-13）。"""
    win = sample_window
    dates = sorted(win.logic.data)
    rec = win.logic.get_record(dates[0])
    assert rec is not None
    win.input_panel.set_edit_mode(dates[0], rec.cash, rec.warehouse)
    assert win.input_panel.is_editing()

    # No → 拦截关窗（close() 返回 False，窗口保持打开）
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )
    assert win.close() is False

    # Yes → 允许关闭
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )
    assert win.close() is True

    # 恢复非编辑态，避免 fixture 收尾 close() 再次触发真实确认框（offscreen 下会阻塞挂起）
    win.input_panel.cancel_edit()


def test_save_triggers_rotation_hint(qapp, settings_guard, tmp_path):
    """保存后触发裁剪：状态提示展示自动删除（O-14，J 系列上限 30 条）。"""
    from app.main_window import MainWindow
    from config import RETENTION_LIMIT
    from tests.conftest import make_stub_client

    today = datetime.now()
    # 31 个日期键（含今天），超出保留上限 RETENTION_LIMIT 1 条 → 触发裁剪
    data = {}
    for off in range(RETENTION_LIMIT, -1, -1):
        d = (today - timedelta(days=off)).strftime(DATE_FORMAT)
        data[d] = {"cash": 100.0, "warehouse": 200.0 + off}

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(data),
        client=make_stub_client(),
    )
    assert len(win.logic.data) == RETENTION_LIMIT + 1

    win.input_panel.fill_values(100, 300)
    win.save_today()

    assert len(win.logic.data) == RETENTION_LIMIT  # 最旧 1 条被自动裁剪
    indicator = win.input_panel.saved_indicator.text()
    assert f"已保留最近 {RETENTION_LIMIT} 条记录" in indicator
    assert "自动清理 1 条较早记录" in indicator
    win.close()


# ── 7. 删除数据 ──────────────────────────────────────────


def test_delete_record_yes(sample_window, monkeypatch):
    """确认删除（Yes）→ 记录被删。"""
    win = sample_window

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )

    target = sorted(win.logic.data)[0]
    old_len = len(win.logic.data)
    win.table.delete_requested.emit(target)
    assert win.logic.get_record(target) is None
    assert len(win.logic.data) == old_len - 1


def test_delete_record_cancel(sample_window, monkeypatch):
    """确认删除（No）→ 记录保留。"""
    win = sample_window

    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.No),
    )

    target = sorted(win.logic.data)[1]
    old_len = len(win.logic.data)
    win.table.delete_requested.emit(target)
    assert win.logic.get_record(target) is not None
    assert len(win.logic.data) == old_len


# ── 8. 主题切换 ──────────────────────────────────────────


def test_theme_toggle(sample_window):
    """主题按钮点击切换，文字随主题变化。"""
    win = sample_window

    initial_text = win.sidebar.theme_btn.text()
    assert initial_text in ("暗色", "亮色")

    win.sidebar.theme_btn.click()  # 切到另一主题
    assert win.sidebar.theme_btn.text() != initial_text

    win.sidebar.theme_btn.click()  # 切回
    assert win.sidebar.theme_btn.text() == initial_text


def _icon_rgb(icon) -> tuple:
    """取 QIcon 渲染像素中 alpha 最高的 RGB（细线图标抗锯齿取主体色）。"""
    img = icon.pixmap(16, 16).toImage()
    best = None
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 0 and (best is None or c.alpha() > best.alpha()):
                best = c
    assert best is not None
    return best.getRgb()[:3]


def _hex_rgb(hex_color: str) -> tuple:
    """"#a8adbd" → (168, 173, 189)。"""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def test_icons_follow_theme_toggle(sample_window):
    """IC-02：主题切换后导航图标颜色随主题刷新（Falsify：漏重建则颜色冻结）。

    亮暗 FG_LABEL 双主题值不同（#3c4a43 vs #a8adbd）；refresh_theme 链路
    经 sidebar.apply_theme 重建图标后，像素应等于新主题 FG_LABEL（±6 抗锯齿）。
    """
    from app.theme import get_color

    win = sample_window
    light_rgb = _icon_rgb(win.sidebar._nav_items[0].icon())

    win.sidebar.theme_btn.click()  # light → dark（refresh_theme 全链路）
    dark_rgb = _icon_rgb(win.sidebar._nav_items[0].icon())

    assert light_rgb != dark_rgb, "主题切换后图标颜色未变化（apply_theme 漏重建）"
    want = _hex_rgb(get_color("FG_LABEL"))
    for actual, expected in zip(dark_rgb, want):
        assert abs(actual - expected) <= 6, f"图标色 {dark_rgb} ≠ FG_LABEL {want}"

    win.sidebar.theme_btn.click()  # 切回 light（theme._current_theme 全局态，防泄漏）


def test_theme_toggle_updates_exchange_labels(sample_window):
    """U-03 评审修复：主题切换后兑换页 7 包标签色随主题重解析。

    包标签为内联样式，构建期冻结；refresh_theme 链路必须调用
    exchange_page.apply_theme()，否则亮→暗切换残留 light 深墨色（对比度跌破 AA）。
    """
    from app.exchange_page import _PACKAGE_CONFIG
    from app.theme import get_color

    win = sample_window
    exchange = win.profit_page.exchange_page

    win.sidebar.theme_btn.click()  # light → dark
    for i, cfg in enumerate(_PACKAGE_CONFIG):
        assert get_color(cfg.color) in exchange._cards[i]._pkg_label.styleSheet(), (
            f"dark 下第 {i} 卡标签残留构建期色（apply_theme 链路未生效）"
        )
    for i, card in enumerate(exchange._cards):
        assert get_color("SEPARATOR") in card._sep.styleSheet(), (
            f"dark 下第 {i} 卡分隔线残留构建期色（Z-01 未生效）"
        )

    win.sidebar.theme_btn.click()  # 切回 light
    for i, cfg in enumerate(_PACKAGE_CONFIG):
        assert get_color(cfg.color) in exchange._cards[i]._pkg_label.styleSheet(), (
            f"light 下第 {i} 卡标签未随主题重解析"
        )
    for i, card in enumerate(exchange._cards):
        assert get_color("SEPARATOR") in card._sep.styleSheet(), (
            f"light 下第 {i} 卡分隔线未随主题重解析"
        )


# ── 8.5 注入 seam + 共享 client + 单出口扇出（C2-02）──────


def test_main_window_shares_single_injected_client(qapp, settings_guard, tmp_path):
    """C2-02：MainWindow(client=fake) → 利润页两子页 _client 同一实例（共享 client）。"""
    from types import SimpleNamespace

    from app.main_window import MainWindow

    fake = SimpleNamespace()
    win = MainWindow(
        store=DataStore(tmp_path / "d.json", tmp_path / "d.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
        client=fake,
    )
    assert win.profit_page.crafting_page._client is fake
    assert win.profit_page.exchange_page._client is fake
    win.close()


def test_shared_client_concurrent_preload_no_errors(
    qapp, settings_guard, tmp_path, monkeypatch
):
    """C2-02 ⑦：共享 client 两页并发 preload 无异常。

    两子页各自后台线程同时向同一 client 取数（线程重叠由 fetch 内 sleep 保证）；
    依赖 01 的锁保证线程安全（握手恰一次已在 01 覆盖），此处断言无异常 + 双页 loaded。
    """
    import time

    from PySide6.QtTest import QTest

    from app.main_window import MainWindow
    from kkrb_client import AmmoPackageItem, CraftingProduct, KkrbClient

    calls: list[str] = []
    client = KkrbClient()
    monkeypatch.setattr(
        client,
        "fetch_ov_data",
        lambda: (
            time.sleep(0.02), calls.append("ov"),
            [CraftingProduct("技术中心", "复合弓", 100, 200, "晚上8点")],
        )[2],
    )
    monkeypatch.setattr(
        client,
        "fetch_ammo_package_data",
        lambda: (
            time.sleep(0.02), calls.append("ammo"),
            [AmmoPackageItem("3级子弹自选包", "5.7mm", 3, 40, 100, 4000, 500)],
        )[2],
    )

    win = MainWindow(
        store=DataStore(tmp_path / "d.json", tmp_path / "d.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
        client=client,
    )
    assert win.profit_page.crafting_page._client is client
    assert win.profit_page.exchange_page._client is client

    win.profit_page.preload()  # 扇出两子页，各自后台线程并发取数
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        QTest.qWait(50)
        qapp.processEvents()
        if (
            win.profit_page.crafting_page.is_loaded
            and win.profit_page.exchange_page.is_loaded
        ):
            break
    assert win.profit_page.crafting_page.is_loaded
    assert win.profit_page.exchange_page.is_loaded
    assert sorted(calls) == ["ammo", "ov"]
    win.close()


def test_startup_preload_fans_out_via_profit_page(qapp, settings_guard, tmp_path):
    """C2-02：启动 500ms 定时器回调走 profit_page.preload() 单出口（不再直插两子页）。"""
    import time

    from types import SimpleNamespace

    from PySide6.QtTest import QTest

    from app.main_window import MainWindow

    win = MainWindow(
        store=DataStore(tmp_path / "d.json", tmp_path / "d.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
        client=SimpleNamespace(),
    )
    calls: list[str] = []
    win.profit_page.preload = lambda: calls.append("preload")  # type: ignore[method-assign]
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not calls:
        QTest.qWait(50)
        qapp.processEvents()
    assert calls == ["preload"]
    win.close()


def test_profit_page_access_whitelist_in_main_window() -> None:
    """C2-02 ⑥：main_window.py 中 `profit_page.` 后只允许 refresh/preload/apply_theme/shutdown。

    单出口契约（spec 4.2.7 + E5）：此后若在 main_window 直插
    profit_page.crafting_page 等子页访问即被 AST 证伪；扫描限 app/ 源码，
    测试文件对子页的直接访问不受限。
    """
    import ast
    import inspect

    import app.main_window as mw

    allowed = {"refresh", "preload", "apply_theme", "shutdown"}
    tree = ast.parse(inspect.getsource(mw))
    offenders: list[str] = []
    for node in ast.walk(tree):
        # 形如 `X.profit_page.Y` 的属性链：外层 attr 必须落在白名单
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
            if node.value.attr == "profit_page" and node.attr not in allowed:
                offenders.append(f"L{node.lineno}: profit_page.{node.attr}")
    assert offenders == [], f"main_window 直插 profit_page 子页访问：{offenders}"


# ── 9. 窗口置顶 ──────────────────────────────────────────


def test_pin_toggle(sample_window):
    """置顶按钮点击切换窗口 flag。"""
    win = sample_window
    stays_on_top = Qt.WindowType.WindowStaysOnTopHint

    assert not bool(win.windowFlags() & stays_on_top)

    win.sidebar.pin_btn.click()
    assert bool(win.windowFlags() & stays_on_top)

    win.sidebar.pin_btn.click()
    assert not bool(win.windowFlags() & stays_on_top)


# ── 10. 设置持久化 ───────────────────────────────────────


def test_settings_persistence(sample_window, tmp_path):
    """设置写入与恢复（theme/pinned/geometry 落盘）。"""
    import app.main_window as mw

    win = sample_window
    test_settings = tmp_path / "settings.json"

    # 通过公开交互触发状态变更；closeEvent → _save_settings 落盘（公开 seam）
    win.sidebar.theme_btn.click()   # _toggle_theme 内部已保存 theme
    win.sidebar.pin_btn.click()     # _toggle_pin 不落盘
    win.close()

    assert test_settings.exists()
    with open(test_settings, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved.get("theme") == "dark"  # 默认 light → 点击一次 → dark
    assert saved.get("pinned") is True
    assert "geometry" in saved
    assert saved.get("animations") is True  # 默认 true 纳入持久化闭环（C3-11）
    assert "current_account" not in saved  # 注入模式无账号概念，不写该键（C3-11）


def test_animations_false_persists_through_close(qapp, tmp_path):
    """C3-11 往返回归：animations=false 预置 → 构造 → closeEvent → 落盘仍 false。

    旧实现 _save_settings 全量覆盖写不写 animations——启动读取的 false
    偏好首次落盘即丢；update 流程必须保留（可证伪回归）。
    """
    from app.main_window import MainWindow
    from data_store import DataStore
    from settings_store import SettingsStore
    from tests.conftest import make_stub_client

    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"animations": False}), encoding="utf-8")

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        settings_store=SettingsStore(settings_file),
        client=make_stub_client(),
    )
    win.close()

    saved = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved.get("animations") is False, (
        f"animations=false 偏好必须往返保留，实际落盘 {saved.get('animations')!r}"
    )


def test_unknown_settings_key_survives_theme_toggle_and_close(qapp, tmp_path):
    """C3-11：预置 custom 未知键 → 主题切换 + 关窗 → 落盘仍含 custom（端到端保留）。"""
    from app.main_window import MainWindow
    from data_store import DataStore
    from settings_store import SettingsStore
    from tests.conftest import make_stub_client

    settings_file = tmp_path / "settings.json"
    settings_file.write_text(json.dumps({"custom": 1}), encoding="utf-8")

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        settings_store=SettingsStore(settings_file),
        client=make_stub_client(),
    )
    win.sidebar.theme_btn.click()  # _toggle_theme → _save_settings
    win.close()                    # closeEvent → _save_settings

    saved = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved.get("custom") == 1, f"未知键 custom 必须端到端保留：{saved}"
    assert saved.get("theme") == "dark"


# ── 11. 窗口几何恢复 ─────────────────────────────────────


def test_geometry_restore_old_format(qapp, tmp_path, monkeypatch):
    """旧格式（Tkinter）geometry 恢复无 crash。"""
    import app.main_window as mw
    from app.main_window import MainWindow
    from tests.conftest import make_stub_client

    test_file = tmp_path / "settings_old.json"
    monkeypatch.setattr(mw, "SETTINGS_FILE", test_file)
    test_file.write_text(
        json.dumps({"geometry": "680x900+100+50", "pinned": False, "theme": "light"}),
        encoding="utf-8",
    )

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        client=make_stub_client(),
    )
    win.close()


def test_geometry_restore_new_format(qapp, tmp_path, monkeypatch):
    """新格式（空 geometry / hex）恢复无 crash。"""
    import app.main_window as mw
    from app.main_window import MainWindow
    from tests.conftest import make_stub_client

    test_file = tmp_path / "settings_new.json"
    monkeypatch.setattr(mw, "SETTINGS_FILE", test_file)
    test_file.write_text(
        json.dumps({"geometry": "", "pinned": False, "theme": "dark"}),
        encoding="utf-8",
    )

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        client=make_stub_client(),
    )
    win.close()


# ── 13. 金额输入校验联动 ─────────────────────────────────


def test_input_validation_save_btn(sample_window, type_and_settle):
    """save_btn 随两个字段合法性联动启停。

    D-04：校验断言走真实事件链路（QTest 键入 → 150ms 去抖 → validity_changed
    → save_btn），不再用 `refresh_validity()` 同步后门。
    """
    ip = sample_window.input_panel

    # 初始空 → 禁用
    assert not ip.save_btn.isEnabled()

    # 填一个字段 → 仍禁用
    type_and_settle(ip.cash_entry, "100000")
    assert not ip.save_btn.isEnabled()

    # 填两个字段 → 启用
    type_and_settle(ip.warehouse_entry, "200000")
    assert ip.save_btn.isEnabled()

    # 改现金为非法 → 禁用
    type_and_settle(ip.cash_entry, "abc")
    assert not ip.save_btn.isEnabled()

    # 恢复合法 → 启用
    type_and_settle(ip.cash_entry, "100000")
    assert ip.save_btn.isEnabled()

    # 清空两字段 → 禁用
    type_and_settle(ip.cash_entry, "")
    type_and_settle(ip.warehouse_entry, "")
    assert not ip.save_btn.isEnabled()


# ── 14. 键盘快捷键 ───────────────────────────────────────


def test_keyboard_shortcuts_enter_and_escape(sample_window):
    """Enter / Esc 快捷键已绑定 QAction。"""
    win = sample_window
    actions = win.actions()

    enter_shortcuts = [
        a for a in actions if a.shortcut() == QKeySequence(Qt.Key.Key_Return)
    ]
    assert len(enter_shortcuts) >= 1

    esc_shortcuts = [
        a for a in actions if a.shortcut() == QKeySequence(Qt.Key.Key_Escape)
    ]
    assert len(esc_shortcuts) >= 1


# ── O-04. CSV 导出 ───────────────────────────────────


def test_export_btn_exists(sample_window):
    """标题栏存在「导出 CSV」按钮。"""
    win = sample_window
    assert hasattr(win.sidebar, "export_btn")
    assert win.sidebar.export_btn.text() == "导出 CSV"


def test_export_csv_writes_file(sample_window, monkeypatch, tmp_path):
    """点击导出 → 选择路径 → 写入 utf-8-sig CSV（Excel 可直接打开）。"""
    win = sample_window
    out = tmp_path / "export.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(out), "CSV 文件 (*.csv)")),
    )

    win.sidebar.export_btn.click()

    assert out.exists()
    raw = out.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # utf-8-sig BOM
    text = raw.decode("utf-8-sig")
    assert text.startswith("日期,现金,仓库,较前日,收益率\n")


def test_export_csv_cancel_writes_nothing(sample_window, monkeypatch, tmp_path):
    """取消文件选择 → 不写入文件、无异常。"""
    win = sample_window
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **kw: ("", "")),
    )

    win.sidebar.export_btn.click()

    assert list(tmp_path.iterdir()) == []


def test_export_csv_failure_shows_warning(sample_window, monkeypatch, tmp_path):
    """写入失败 → 弹出警告且不静默。"""
    win = sample_window
    out = tmp_path / "export.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(out), "CSV 文件 (*.csv)")),
    )
    monkeypatch.setattr(
        "builtins.open",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("disk full")),
    )
    warnings: list = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **kw: warnings.append(a)),
    )

    win.sidebar.export_btn.click()

    assert warnings  # 写失败时弹了警告
    assert not out.exists()


# ── O-05. 今日未录入提醒 ─────────────────────────────


@pytest.fixture
def window_without_today(qapp, settings_guard, tmp_path):
    """数据不含今日记录的 MainWindow（触发「今日未录入」提醒）。"""
    from app.main_window import MainWindow
    from tests.conftest import make_stub_client

    data = make_sample_data()
    today_str = datetime.now().strftime(DATE_FORMAT)
    data.pop(today_str, None)
    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(data),
        client=make_stub_client(),
    )
    yield win
    win.close()


def test_today_status_shown_when_not_recorded(window_without_today):
    """今日未录入时提醒标签可见。"""
    win = window_without_today
    assert win.logic.get_record(win.today) is None
    assert win._today_status_label.text() == "今日未录入"
    assert not win._today_status_label.isHidden()


def test_today_status_hidden_after_save(window_without_today):
    """保存今日数据后提醒标签隐藏。"""
    win = window_without_today
    assert not win._today_status_label.isHidden()

    win.input_panel.fill_values(90000000, 470000000)
    win.save_today()

    assert win.logic.get_record(win.today) is not None
    assert win._today_status_label.isHidden()


def test_today_status_hidden_when_recorded(sample_window):
    """今日已有记录时提醒标签隐藏。"""
    win = sample_window
    assert win.logic.get_record(win.today) is not None
    assert win._today_status_label.isHidden()


# ── O-06. 图表稀疏数据提示 ───────────────────────────


def test_chart_sparse_data_hint(sample_window):
    """O-06：n=2~3 时叠加「数据较少」半透明提示；n>=4 时无提示；n<2 时回归占位。"""
    win = sample_window
    present = win.logic.recent_records(7)
    assert len(present) >= 5  # 样本数据充足

    # n >= 4：无稀疏提示
    win.chart.draw(present)
    assert win.chart._placeholder_label is None

    # n = 3 / n = 2：叠加半透明提示，且不拦截鼠标（不触碰交互）
    for subset in (present[-3:], present[-2:]):
        win.chart.draw(subset)
        label = win.chart._placeholder_label
        assert label is not None
        assert "数据较少" in label.text()
        assert label.testAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

    # n < 2：回归原占位提示（至少需要两天数据）
    win.chart.draw(present[-1:])
    label = win.chart._placeholder_label
    assert label is not None
    assert "至少需要两天数据" in label.text()


# ── 双 Y 轴合并图结构（G-01 评审修正 0559537：无填充、hover 按所属 ViewBox 定位）──


def test_chart_dual_axis_no_fill_and_hover_views(sample_window):
    """合并图结构：单 PlotWidget 双曲线/双轴、无填充区域、hover 标签按所属 ViewBox 定位。"""
    win = sample_window
    records = win.logic.recent_records(7)
    assert len(records) >= 2
    win.chart.draw(records)

    state = win.chart.state
    assert len(state.series) == 2
    assert state.series[0].name == "warehouse"
    assert state.series[1].name == "cash"
    assert state.axis_count == 2


# ── G-01. 图表双 Y 轴合并（ADR-0002）────────────────────


def test_chart_dual_axis_merged(sample_window):
    """G-01：双曲线合并到同一坐标系后，一次 draw 即渲染两线于同一 PlotWidget。

    仓库（左轴）与现金（右轴）各自落入独立 ViewBox（各自 Y 量纲，共享 X 轴）；
    图例显式注册两条曲线（副 ViewBox 项目不会自动进主 PlotItem 图例）。
    """
    win = sample_window
    records = win.logic.recent_records(7)
    assert len(records) >= 5  # 样本数据充足

    win.chart.draw(records)

    state = win.chart.state
    assert len(state.series) == 2
    assert state.series[0].name == "warehouse"
    assert state.series[1].name == "cash"
    assert state.series[0].data_points > 0
    assert state.series[1].data_points > 0
    assert state.axis_count == 2


# ── 14. 视图切换 7/30（J 系列）─────────────────────────


@pytest.fixture
def view_switch_window(qapp, settings_guard, tmp_path):
    """30 条记录的 MainWindow（相对今天生成，隔离真实数据/settings）。

    J 系列：视图切换用例需超 7 条的存量来验证 7↔30 窗口联动与
    「切回 7 不丢存储」（Q5 视图/存储解耦）。
    """
    from app.main_window import MainWindow
    from data_store import DataStore
    from tests.conftest import make_stub_client

    today = datetime.now()
    data = {}
    for off in range(30):
        d = (today - timedelta(days=off)).strftime(DATE_FORMAT)
        data[d] = {"cash": 100.0 + off, "warehouse": 200.0 + off * 1000}
    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(data),
        client=make_stub_client(),
    )
    yield win
    win.close()


def test_view_default_is_7(sample_window):
    """启动默认视图 7：_view_n=7、7天按钮选中、双栏均分 ceil(n/2)。"""
    win = sample_window
    assert win._view_n == 7
    assert win.table.current_view() == 7
    checked = [b.property("days") for b in win.table._view_buttons if b.isChecked()]
    assert checked == [7]

    win.refresh_display()
    # 样本 6 条 → mid=ceil(6/2)=3 → 3+3（Q7 均分）
    assert win.table._left_table.rowCount() == 3
    assert win.table._right_table.rowCount() == 3


def test_view_switch_to_30_refreshes_all(view_switch_window):
    """切到 30：view_changed(30) 信号 → _view_n=30 → 表格 15+15 + 汇总最近30条 全联动。"""
    win = view_switch_window
    assert win._view_n == 7
    win.refresh_display()
    assert win.table._left_table.rowCount() + win.table._right_table.rowCount() == 7

    received = []
    win.table.view_changed.connect(received.append)
    btn30 = next(b for b in win.table._view_buttons if b.property("days") == 30)
    btn30.click()

    assert received == [30]           # 信号契约（Q8：emit 当前视图条数）
    assert win._view_n == 30          # MainWindow 视角同步（Q10 单一开关）
    assert win.table.current_view() == 30
    assert win.table._left_table.rowCount() == 15   # 30 → 15+15 均分（Q7）
    assert win.table._right_table.rowCount() == 15
    assert "最近30条" in win._summary_caption.text()   # 汇总联动（Q9）


def test_view_switch_back_to_7_keeps_storage(view_switch_window):
    """切回 7：窗口收窄到 7 条，存储仍 30 条（Q5 解耦，切回不丢数据）。"""
    win = view_switch_window
    btn30 = next(b for b in win.table._view_buttons if b.property("days") == 30)
    btn30.click()
    assert win.table.current_view() == 30

    btn7 = next(b for b in win.table._view_buttons if b.property("days") == 7)
    btn7.click()

    assert win.table.current_view() == 7
    assert win._view_n == 7
    rows = win.table._left_table.rowCount() + win.table._right_table.rowCount()
    assert rows == 7
    assert len(win.logic.data) == 30      # 存储不丢
    assert "最近7条" in win._summary_caption.text()


def test_cash_summary_label_follows_view(view_switch_window):
    """现金总变化磁贴随视图 7/30 联动，与总盈亏磁贴同卡渲染（U-01 磁贴化）。"""
    win = view_switch_window
    assert hasattr(win, "_cash_summary_label")  # 双磁贴就位
    assert hasattr(win, "_summary_caption")

    win.refresh_display()
    assert "最近7条" in win._summary_caption.text()
    assert "最近7条现金总变化" in win._cash_summary_caption.text()
    # 磁贴数字行有内容（拆「说明：数值」后数值非空）
    assert win._summary_label.text() != ""

    btn30 = next(b for b in win.table._view_buttons if b.property("days") == 30)
    btn30.click()
    assert "最近30条现金总变化" in win._cash_summary_caption.text()


# ── Y-03. 启动解析当前账号（current_account 持久化 + 兜底恢复）──
#
# seam 定案：仅当未注入 store/logic 时才走账号解析（生产默认路径）；注入
# account_store + settings_store 让完整解析链路落在 tmp_path，零真实用户目录。


@pytest.fixture
def account_window_factory(qapp, settings_guard, tmp_path):
    """构造走账号解析路径的 MainWindow 工厂（注入 AccountStore/SettingsStore）。

    setup(acc) 在窗口构造前调用，用于预置账号/数据（窗口构造即解析 current_account）。
    """
    from account_store import AccountStore
    from app.main_window import MainWindow
    from settings_store import SettingsStore
    from tests.conftest import make_stub_client

    def _make(settings_data=None, setup=None):
        acc = AccountStore(tmp_path / "accounts")
        if setup is not None:
            setup(acc)
        settings_file = tmp_path / "settings.json"
        if settings_data is not None:
            settings_file.write_text(
                json.dumps(settings_data, ensure_ascii=False), encoding="utf-8"
            )
        win = MainWindow(
            account_store=acc,
            settings_store=SettingsStore(settings_file),
            client=make_stub_client(),
        )
        return win, acc

    return _make


def _save_account_record(acc, name, data):
    """向指定账号写入一条记录（通过 DataStore 注入，验证账号隔离）。"""
    acc.create_account(name)
    acc.new_store(name).save(data)


def test_startup_resolves_saved_current_account(account_window_factory, tmp_path):
    """settings.current_account 指向存在的账号 → 启动落在该账号：store 路径 / 数据 / 标题。"""
    win, acc = account_window_factory(
        settings_data={"current_account": "小号"},
        setup=lambda a: _save_account_record(
            a, "小号", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}
        ),
    )

    try:
        assert win.current_account == "小号"
        assert win.store.data_file == tmp_path / "accounts" / "小号" / "data.json"
        assert win.logic.get_record("2026-08-01") is not None
        assert "小号" in win._title_label.text()
    finally:
        win.close()


def test_startup_falls_back_when_current_account_missing(account_window_factory):
    """settings 无 current_account（首次升级/全新安装）→ 回退主账号并自动建目录。"""
    win, acc = account_window_factory(settings_data={})

    try:
        assert win.current_account == "主账号"
        assert (acc.accounts_dir / "主账号").is_dir()
        assert win.store.load() == {}  # 主账号空库起步（H3/H5）
        assert "主账号" in win._title_label.text()
    finally:
        win.close()


def test_startup_falls_back_when_current_account_invalid(account_window_factory):
    """current_account 指向不存在目录 → 回退主账号。"""
    win, acc = account_window_factory(settings_data={"current_account": "已删除"})
    acc.create_account("小号")

    try:
        assert win.current_account == "主账号"
    finally:
        win.close()


def test_startup_falls_back_when_current_account_not_string(account_window_factory):
    """current_account 非字符串（损坏/手改 settings）→ 回退主账号。"""
    win, _ = account_window_factory(settings_data={"current_account": 123})

    try:
        assert win.current_account == "主账号"
    finally:
        win.close()


def test_startup_creates_default_account_when_accounts_empty(account_window_factory):
    """accounts/ 为空 → 自动创建主账号空数据（resolve_account 兜底）。"""
    win, acc = account_window_factory(settings_data={"current_account": "小号"})

    try:
        assert win.current_account == "主账号"
        assert (acc.accounts_dir / "主账号").is_dir()
    finally:
        win.close()


def test_close_persists_current_account_with_other_settings(account_window_factory):
    """关窗落盘回读：current_account 写入 settings.json，geometry/pinned/theme 不丢。"""
    win, acc = account_window_factory(
        settings_data={"current_account": "小号"},
        setup=lambda a: _save_account_record(
            a, "小号", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}
        ),
    )

    win.sidebar.theme_btn.click()  # 触发状态变更（theme 落盘路径）
    win.close()

    saved = json.loads(
        (acc.accounts_dir.parent / "settings.json").read_text(encoding="utf-8")
    )
    assert saved.get("current_account") == "小号"
    assert saved.get("theme") == "dark"  # 与 encode_settings 输出合并，不丢
    assert "geometry" in saved
    assert "pinned" in saved


def test_account_mode_persists_current_account_key_forward(account_window_factory):
    """C3-11 正向断言：账号模式落盘含 current_account 键且值非空。

    与 test_settings_persistence 的注入模式反向断言（"not in saved"）成对
    ——验收 1「账号模式含 current_account；注入模式不含」双向可证伪。
    """
    from settings_store import KNOWN_KEYS

    win, acc = account_window_factory(
        settings_data={"current_account": "小号"},
        setup=lambda a: _save_account_record(
            a, "小号", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}
        ),
    )
    win.close()

    saved = json.loads(
        (acc.accounts_dir.parent / "settings.json").read_text(encoding="utf-8")
    )
    assert "current_account" in saved, f"账号模式落盘必须含 current_account 键：{saved}"
    assert saved["current_account"] == "小号"  # 值非空且为当前账号
    assert set(KNOWN_KEYS) <= set(saved), (
        f"账号模式落盘应含全部已知键 {sorted(KNOWN_KEYS)}：{saved}"
    )


def test_injected_store_skips_account_resolution(qapp, settings_guard, tmp_path):
    """注入 store（既有模式）→ 跳过账号解析：resolve 不被调用、无账号概念、标题不变。"""
    from account_store import AccountStore
    from app.main_window import MainWindow
    from data_store import DataStore
    from settings_store import SettingsStore
    from tests.conftest import make_stub_client

    calls = {"resolve": 0, "new_store": 0}

    class SpyStore(AccountStore):
        def resolve_account(self, current):
            calls["resolve"] += 1
            return super().resolve_account(current)

        def new_store(self, name):
            calls["new_store"] += 1
            return super().new_store(name)

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        account_store=SpyStore(tmp_path / "accounts"),
        settings_store=SettingsStore(tmp_path / "settings.json"),
        client=make_stub_client(),
    )

    assert calls["resolve"] == 0
    assert calls["new_store"] == 0
    assert win.current_account is None
    assert win._title_label.text() == "Delta Force Dashboard"  # 标题保持原样
    assert not (tmp_path / "accounts").exists()  # 零真实目录触碰
    win.close()


def _find_accounts_literals(source: str) -> list[tuple[int, str]]:
    """AST 提取源码中所有含 "accounts" 的字符串字面量（含 f-string 分段）。

    F-P2 评审修复：真 AST 检查（ast.parse + ast.walk），文本检查可绕过的
    单引号 / f-string / 拼接变体均被捕获；返回 (行号, 字面量) 列表用于定位。
    docstring（模块/类/函数首条 Expr 常量）是文档引用业务层方法名
    （list_accounts / set_accounts）的合法位置，不计入拼装嫌疑。
    """
    import ast

    tree = ast.parse(source)
    docstrings = _collect_docstring_nodes(tree)
    found = []
    for node in ast.walk(tree):
        if node in docstrings:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "accounts" in node.value:
                found.append((node.lineno, node.value))
        elif isinstance(node, ast.JoinedStr):
            for part in node.values:
                if (
                    isinstance(part, ast.Constant)
                    and isinstance(part.value, str)
                    and "accounts" in part.value
                ):
                    found.append((part.lineno, part.value))
    return found


def _collect_docstring_nodes(tree) -> set:
    """收集模块/类/函数 docstring 节点（各定义体首条 Expr-Constant 字符串）。"""
    import ast

    nodes = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            nodes.add(body[0].value)
    return nodes


def test_ui_layers_do_not_build_account_paths():
    """AST 防复发：UI 层（main_window / sidebar）不得直接拼装账号路径。

    F-P2 评审修复：真 AST 提取字符串字面量与 f-string 分段（原裸文本检查
    可被单引号 / f-string 绕过，ast 零使用）；引用账号目录常量同样拦截。
    """
    import pathlib

    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    for name in ("main_window.py", "sidebar.py"):
        source = (app_dir / name).read_text(encoding="utf-8")
        assert _find_accounts_literals(source) == [], (
            f"{name} 含账号目录名字面量（必须走 account_store）"
        )
        assert "ACCOUNTS_DIR_NAME" not in source, (
            f"{name} 引用账号目录常量（必须走 account_store）"
        )


def test_accounts_literal_detection_catches_quote_variants():
    """F-P2：AST 检查能抓到单引号 / f-string / 拼接变体（文本检查可绕过的形态）。"""
    snippet = (
        "def evil(x):\n"
        "    a = 'accounts'            # 单引号变体\n"
        "    b = f\"{x}/accounts\"      # f-string 变体\n"
        "    c = 'sub/' + 'accounts'   # 拼接变体\n"
    )
    found = _find_accounts_literals(snippet)
    assert len(found) >= 3, f"变体未被 AST 检查捕获：{found}"


# ── Y-04. 侧边栏账号区（下拉框 + 新建账号 + 命名对话框）────


def _monkeypatch_input_dialog(monkeypatch, result):
    """命名对话框返回 (text, ok)；未调用则断言失败。"""
    from PySide6.QtWidgets import QInputDialog

    calls = []

    def _fake_gettext(*a, **kw):
        calls.append(a)
        return result

    monkeypatch.setattr(QInputDialog, "getText", staticmethod(_fake_gettext))
    return calls


def test_account_area_initial_state(account_window_factory):
    """账号区就位：下拉列出全部账号且当前账号选中 + 新建按钮。"""
    win, _ = account_window_factory(
        setup=lambda a: (
            _save_account_record(a, "主账号", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}),
            a.create_account("小号"),
        )
    )

    try:
        assert not win.sidebar.account_combo.isHidden()
        items = [
            win.sidebar.account_combo.itemText(i)
            for i in range(win.sidebar.account_combo.count())
        ]
        assert items == ["主账号", "小号"]
        assert win.sidebar.account_combo.currentText() == "主账号"
        assert "新建账号" in win.sidebar.new_account_btn.text()
        assert win._title_label.text() == "Delta Force Dashboard · 主账号"
    finally:
        win.close()


def test_create_account_success_appears_in_list_without_switching(
    account_window_factory, monkeypatch
):
    """新建成功 → 下拉立即出现新账号；当前账号不变；新账号空库（H5）。"""
    win, acc = account_window_factory(
        setup=lambda a: _save_account_record(
            a, "主账号", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}
        )
    )
    _monkeypatch_input_dialog(monkeypatch, ("新账号", True))

    win.sidebar.new_account_btn.click()

    items = [
        win.sidebar.account_combo.itemText(i)
        for i in range(win.sidebar.account_combo.count())
    ]
    assert items == ["主账号", "新账号"]
    assert win.current_account == "主账号"  # 决策 6：当前账号不变
    assert win.sidebar.account_combo.currentText() == "主账号"
    new_dir = acc.accounts_dir / "新账号"
    assert new_dir.is_dir()
    assert not (new_dir / "data.json").exists()  # H5：空库起步
    assert win._title_label.text() == "Delta Force Dashboard · 主账号"
    win.close()


@pytest.mark.parametrize(
    "name",
    ["", "   ", "主账号", "a/b", "a\\b", "a:b", "a*b", 'a"b', "a<b", "a>b", "a|b", " a", "a ", ".a", "a."],
)
def test_create_account_rejects_invalid_names(
    account_window_factory, monkeypatch, name
):
    """非法名（空/重名/禁用字符/首尾空格或点）→ 可读提示、零目录产生、列表不变。"""
    from PySide6.QtWidgets import QMessageBox

    win, acc = account_window_factory(
        setup=lambda a: (
            _save_account_record(a, "主账号", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}),
            a.create_account("小号"),
        )
    )
    _monkeypatch_input_dialog(monkeypatch, (name, True))
    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **kw: warnings.append(a)),
    )

    win.sidebar.new_account_btn.click()

    assert warnings, "非法名必须给出可读提示"
    assert acc.list_accounts() == ["主账号", "小号"]  # 零目录产生
    assert win.sidebar.account_combo.count() == 2
    assert win.current_account == "主账号"  # 当前账号不受影响
    win.close()


def test_create_account_cancel_is_noop(account_window_factory, monkeypatch):
    """命名对话框取消 → 无操作（不创建、不提示）。"""
    from PySide6.QtWidgets import QMessageBox

    win, acc = account_window_factory(
        setup=lambda a: _save_account_record(
            a, "主账号", {"2026-08-01": {"cash": 1.0, "warehouse": 2.0}}
        )
    )
    _monkeypatch_input_dialog(monkeypatch, ("随便", False))
    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **kw: warnings.append(a)),
    )

    win.sidebar.new_account_btn.click()

    assert warnings == []  # 取消不弹提示
    assert acc.list_accounts() == ["主账号"]
    win.close()


def test_account_area_hidden_when_store_injected(qapp, settings_guard, tmp_path):
    """注入 store（既有模式）→ 账号区隐藏（无账号概念，零破坏）。"""
    from app.main_window import MainWindow
    from data_store import DataStore
    from settings_store import SettingsStore
    from tests.conftest import make_stub_client

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        settings_store=SettingsStore(tmp_path / "settings.json"),
        client=make_stub_client(),
    )

    assert win.sidebar.account_combo.isHidden()
    assert win.sidebar.new_account_btn.isHidden()
    win.close()


# ── Y-05. 账号切换（运行中切换 + 记账页整体重载 + 落盘）──


def _two_account_dates() -> dict:
    """双账号测试日期集：主账号 -2/-1 天、小号 -3 天（相对 now，不含今日）。

    「测试数据相对 now」纪律（S3 评审修复）：保存/今日状态断言不与墙钟耦合。
    """
    today = datetime.now()
    return {
        "main_dates": [
            (today - timedelta(days=2)).strftime(DATE_FORMAT),
            (today - timedelta(days=1)).strftime(DATE_FORMAT),
        ],
        "xiao_date": (today - timedelta(days=3)).strftime(DATE_FORMAT),
    }


def _two_account_env(acc, dates: dict) -> None:
    """预置双账号：主账号 2 条、小号 1 条（日期由 _two_account_dates 提供）。"""
    _save_account_record(
        acc,
        "主账号",
        {
            dates["main_dates"][0]: {"cash": 100.0, "warehouse": 200.0},
            dates["main_dates"][1]: {"cash": 150.0, "warehouse": 250.0},
        },
    )
    _save_account_record(acc, "小号", {dates["xiao_date"]: {"cash": 500.0, "warehouse": 900.0}})


def _select_account(win, name):
    """通过下拉框真实信号链路选择账号（activated → account_selected → MainWindow）。"""
    combo = win.sidebar.account_combo
    for i in range(combo.count()):
        if combo.itemText(i) == name:
            combo.activated.emit(i)
            return
    raise AssertionError(f"下拉框没有账号 {name!r}")


def test_switch_account_reloads_all_views(account_window_factory, tmp_path):
    """切换 → 换 DataStore/logic + refresh_display 全量刷新（表格/汇总/今日状态/标题/下拉）。"""
    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    assert win.table._left_table.rowCount() == 1
    assert win.table._right_table.rowCount() == 1  # 主账号 2 条 → 1+1

    try:
        _select_account(win, "小号")

        assert win.current_account == "小号"
        assert win.store.data_file == tmp_path / "accounts" / "小号" / "data.json"
        assert win.logic.get_record(dates["xiao_date"]) is not None
        assert win.logic.get_record(dates["main_dates"][0]) is None  # 旧账号数据不可见
        # 表格刷新：小号 1 条 → 1+0
        assert win.table._left_table.rowCount() == 1
        assert win.table._right_table.rowCount() == 0
        # 汇总磁贴刷新（小号 total=900 ≠ 主账号 total=250）
        assert win._summary_label.text() != ""
        # 今日状态刷新（小号无今日记录 → 提示可见）
        assert not win._today_status_label.isHidden()
        # 标题与下拉选中同步
        assert win._title_label.text() == "Delta Force Dashboard · 小号"
        assert win.sidebar.account_combo.currentText() == "小号"
    finally:
        win.close()


def test_switch_persists_and_restarts_into_new_account(account_window_factory, tmp_path):
    """切换后关窗落盘 current_account；重启（同 settings 文件）回到新账号（回读断言）。"""
    from app.main_window import MainWindow
    from settings_store import SettingsStore
    from tests.conftest import make_stub_client

    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    _select_account(win, "小号")
    win.close()

    saved = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert saved.get("current_account") == "小号"

    # 重启：同一 accounts/settings 路径重新构造 → 回到小号
    win2 = MainWindow(
        account_store=acc,
        settings_store=SettingsStore(tmp_path / "settings.json"),
        client=make_stub_client(),
    )
    try:
        assert win2.current_account == "小号"
        assert win2.logic.get_record(dates["xiao_date"]) is not None
        assert win2._title_label.text() == "Delta Force Dashboard · 小号"
        assert win2.sidebar.account_combo.currentText() == "小号"
    finally:
        win2.close()


def test_switch_cancels_edit_state(account_window_factory):
    """切换时取消编辑模式（防跨账号污染）：退出编辑、字段清空。"""
    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    edit_date = dates["main_dates"][1]
    win.input_panel.set_edit_mode(edit_date, 150.0, 250.0)
    assert win.input_panel.is_editing()

    try:
        _select_account(win, "小号")

        assert not win.input_panel.is_editing()
        assert win.input_panel.get_editing_date() is None
        assert win.input_panel.get_cash_raw() == ""
        assert win.input_panel.get_warehouse_raw() == ""
        assert win.input_panel.save_btn.text() == "保存今日数据"
    finally:
        win.input_panel.cancel_edit()  # 红阶段防御：切换未实现时避免关窗确认框挂起
        win.close()


def test_switch_cancels_reuse_state(account_window_factory):
    """切换时取消复用模式（防跨账号污染）：退出复用、字段清空。"""
    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    reuse_date = dates["main_dates"][1]
    win.input_panel.set_reuse_hint(f"{reuse_date} 的数据", 150.0, 250.0)
    assert win.input_panel.is_reusing()

    try:
        _select_account(win, "小号")

        assert not win.input_panel.is_reusing()
        assert win.input_panel.get_cash_raw() == ""
        assert win.input_panel.get_warehouse_raw() == ""
        assert win.input_panel.reuse_btn.text() == "复用昨日"
    finally:
        win.input_panel.cancel_reuse()  # 红阶段防御：避免关窗确认框挂起
        win.close()


def test_switch_save_lands_in_new_account(account_window_factory, tmp_path):
    """切换后保存即时落在新账号文件；原账号文件不变。"""
    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    _select_account(win, "小号")

    win.input_panel.fill_values(100, 300)
    win.save_today()

    saved_xiao = json.loads(
        (tmp_path / "accounts" / "小号" / "data.json").read_text(encoding="utf-8")
    )
    assert win.today in saved_xiao  # 今日记录写入小号
    saved_main = json.loads(
        (tmp_path / "accounts" / "主账号" / "data.json").read_text(encoding="utf-8")
    )
    assert win.today not in saved_main  # 主账号文件不变
    assert set(saved_main) == set(dates["main_dates"])  # 主账号原有记录不变
    win.close()


def test_switch_delete_lands_in_new_account(account_window_factory, monkeypatch, tmp_path):
    """切换后删除即时落在新账号文件；原账号文件不变。"""
    from PySide6.QtWidgets import QMessageBox

    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **kw: QMessageBox.StandardButton.Yes),
    )
    _select_account(win, "小号")

    win.table.delete_requested.emit(dates["xiao_date"])

    saved_xiao = json.loads(
        (tmp_path / "accounts" / "小号" / "data.json").read_text(encoding="utf-8")
    )
    assert dates["xiao_date"] not in saved_xiao  # 小号记录被删
    saved_main = json.loads(
        (tmp_path / "accounts" / "主账号" / "data.json").read_text(encoding="utf-8")
    )
    assert set(saved_main) == set(dates["main_dates"])  # 主账号不变
    win.close()


def test_switch_export_uses_new_account(account_window_factory, monkeypatch, tmp_path):
    """切换后 CSV 导出作用于新账号（导出内容 = 小号数据）。"""
    from PySide6.QtWidgets import QFileDialog

    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    out = tmp_path / "export.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(out), "CSV 文件 (*.csv)")),
    )
    _select_account(win, "小号")

    win.sidebar.export_btn.click()

    text = out.read_text(encoding="utf-8-sig")
    assert dates["xiao_date"] in text  # 小号记录
    assert dates["main_dates"][0] not in text  # 主账号独有记录不出现
    win.close()


def test_switch_same_account_noop(account_window_factory, monkeypatch):
    """选择当前账号本身 → no-op：不换 store/logic、不落盘。"""
    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    old_store = win.store
    old_logic = win.logic
    save_calls = []
    monkeypatch.setattr(win.settings_store, "save", lambda s: save_calls.append(s))

    try:
        _select_account(win, "主账号")  # 当前就是主账号

        assert win.store is old_store  # 对象引用不变（未重载）
        assert win.logic is old_logic
        assert win.current_account == "主账号"
        assert save_calls == []  # 不落盘
        assert win._title_label.text() == "Delta Force Dashboard · 主账号"
    finally:
        win.close()


def test_switch_unknown_account_ignored(account_window_factory, monkeypatch):
    """目标账号不在列表（防御）→ 忽略；越界 index 产生空名 → 非法名提示（不切换）。"""
    from PySide6.QtWidgets import QMessageBox

    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **kw: warnings.append(a)),
    )
    old_store = win.store

    try:
        win.sidebar.account_combo.activated.emit(99)  # 越界 index → 空文本（非法名）

        assert warnings  # 非法名（空）给可读提示（F-P1 防御分支）
        assert win.current_account == "主账号"
        assert win.store is old_store
    finally:
        win.close()


def test_switch_does_not_touch_profit_page(account_window_factory):
    """利润页零改动：切换不重建 profit_page、不触碰其状态。"""
    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    before = win.profit_page

    try:
        _select_account(win, "小号")

        assert win.profit_page is before  # 同一对象，未被触碰
    finally:
        win.close()


def test_switch_rejects_illegal_account_with_warning(account_window_factory, monkeypatch):
    """F-P1 防御：非法账号名（绕过列表过滤直接触发）→ 拒绝切换 + 可读提示 + 零写入。"""
    from PySide6.QtWidgets import QMessageBox

    dates = _two_account_dates()
    win, acc = account_window_factory(setup=lambda a: _two_account_env(a, dates))
    (acc.accounts_dir / ".dot").mkdir()  # 手工非法目录
    warnings = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        staticmethod(lambda *a, **kw: warnings.append(a)),
    )
    old_store = win.store

    try:
        win.sidebar.account_selected.emit(".dot")  # 直接 emit（绕过下拉过滤）

        assert warnings, "非法账号必须给出可读提示"
        assert win.current_account == "主账号"  # 不切换
        assert win.store is old_store  # 不重载
        assert not (acc.accounts_dir / ".dot" / "data.json").exists()  # 零写入
    finally:
        win.close()


def test_startup_combo_excludes_illegal_accounts(account_window_factory):
    """F-P1 一致性：启动后下拉列表不含非法目录（过滤与 resolve 兜底行为一致）。"""
    dates = _two_account_dates()

    def _setup(a):
        _two_account_env(a, dates)
        (a.accounts_dir / ".dot").mkdir()

    win, acc = account_window_factory(setup=_setup)

    try:
        items = [
            win.sidebar.account_combo.itemText(i)
            for i in range(win.sidebar.account_combo.count())
        ]
        assert ".dot" not in items
        assert win.current_account == "主账号"  # 解析兜底不受非法目录干扰
    finally:
        win.close()


# ── C1-08. 主题刷新契约（树遍历收集 + refresh_theme 解耦）──


def test_theme_refreshers_collected_at_startup(sample_window):
    """C1-08：_theme_refreshers 非空且含 sidebar/input_panel/chart/table/profit_page。"""
    win = sample_window
    refreshers = win._theme_refreshers
    assert refreshers, "启动期必须收集到主题刷新器"
    members = {id(w) for w in refreshers}
    for expected in (
        win.sidebar,
        win.input_panel,
        win.chart,
        win.table,
        win.profit_page,
        win.bonus_door_page,  # BD-03：密码门页具 apply_theme，自动纳入（C1-08 契约）
    ):
        assert id(expected) in members, f"{type(expected).__name__} 未入列"
    # 防双扇出：profit_page 入列时 crafting/exchange 不得重复入列
    assert id(win.profit_page.crafting_page) not in members, "crafting 不应重复入列"
    assert id(win.profit_page.exchange_page) not in members, "exchange 不应重复入列"


def test_theme_refreshers_cover_all_apply_theme_widgets(sample_window):
    """C1-08：树上任何具 apply_theme 的组件要么在集合中、要么其祖先在集合中（可证伪）。"""
    from PySide6.QtWidgets import QWidget

    win = sample_window
    collected = {id(w) for w in win._theme_refreshers}

    def covered(widget) -> bool:
        node = widget
        while node is not None:
            if id(node) in collected:
                return True
            node = node.parent()
        return False

    for widget in win.findChildren(QWidget):
        if hasattr(widget, "apply_theme"):
            assert covered(widget), (
                f"{type(widget).__name__} 具 apply_theme 但不在收集集合且无收集祖先"
            )


def test_refresh_theme_does_not_redraw_data(sample_window, monkeypatch):
    """C1-08：refresh_theme 不触发数据渲染路径（取数与摘要零调用）。

    MainWindow 层不得再直插数据渲染：_get_records 即取数入口、零调用即
    零新数据源；_update_summary / _update_today_status 同为数据路径。
    table.apply_theme 内部以缓存重绘（07 契约）不经过这三个入口。
    """
    win = sample_window
    calls: list[str] = []
    monkeypatch.setattr(
        win, "_get_records", lambda: (calls.append("_get_records"), [])[1]
    )
    monkeypatch.setattr(
        win, "_update_summary", lambda: calls.append("_update_summary")
    )
    monkeypatch.setattr(
        win, "_update_today_status", lambda: calls.append("_update_today_status")
    )
    win.refresh_theme()
    assert calls == [], f"refresh_theme 不应触碰数据渲染路径：{calls}"


def test_refresh_theme_source_has_no_data_redraw_calls():
    """C1-08 AST 防复发：refresh_theme 方法体不得访问 table.draw/_update_summary/_update_today_status。"""
    import ast
    import inspect

    import app.main_window as mw

    tree = ast.parse(inspect.getsource(mw))
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "refresh_theme":
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.Attribute)
                    and sub.attr in {"draw", "_update_summary", "_update_today_status"}
                ):
                    violations.append(f"L{sub.lineno}: refresh_theme 访问 {sub.attr}")
    assert violations == [], f"refresh_theme 不得触碰数据渲染路径：{violations}"


def test_kpi_styles_follow_theme_toggle(sample_window):
    """C1-08：主题切换后 KPI 磁贴数字颜色随主题变化（数值文本不受影响）。"""
    from app.theme import get_color

    win = sample_window
    text_before = win._summary_label.text()
    light_style = win._summary_label.styleSheet()

    win.sidebar.theme_btn.click()  # light → dark

    dark_style = win._summary_label.styleSheet()
    assert dark_style != light_style, "KPI 磁贴样式必须随主题变化"
    assert win._summary_label.text() == text_before, "数值文本不受主题切换影响"
    # dark 下样式含当前主题信号色（样本数据总盈亏为正 → FG_POS）
    assert get_color("FG_POS") in dark_style

    win.sidebar.theme_btn.click()  # dark → light 往返
    assert win._summary_label.styleSheet() == light_style


def test_kpi_signal_shared_pure_function():
    """AA-01：KPI 磁贴 signal 走共享纯函数 _kpi_signal（两处调用点单一来源）。

    信号判定语义与 format_window_text 对齐（spec：无数据/仅 1 条 → NONE，
    正/负/零 → POSITIVE/NEGATIVE/NEUTRAL）；期望值来自 spec 语义而非实现。
    """
    import inspect

    from app.main_window import _kpi_signal
    from signals import RateSignal

    # 无数据（total None）→ NONE；仅 1 条记录 → NONE
    assert _kpi_signal(0, None, "总盈亏", 7) is RateSignal.NONE
    assert _kpi_signal(1, 100.0, "总盈亏", 7) is RateSignal.NONE
    # 多记录：正 / 负 / 零
    assert _kpi_signal(2, 100.0, "总盈亏", 7) is RateSignal.POSITIVE
    assert _kpi_signal(2, -100.0, "总盈亏", 7) is RateSignal.NEGATIVE
    assert _kpi_signal(2, 0.0, "总盈亏", 7) is RateSignal.NEUTRAL
    # label/days 透传（现金磁贴同源）
    assert _kpi_signal(2, 50.0, "现金总变化", 30) is RateSignal.POSITIVE

    # 两处 signal 计算必须走同一函数（AA-01 验收：消除 Divergent Change；
    # C4 块 2 后计算点收敛到 KpiPresenter 的 update 渲染路径与主题换色路径）
    from app.kpi_presenter import KpiPresenter

    for method in ("_update_tile", "apply_theme_styles"):
        src = inspect.getsource(getattr(KpiPresenter, method))
        assert "_kpi_signal(" in src, f"{method} 未走共享 _kpi_signal"


def test_sidebar_themed_at_startup(sample_window):
    """C1-08 E2：启动期 sidebar 已应用当前主题（首帧样式 = 当前主题值，不依赖首次切换）。"""
    from app.theme import get_color

    win = sample_window
    assert get_color("MUTED_BG") in win.sidebar.styleSheet(), (
        "sidebar 首帧样式应为当前主题值（refreshers 启动期已应用）"
    )


# ── C1-09. 主题全链路抽查（light→dark→light 机械回归）────


def test_full_chain_theme_toggle_roundtrip(sample_window):
    """C1-09：light→dark→light 循环后各抽查组件样式含当前主题色值（与 get_color 比对）。

    覆盖全部渲染路径：exchange 包标签/分隔线、table 行按钮、sidebar、
    input 面板标签、chart 曲线——主题改动必须双主题×全路径回归。
    """
    from app.exchange_page import _PACKAGE_CONFIG
    from app.table_widget import COL_ACTIONS
    from app.theme import get_color

    win = sample_window
    exchange = win.profit_page.exchange_page
    actions = win.table._left_table.cellWidget(0, COL_ACTIONS)
    assert actions is not None, "表格行按钮未渲染（draw 未创建操作列）"

    def assert_chain_themed():
        for i, cfg in enumerate(_PACKAGE_CONFIG):
            assert get_color(cfg.color) in exchange._cards[i]._pkg_label.styleSheet(), (
                f"{cfg.color} 包标签未随主题（当前 {get_color(cfg.color)}）"
            )
            assert get_color("SEPARATOR") in exchange._cards[i]._sep.styleSheet(), (
                "分隔线未随主题"
            )
        assert get_color("BTN_BG") in actions._edit_btn.styleSheet(), "表格行按钮未随主题"
        assert get_color("MUTED_BG") in win.sidebar.styleSheet(), "sidebar 未随主题"
        assert get_color("FG_LABEL") in win.input_panel._cash_label.styleSheet(), (
            "输入面板标签未随主题"
        )
        curve = win.chart._warehouse_curve
        assert curve is not None, "仓库曲线未绘制"
        pen_color = curve.opts["pen"].color().name().lower()
        assert pen_color == get_color("CHART_WAREHOUSE").lower(), (
            f"图表曲线未随主题：{pen_color} != {get_color('CHART_WAREHOUSE')}"
        )

    assert_chain_themed()          # 初始 light
    win.sidebar.theme_btn.click()  # → dark
    assert_chain_themed()
    win.sidebar.theme_btn.click()  # → light（往返）
    assert_chain_themed()


# ── BD-03. 密码门装配（侧边栏第三导航 + QStackedWidget 第三页）──


def test_bonus_door_nav_item_is_third(sample_window):
    """BD-03：侧边栏第三导航项「密码门」（IC-02：图标走 QIcon 不拼文案）。"""
    win = sample_window
    assert len(win.sidebar.NAV_ITEMS) == 3
    assert win.sidebar.NAV_ITEMS[2] == "密码门"
    assert win.sidebar._NAV_ICONS[2] == "key"


def test_bonus_door_page_assembled_as_third_stack_page(sample_window):
    """BD-03：MainWindow 装配——bonus_door_page 存在、stack 第三页、共享同一 client。"""
    win = sample_window
    assert hasattr(win, "bonus_door_page")
    assert win._stack.count() == 3
    assert win._stack.widget(2) is win.bonus_door_page
    # C2-02 惯例：与利润页共享同一注入 client 实例
    assert win.bonus_door_page._client is win.profit_page.crafting_page._client
    assert win.bonus_door_page._client is win._client


def test_bonus_door_nav_switch_shows_page2(sample_window):
    """BD-03：nav_changed 索引 2 → QStackedWidget 切到第三页（密码门）。"""
    win = sample_window
    win.show()
    win.sidebar.set_current_index(2)
    assert win._stack.currentIndex() == 2
    assert win._stack.currentWidget() is win.bonus_door_page
    # 切回记账页仍正常
    win.sidebar.set_current_index(0)
    assert win._stack.currentIndex() == 0


def test_bonus_door_page_preloaded_on_startup(qapp, settings_guard, tmp_path):
    """BD-03：启动预加载走 _preload_data_pages（利润页 + 密码门页，C2-02 单出口）。"""
    import time

    from PySide6.QtTest import QTest

    from app.main_window import MainWindow
    from calculator import ProfitCalculatorLogic
    from data_store import DataStore
    from kkrb_client import BonusDoorItem
    from tests.conftest import make_stub_client

    win = MainWindow(
        store=DataStore(tmp_path / "d.json", tmp_path / "d.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
        client=make_stub_client(
            bonus_impl=lambda: [
                BonusDoorItem("db", "零号大坝", "870140", "20260813000000"),
            ]
        ),
    )
    win.show()

    def wait_loaded(page, timeout_ms: int = 5000) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            QTest.qWait(50)
            qapp.processEvents()
            if page.is_loaded:
                return True
        return False

    assert wait_loaded(win.bonus_door_page)
    assert win.bonus_door_page._cards[0]._map_label.text() == "零号大坝"
    win.close()


def test_bonus_door_preload_single_exit_via_main_window(qapp, settings_guard, tmp_path):
    """BD-03：_preload_data_pages 单出口扇出——spy 断言 bonus_door_page.preload 被调。"""
    from types import SimpleNamespace

    from app.main_window import MainWindow

    win = MainWindow(
        store=DataStore(tmp_path / "d.json", tmp_path / "d.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
        client=SimpleNamespace(),
    )
    calls: list[str] = []
    win.profit_page.preload = lambda: calls.append("profit")  # type: ignore[method-assign]
    win.bonus_door_page.preload = lambda: calls.append("bonus")  # type: ignore[method-assign]
    win._preload_data_pages()
    assert calls == ["profit", "bonus"]
    win.close()


def test_bonus_door_page_shutdown_on_close(sample_window, monkeypatch):
    """BD-03：closeEvent 回收密码门页后台线程（T-01 同款：shutdown 被调用）。"""
    win = sample_window
    calls: list[str] = []
    monkeypatch.setattr(
        win.bonus_door_page, "shutdown", lambda: calls.append("shutdown")
    )
    win.close()
    assert calls == ["shutdown"]


def test_bonus_door_page_exported_from_app_package():
    """BD-03：app/__init__ 导出 BonusDoorPage。"""
    from app import BonusDoorPage  # noqa: F401

    assert BonusDoorPage.__name__ == "BonusDoorPage"

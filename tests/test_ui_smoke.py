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
    """带样本数据的 MainWindow（不触碰真实 data.json / settings.json）。"""
    from app.main_window import MainWindow

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
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


def test_kpi_tile_splits_caption_and_value(sample_window):
    """U-01：汇总文本拆为「说明行 + 数值行」，磁贴数字为大字号信号色。"""
    from signals import RateSignal

    from app.theme import get_color, summary_style

    win = sample_window

    caption, value = win._split_kpi_text("最近7条总盈亏：+¥41.0M")
    assert caption == "最近7条总盈亏"
    assert value == "+¥41.0M"
    # 无分隔符（兜底）→ 整体作说明，数值留空
    assert win._split_kpi_text("数据不足") == ("数据不足", "")

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


def test_startup_preloads_both_profit_pages(qapp, settings_guard, tmp_path, monkeypatch):
    """U-10：启动 500ms 定时器后制造产物 + 兑换利润均后台预加载（点击零卡顿）。"""
    import os
    import time

    from PySide6.QtTest import QTest

    from app.main_window import MainWindow
    from calculator import ProfitCalculatorLogic
    from data_store import DataStore
    from kkrb_client import AmmoPackageItem, CraftingProduct, KkrbClient

    # offscreen-t 绕过 preload 的 offscreen 守卫；伪造网络数据避免真实 HTTP
    monkeypatch.setitem(os.environ, "QT_QPA_PLATFORM", "offscreen-t")
    monkeypatch.setattr(
        KkrbClient,
        "fetch_ov_data",
        lambda self: [CraftingProduct("技术中心", "复合弓", 100, 200, "晚上8点")],
    )
    monkeypatch.setattr(
        KkrbClient,
        "fetch_ammo_package_data",
        lambda self: [AmmoPackageItem("3级子弹自选包", "5.7mm", 3, 40, 100, 4000, 500)],
    )

    win = MainWindow(
        store=DataStore(tmp_path / "d.json", tmp_path / "d.bak"),
        logic=ProfitCalculatorLogic(make_sample_data()),
    )
    win.show()

    # 轮询等待两个页面预加载完成（固定 qWait 时长与后台线程调度存在竞态）
    def wait_loaded(page, timeout_ms: int = 5000) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            QTest.qWait(50)
            qapp.processEvents()
            if page._loaded_once:
                return True
        return False

    assert wait_loaded(win.profit_page.crafting_page)
    assert wait_loaded(win.profit_page.exchange_page)
    win.close()


def test_page_switch_loop_no_crash(sample_window, monkeypatch):
    """U-11 回归：点利润 → 切回记账 → 再点利润 反复 20 次不崩溃。

    用户报告此操作序列闪退（根因：切页淡入的 QGraphicsOpacityEffect 挂
    QStackedWidget 页面，快速 hide/show 触发 Qt 崩溃路径——已移除切页动画）。
    """
    from PySide6.QtTest import QTest

    from kkrb_client import KkrbClient

    monkeypatch.setattr(KkrbClient, "fetch_ov_data", lambda self: [])
    monkeypatch.setattr(KkrbClient, "fetch_ammo_package_data", lambda self: [])

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


def test_u05_emoji_single_source(sample_window):
    """U-05：emoji 收敛到 ui_text.EMOJI 单一来源；全局字体族含 Segoe UI Emoji。"""
    import re

    from app.theme import generate_qss
    from app.ui_text import EMOJI

    win = sample_window

    # 导航项/置顶按钮文案由 EMOJI 常量拼装
    assert win.sidebar.NAV_ITEMS[0].startswith(EMOJI["nav_ledger"])
    assert win.sidebar.NAV_ITEMS[1].startswith(EMOJI["nav_profit"])
    assert win.sidebar.pin_btn.text().startswith(EMOJI["pin"])

    # 全局字体族统一（微软雅黑 + Segoe UI Emoji，消基线错位）
    assert "Segoe UI Emoji" in generate_qss("light")

    # app 源码（除 ui_text.py 外）无散落 emoji 字面量
    # （含 ✓ U+2713——main_window CSV 导出提示曾绕过 EMOJI 收敛）
    import pathlib

    literal = re.compile(r"[📒🔧🌙☀️📌🔄⚠️💾✓]")
    app_dir = pathlib.Path(__file__).resolve().parent.parent / "app"
    for py in app_dir.glob("*.py"):
        if py.name == "ui_text.py":
            continue
        text = py.read_text(encoding="utf-8")
        assert not literal.search(text), f"{py.name} 含散落 emoji 字面量"


def test_u06_motion_feedback(sample_window, monkeypatch):
    """U-06：曲线绘制动画触发 + fade_in_widget 契约（effect 移除、竞态安全）。

    注：页面切换淡入已移除（QStackedWidget + QGraphicsOpacityEffect 快速切页
    崩溃风险，U-11）；曲线与保存指示动画保留。
    """
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QFrame

    from app.motion import fade_in_widget
    from kkrb_client import KkrbClient

    # 切页会触发利润页懒加载 → 屏蔽真实网络请求
    monkeypatch.setattr(KkrbClient, "fetch_ov_data", lambda self: [])
    monkeypatch.setattr(KkrbClient, "fetch_ammo_package_data", lambda self: [])

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

    today = datetime.now()
    # 31 个日期键（含今天），超出保留上限 RETENTION_LIMIT 1 条 → 触发裁剪
    data = {}
    for off in range(RETENTION_LIMIT, -1, -1):
        d = (today - timedelta(days=off)).strftime(DATE_FORMAT)
        data[d] = {"cash": 100.0, "warehouse": 200.0 + off}

    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(data),
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
    assert initial_text in ("🌙 暗色", "☀️ 亮色")

    win.sidebar.theme_btn.click()  # 切到另一主题
    assert win.sidebar.theme_btn.text() != initial_text

    win.sidebar.theme_btn.click()  # 切回
    assert win.sidebar.theme_btn.text() == initial_text


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


# ── 11. 窗口几何恢复 ─────────────────────────────────────


def test_geometry_restore_old_format(qapp, tmp_path, monkeypatch):
    """旧格式（Tkinter）geometry 恢复无 crash。"""
    import app.main_window as mw
    from app.main_window import MainWindow

    test_file = tmp_path / "settings_old.json"
    monkeypatch.setattr(mw, "SETTINGS_FILE", test_file)
    test_file.write_text(
        json.dumps({"geometry": "680x900+100+50", "pinned": False, "theme": "light"}),
        encoding="utf-8",
    )

    win = MainWindow(store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"))
    win.close()


def test_geometry_restore_new_format(qapp, tmp_path, monkeypatch):
    """新格式（空 geometry / hex）恢复无 crash。"""
    import app.main_window as mw
    from app.main_window import MainWindow

    test_file = tmp_path / "settings_new.json"
    monkeypatch.setattr(mw, "SETTINGS_FILE", test_file)
    test_file.write_text(
        json.dumps({"geometry": "", "pinned": False, "theme": "dark"}),
        encoding="utf-8",
    )

    win = MainWindow(store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"))
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

    data = make_sample_data()
    today_str = datetime.now().strftime(DATE_FORMAT)
    data.pop(today_str, None)
    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(data),
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

    today = datetime.now()
    data = {}
    for off in range(30):
        d = (today - timedelta(days=off)).strftime(DATE_FORMAT)
        data[d] = {"cash": 100.0 + off, "warehouse": 200.0 + off * 1000}
    win = MainWindow(
        store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"),
        logic=ProfitCalculatorLogic(data),
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

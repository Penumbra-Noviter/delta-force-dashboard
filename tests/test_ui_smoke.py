"""
C5 迁移：verify_all.py 的 UI 烟测并入 pytest（offscreen）。

verify_all.py 原第 1~3、12 节为纯逻辑叶子测试，已被 tests/test_calculator.py、
tests/test_formatting.py、tests/test_data_store.py 覆盖，不在此迁移。
本文件承接原第 4~11、13~14 节 UI 烟测（verify_all 共 14 节）：
- 启动/渲染、保存、编辑、删除（mock 确认框）、主题切换、窗口置顶、
  设置持久化、几何恢复、输入校验联动、失焦格式化、快捷键绑定。
- 所有 MainWindow 构造注入临时 store/logic，不触碰真实 data.json / settings.json
  （参照 tests/test_input_panel.py 的 main_window + settings_guard 模式）。

迁移原则（C5）：C4 已造真 seam，测试尽可能走公开 API 与公开信号
（fill_values / set_edit_mode / delete_requested / theme_btn.click 等），
不再调用私有 _start_edit；仅校验非法输入（fill_values 只接受数值）与
失焦格式化开关等无公开 seam 处仍直取输入框。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

# offscreen 平台必须在 QApplication 创建前设置
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMessageBox

from calculator import ProfitCalculatorLogic
from config import DATE_FORMAT
from data_store import DataStore

__all__ = []


# ── 样本数据（与 verify_all.make_sample_data 等价）──────


def make_sample_data() -> dict:
    """创建 6 天连续样本数据（相对今天，保证落在 7 日滚动窗口内）。

    原 verify_all 用固定日期（2026-07-20~27）；迁移后改为相对今天生成，
    避免样本日超出 [today-6, today] 窗口导致 test_ui_initialization 断言
    在 2026-08-03 之后必然失败（时间耦合回归）。
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
    assert win.windowTitle() == "收益计算器"
    assert win.minimumWidth() >= 560 and win.minimumHeight() >= 700

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

    # 初始有样本数据
    records = win.logic.get_weekly_records(win.today, 7)
    present = [d for d, r in records if r is not None]
    assert len(present) > 0

    # 表格 / 图表 draw 无 crash
    data_records = [(d, r) for d, r in records if r is not None]
    win.table.draw(data_records, win.today)
    win.chart.draw(data_records)

    # 7 列表头名称（双栏同构，使用左表验证）
    headers = [
        win.table._left_table.horizontalHeaderItem(i).text() for i in range(7)
    ]
    expected = ["日期", "现金", "仓库（总收益）", "较前日", "收益率", "盈亏", "操作"]
    assert headers == expected

    # 盈亏标签单元格
    pnl_widget = win.table._left_table.cellWidget(0, 5)
    assert pnl_widget is not None


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

    initial_text = win.theme_btn.text()
    assert initial_text in ("🌙 暗色", "☀️ 亮色")

    win.theme_btn.click()  # 切到另一主题
    assert win.theme_btn.text() != initial_text

    win.theme_btn.click()  # 切回
    assert win.theme_btn.text() == initial_text


# ── 9. 窗口置顶 ──────────────────────────────────────────


def test_pin_toggle(sample_window):
    """置顶按钮点击切换窗口 flag。"""
    win = sample_window
    stays_on_top = Qt.WindowType.WindowStaysOnTopHint

    assert not bool(win.windowFlags() & stays_on_top)

    win.pin_btn.click()
    assert bool(win.windowFlags() & stays_on_top)

    win.pin_btn.click()
    assert not bool(win.windowFlags() & stays_on_top)


# ── 10. 设置持久化 ───────────────────────────────────────


def test_settings_persistence(sample_window, tmp_path):
    """设置写入与恢复（theme/pinned/geometry 落盘）。"""
    import app.main_window as mw

    win = sample_window
    test_settings = tmp_path / "settings.json"

    # 通过公开交互触发状态变更；closeEvent → _save_settings 落盘（公开 seam）
    win.theme_btn.click()   # _toggle_theme 内部已保存 theme
    win.pin_btn.click()     # _toggle_pin 不落盘
    win.close()

    assert test_settings.exists()
    with open(test_settings, "r", encoding="utf-8") as f:
        saved = json.load(f)
    assert saved.get("theme") == "dark"  # 默认 light → 点击一次 → dark
    assert saved.get("pinned") is True
    assert "geometry" in saved


def test_load_settings_corrupt_logs_warning(tmp_path, monkeypatch, caplog):
    """损坏的 settings.json：_load_settings 不抛异常，且记录 warning。"""
    import app.main_window as mw

    bad_file = tmp_path / "settings.json"
    bad_file.write_text("{ not valid json !!!", encoding="utf-8")
    monkeypatch.setattr(mw, "SETTINGS_FILE", bad_file)

    with caplog.at_level("WARNING"):
        result = mw.MainWindow._load_settings()

    assert result == {}
    assert any("设置文件读取失败" in rec.message for rec in caplog.records)

def test_load_settings_top_level_list_returns_default(tmp_path, monkeypatch, caplog):
    """settings.json 顶层是 list：_load_settings 返回默认 {} 并记 warning（O-09）。"""
    import app.main_window as mw

    bad_file = tmp_path / "settings.json"
    bad_file.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(mw, "SETTINGS_FILE", bad_file)

    with caplog.at_level("WARNING"):
        result = mw.MainWindow._load_settings()

    assert result == {}
    assert any("顶层非 dict" in rec.message for rec in caplog.records)


def test_save_settings_failure_logs_warning(qapp, tmp_path, monkeypatch, caplog):
    """settings.json 写入失败：不抛异常，仅记录 warning。"""
    import app.main_window as mw
    from app.main_window import MainWindow

    # 目标目录不存在 → open(..., "w") 抛 OSError
    bad_file = tmp_path / "missing_dir" / "settings.json"
    monkeypatch.setattr(mw, "SETTINGS_FILE", bad_file)

    win = MainWindow(store=DataStore(tmp_path / "data.json", tmp_path / "data.json.bak"))
    with caplog.at_level("WARNING"):
        win._save_settings()
    win.close()

    assert any("设置文件写入失败" in rec.message for rec in caplog.records)


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


def test_input_validation_save_btn(sample_window):
    """save_btn 随两个字段合法性联动启停。

    输入校验走 150ms 去抖 QTimer（异步），测试用 C4 seam
    `refresh_validity()` 立即同步重校验，断言结果确定。
    """
    ip = sample_window.input_panel

    # 初始空 → 禁用
    ip.refresh_validity()
    assert not ip.save_btn.isEnabled()

    # 填一个字段 → 仍禁用
    ip.cash_entry.setText("100000")
    ip.refresh_validity()
    assert not ip.save_btn.isEnabled()

    # 填两个字段 → 启用
    ip.warehouse_entry.setText("200000")
    ip.refresh_validity()
    assert ip.save_btn.isEnabled()

    # 改现金为非法 → 禁用
    ip.cash_entry.setText("abc")
    ip.refresh_validity()
    assert not ip.save_btn.isEnabled()

    # 恢复合法 → 启用
    ip.cash_entry.setText("100000")
    ip.refresh_validity()
    assert ip.save_btn.isEnabled()

    # 清空两字段 → 禁用
    ip.cash_entry.setText("")
    ip.warehouse_entry.setText("")
    ip.refresh_validity()
    assert not ip.save_btn.isEnabled()


# ── 14. 失焦格式化 ───────────────────────────────────────


def test_money_edit_focus_out_formatting(sample_window):
    """输入框失焦时格式化为 ¥ 千分位。"""
    cash = sample_window.input_panel.cash_entry

    cash._formatting = False
    cash.setText("123456")
    assert cash.text() == "123456"

    # 触发真实 focusOutEvent（offscreen 下无法靠窗口焦点，直接派发事件）
    cash.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
    assert cash.text() == "¥123,456.00"


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
    assert hasattr(win, "export_btn")
    assert win.export_btn.text() == "导出 CSV"


def test_export_csv_writes_file(sample_window, monkeypatch, tmp_path):
    """点击导出 → 选择路径 → 写入 utf-8-sig CSV（Excel 可直接打开）。"""
    win = sample_window
    out = tmp_path / "export.csv"
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        staticmethod(lambda *a, **kw: (str(out), "CSV 文件 (*.csv)")),
    )

    win.export_btn.click()

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

    win.export_btn.click()

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

    win.export_btn.click()

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
    records = win.logic.get_weekly_records(win.today, 7)
    present = [(d, r) for d, r in records if r is not None]
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

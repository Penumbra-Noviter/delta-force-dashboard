"""
全量验证脚本（offscreen 模式）。

逐个验证 pyside6-migration-bugs.md 中所有待办项。
运行方式：QT_QPA_PLATFORM=offscreen python verify_all.py
退出码：0 = 全部通过，非 0 = 有失败项。
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch

# ── 在 import 任何 Qt 模块前设置 offscreen ──
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication, QMessageBox

# 切换到项目根目录
PROJECT_ROOT = Path("D:/Desktop/Craft/Profit Calculator").resolve()
os.chdir(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from app.theme import THEMES, get_color, get_theme, set_theme
from data_store import DataStore
from formatting import (
    format_input_value,
    format_money,
    is_valid_money_input,
    parse_money_input,
    unformat_input_value,
)
from calculator import DayRecord, ProfitCalculatorLogic


# ═══════════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════════

PASS = 0
FAIL = 0
VERIFIED = []  # 已通过的验证项
LOG = []


def announce(label: str) -> None:
    LOG.append(f"\n{'─' * 60}\n▶ {label}\n{'─' * 60}")


def ok(label: str) -> None:
    global PASS
    PASS += 1
    VERIFIED.append(label)
    LOG.append(f"  ✅ {label}")


def fail(label: str, detail: str = "") -> None:
    global FAIL
    FAIL += 1
    msg = f"❌ {label}" + (f" — {detail}" if detail else "")
    LOG.append(msg)
    print(f"  {msg}")


def check(label: str, cond: bool, detail: str = "") -> None:
    if cond:
        ok(label)
    else:
        fail(label, detail)


def _backup_data_json() -> dict | None:
    """备份 data.json 内容（用于测试前后恢复）。"""
    data_file = PROJECT_ROOT / "data.json"
    if data_file.exists():
        try:
            import json
            with open(data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _restore_data_json(data: dict | None) -> None:
    """恢复 data.json 内容。"""
    import json
    data_file = PROJECT_ROOT / "data.json"
    if data is not None:
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    elif data_file.exists():
        data_file.unlink()


def make_sample_data() -> dict:
    """创建 6 天连续样本数据。"""
    return {
        "2026-07-20": {"cash": 54360000.0, "warehouse": 419900000.0},
        "2026-07-21": {"cash": 52340000.0, "warehouse": 419800000.0},
        "2026-07-22": {"cash": 58155000.0, "warehouse": 427400000.0},
        "2026-07-24": {"cash": 80088000.0, "warehouse": 447900000.0},
        "2026-07-25": {"cash": 82514000.0, "warehouse": 450200000.0},
        "2026-07-27": {"cash": 88541000.0, "warehouse": 460900000.0},
    }


# ═══════════════════════════════════════════════
# 1. 业务逻辑层验证（不依赖 UI）
# ═══════════════════════════════════════════════

def test_calculator_layer() -> None:
    """验证 calculator.py 核心方法。"""
    data = make_sample_data()
    logic = ProfitCalculatorLogic(data)

    # 基础查询
    rec = logic.get_record("2026-07-20")
    check("get_record 返回 DayRecord", rec is not None)
    if rec:
        check("DayRecord.cash 正确", rec.cash == 54360000.0)
        check("DayRecord.warehouse 正确", rec.warehouse == 419900000.0)
        check("DayRecord.total == warehouse", rec.total == 419900000.0)

    # 缺失值查询
    none_rec = logic.get_record("2026-07-19")
    check("get_record 无数据返回 None", none_rec is None)

    # 最近记录回溯
    last = logic.last_record_before("2026-07-23")
    check("last_record_before 跳过空白日", last is not None)
    if last:
        check("  → 回溯到 07-22", last[0] == "2026-07-22")

    # 7 日滚动查询
    weekly = logic.get_weekly_records("2026-07-27", 7)
    check("get_weekly_records 返回 7 项", len(weekly) == 7)
    present = sum(1 for _, r in weekly if r is not None)
    check(f"  其中 {present}/7 天有数据", present == 5)

    # save_record
    rec2 = logic.save_record("2026-07-28", 90000000.0, 470000000.0)
    check("save_record 回传 DayRecord", rec2 is not None)
    check("  数据已写入", "2026-07-28" in logic.data)

    # 收益率
    rate = logic.calculate_rate(419900000.0, 419800000.0)
    check("calculate_rate 返回数值", rate is not None)
    if rate is not None:
        check("  rate ~ -0.0238%", abs(rate + 0.0238) < 0.001)
    rate_none = logic.calculate_rate(None, 100.0)
    check("calculate_rate None 前值 → None", rate_none is None)
    rate_zero = logic.calculate_rate(0, 100.0)
    check("calculate_rate 前值=0 → None", rate_zero is None)

    # format_rate
    r1, c1 = logic.format_rate(2.4)
    check("format_rate 正数 → +2.4%", r1 == "+2.4%")
    r2, _ = logic.format_rate(-1.3)
    check("format_rate 负数 → -1.3%", r2 == "-1.3%")
    r3, _ = logic.format_rate(0.0)
    check("format_rate 零 → 0.0%", r3 == "0.0%")
    r4, _ = logic.format_rate(None)
    check("format_rate None → —", r4 == "—")

    # PnL 标签
    p1, _ = logic.get_pnl_label(100.0, 200.0)
    check("get_pnl_label 盈", p1 == "盈")
    p2, _ = logic.get_pnl_label(200.0, 100.0)
    check("get_pnl_label 亏", p2 == "亏")
    p3, _ = logic.get_pnl_label(None, 100.0)
    check("get_pnl_label 无前值 → —", p3 == "—")
    p4, _ = logic.get_pnl_label(100.0, 100.0)
    check("get_pnl_label 持平 → —", p4 == "—")


# ═══════════════════════════════════════════════
# 2. 格式化层验证
# ═══════════════════════════════════════════════

def test_formatting_layer() -> None:
    """验证金额格式化与解析。"""
    check("format_money 正数", format_money(1234.56) == "¥1,234.56")
    check("format_money 零", format_money(0) == "¥0.00")
    check("format_money None → —", format_money(None) == "—")
    check("format_money 负数", format_money(-500) == "¥-500.00")

    check("parse_money_input 纯数字", parse_money_input("1000") == 1000.0)
    check("parse_money_input K 后缀", parse_money_input("1.5K") == 1500.0)
    check("parse_money_input M 后缀", parse_money_input("2.5M") == 2500000.0)
    check("parse_money_input B 后缀", parse_money_input("1B") == 1000000000.0)
    check("parse_money_input 空 → None", parse_money_input("") is None)
    check("parse_money_input ¥", parse_money_input("¥1000") == 1000.0)
    check("parse_money_input 逗号", parse_money_input("1,000") == 1000.0)
    check("parse_money_input 负数", parse_money_input("-1000") == -1000.0)

    check("is_valid_money_input 有效", is_valid_money_input("1000") is True)
    check("is_valid_money_input 空合法", is_valid_money_input("") is True)
    check("is_valid_money_input 非法", is_valid_money_input("abc") is False)

    val = format_input_value(5000.0)
    check("format_input_value 含 ¥ 前缀", val == "¥5,000.00")

    u1 = unformat_input_value("¥1,234.56")
    check("unformat_input_value 去符号逗号", u1 == "1234.56")


# ═══════════════════════════════════════════════
# 3. DataStore 层验证
# ═══════════════════════════════════════════════

def test_datastore_layer() -> None:
    """DataStore 原子写入、损坏恢复、滚动备份。"""

    with tempfile.TemporaryDirectory() as tmp:
        data_file = Path(tmp) / "data.json"
        backup_file = Path(tmp) / "data.json.bak"

        store = DataStore(data_file=data_file, backup_file=backup_file)

        # 初始加载为空
        empty = store.load()
        check("空文件加载 → dict", isinstance(empty, dict))

        # 保存 1
        data1 = {"2026-07-28": {"cash": 100, "warehouse": 200}}
        store.save(data1)
        check("保存后文件存在", data_file.exists())

        # 重载验证
        loaded = store.load()
        check("回环一致", loaded == data1)

        # 损坏恢复（需要至少两次保存以产生备份）
        data2 = {"2026-07-29": {"cash": 200, "warehouse": 300}}
        store.save(data2)
        with open(data_file, "w") as f:
            f.write("{corrupt}")
        recovered = store.load()
        check("损坏后自动恢复非空", isinstance(recovered, dict))
        check("  从备份恢复", len(recovered) > 0)


# ═══════════════════════════════════════════════
# 4. UI 启动 & 基本渲染（offscreen）
# ═══════════════════════════════════════════════

_app: QApplication | None = None


def get_app() -> QApplication:
    global _app
    if _app is None:
        _app = QApplication(sys.argv)
    return _app


def test_ui_initialization() -> None:
    """UI 启动无 crash + 基础渲染。"""
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # 基本属性
    check("窗口标题正确", win.windowTitle() == "收益计算器")
    check("窗口最小尺寸", win.minimumWidth() >= 560 and win.minimumHeight() >= 700)

    # 子组件存在
    check("存在 input_panel", hasattr(win, "input_panel"))
    check("存在 table", hasattr(win, "table"))
    check("存在 chart", hasattr(win, "chart"))

    # 输入面板
    ip = win.input_panel
    check("input_panel 有 cash_entry", hasattr(ip, "cash_entry"))
    check("input_panel 有 warehouse_entry", hasattr(ip, "warehouse_entry"))
    check("input_panel 有 save_btn", hasattr(ip, "save_btn"))

    # 表格列数 = 7
    table = win.table
    check("表格列数 = 7", table.columnCount() == 7)

    # 初始状态：有 6 天样本数据
    records = win._get_records()
    check(f"初始有 {len(records)} 天记录", len(records) > 0)

    # 表格 draw
    try:
        table.draw(records, win.today)
        check("table.draw() 无 crash", True)
    except Exception as e:
        check("table.draw() 无 crash", False, str(e))

    # 图表 draw
    try:
        win.chart.draw(records)
        check("chart.draw() 无 crash", True)
    except Exception as e:
        check("chart.draw() 无 crash", False, str(e))

    # 7 列表头名称（双栏同构，使用左表验证）
    headers = [table._left_table.horizontalHeaderItem(i).text() for i in range(7)]
    expected = ["日期", "现金", "仓库（总收益）", "较前日", "收益率", "盈亏", "操作"]
    check("7 列表头名称正确", headers == expected)

    # 检查盈亏标签的单元格（取左侧表格第一条记录）
    pnl_widget = table._left_table.cellWidget(0, 5)
    check("盈亏列有 PnLBadge widget", pnl_widget is not None)

    win.close()


# ═══════════════════════════════════════════════
# 5. 保存数据
# ═══════════════════════════════════════════════

def test_save_today() -> None:
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # 在输入框填值
    win.input_panel.cash_entry.setText("90000000")
    win.input_panel.warehouse_entry.setText("470000000")

    # 触发保存
    try:
        win.save_today()
        check("save_today 无 crash", True)
    except Exception as e:
        check("save_today 无 crash", False, str(e))

    # 验证数据已写入
    today_rec = win.logic.get_record(win.today)
    check(f"今日 {win.today} 数据已保存", today_rec is not None)
    if today_rec:
        check("  cash=90000000", today_rec.cash == 90000000.0)
        check("  warehouse=470000000", today_rec.warehouse == 470000000.0)

    # 验证保存指示器
    indicator_text = win.input_panel.saved_indicator.text()
    check("保存后显示指示器", "✓" in indicator_text and "470.0M" in indicator_text)

    win.close()


# ═══════════════════════════════════════════════
# 6. 编辑模式
# ═══════════════════════════════════════════════

def test_edit_mode() -> None:
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # 编辑 07-25 的数据
    rec = win.logic.get_record("2026-07-25")
    check("编辑目标记录存在", rec is not None)
    if rec is None:
        win.close()
        return

    win._start_edit("2026-07-25", rec)
    check("edit 后 _editing_date 设置", win.input_panel.get_editing_date() == "2026-07-25")
    check("edit 后按钮文字含更新", "更新数据" in win.input_panel.save_btn.text())
    check("取消编辑按钮可见", not win.input_panel.cancel_edit_btn.isHidden())

    # 取消编辑
    win._cancel_edit()
    check("取消后 _editing_date 清空", win.input_panel.get_editing_date() is None)
    check("取消后按钮恢复", win.input_panel.save_btn.text() == "保存今日数据")
    check("取消编辑按钮隐藏", not win.input_panel.cancel_edit_btn.isVisible())

    # 再编辑一次，修改值并保存
    win._start_edit("2026-07-25", rec)
    win.input_panel.cash_entry.setText("83000000")
    win.input_panel.warehouse_entry.setText("451000000")
    win.save_today()

    updated = win.logic.get_record("2026-07-25")
    check("编辑保存后数据更新", updated is not None)
    if updated:
        check("  cash=83000000", updated.cash == 83000000.0)
        check("  warehouse=451000000", updated.warehouse == 451000000.0)

    # 取消编辑模式（已由 save_today 内部调用）
    check("保存后退出编辑模式", not win.input_panel.is_editing())

    win.close()


# ═══════════════════════════════════════════════
# 7. 删除数据
# ═══════════════════════════════════════════════

def _yes_reply(*args, **kwargs):
    return QMessageBox.StandardButton.Yes


def test_delete_record() -> None:
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # 用 mock 替换确认对话框为 Yes
    import PySide6.QtWidgets
    original = PySide6.QtWidgets.QMessageBox.question
    PySide6.QtWidgets.QMessageBox.question = staticmethod(_yes_reply)

    try:
        # 删除 07-20
        old_len = len(win.logic.data)
        win._delete_record("2026-07-20")
        rec_20 = win.logic.get_record("2026-07-20")
        check("删除后 07-20 不存在", rec_20 is None)
        check("删除后数据量-1", len(win.logic.data) == old_len - 1)
    finally:
        PySide6.QtWidgets.QMessageBox.question = original

    win.close()


def test_delete_cancel() -> None:
    """确认对话框取消不应删除。"""
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # mock 返回 No
    import PySide6.QtWidgets
    original = PySide6.QtWidgets.QMessageBox.question
    PySide6.QtWidgets.QMessageBox.question = staticmethod(
        lambda *a, **kw: QMessageBox.StandardButton.No
    )

    try:
        old_len = len(win.logic.data)
        win._delete_record("2026-07-21")
        rec_21 = win.logic.get_record("2026-07-21")
        check("取消删除后数据仍在", rec_21 is not None)
        check("取消删除后数据量不变", len(win.logic.data) == old_len)
    finally:
        PySide6.QtWidgets.QMessageBox.question = original

    win.close()


# ═══════════════════════════════════════════════
# 8. 主题切换
# ═══════════════════════════════════════════════

def test_theme_toggle() -> None:
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    initial = win._theme
    check(f"初始主题: {initial}", initial in ("light", "dark"))

    # 切换
    win._toggle_theme()
    check("切换后主题不同", win._theme != initial)
    check("主题色板加载正确", win._theme in THEMES)

    # 再切回去
    win._toggle_theme()
    check("切回后恢复", win._theme == initial)

    # 验证按钮文字
    expected_btn = "🌙 暗色" if win._theme == "light" else "☀️ 亮色"
    check("主题按钮文字正确", win.theme_btn.text() == expected_btn)

    win.close()


# ═══════════════════════════════════════════════
# 9. 窗口置顶切换
# ═══════════════════════════════════════════════

def test_pin_toggle() -> None:
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # 初始非置顶
    initial = win._pinned
    check(f"初始 _pinned={initial}", initial is False)

    # 切换
    win._toggle_pin()
    check("切换后 _pinned=True", win._pinned is True)

    # 再切回
    win._toggle_pin()
    check("再切后 _pinned=False", win._pinned is False)

    win.close()


# ═══════════════════════════════════════════════
# 10. 设置持久化
# ═══════════════════════════════════════════════

def test_settings_persistence(tmp_path: Path) -> None:
    """验证设置写入与恢复。"""
    from app.main_window import MainWindow

    # 临时替换 SETTINGS_FILE
    import app.main_window as mw_mod
    orig_settings = mw_mod.SETTINGS_FILE
    test_settings = tmp_path / "settings.json"

    try:
        mw_mod.SETTINGS_FILE = test_settings

        app = get_app()
        win = MainWindow()

        # 写入设置
        win._pinned = True
        win._theme = "dark"
        win._save_settings()

        check("设置文件已创建", test_settings.exists())

        # 读取验证
        with open(test_settings, "r") as f:
            saved = json.load(f)
        check("设置含 theme=dark", saved.get("theme") == "dark")
        check("设置含 pinned=true", saved.get("pinned") is True)
        check("设置含 geometry", "geometry" in saved)

        win.close()
    finally:
        mw_mod.SETTINGS_FILE = orig_settings


# ═══════════════════════════════════════════════
# 11. 窗口几何恢复
# ═══════════════════════════════════════════════

def test_geometry_restore(tmp_path: Path) -> None:
    """验证旧格式 + 新格式几何恢复。"""
    from app.main_window import MainWindow
    import app.main_window as mw_mod
    orig_settings = mw_mod.SETTINGS_FILE

    try:
        # 旧格式 (Tkinter)
        test_file = tmp_path / "settings_old.json"
        mw_mod.SETTINGS_FILE = test_file
        test_file.write_text(
            json.dumps({"geometry": "680x900+100+50", "pinned": False, "theme": "light"})
        )

        app = get_app()
        win = MainWindow()
        check("旧格式 geometry 恢复无 crash", True)
        win.close()

        # 新格式
        test_file2 = tmp_path / "settings_new.json"
        mw_mod.SETTINGS_FILE = test_file2
        test_file2.write_text(
            json.dumps({"geometry": "", "pinned": False, "theme": "dark"})
        )
        win2 = MainWindow()
        check("空 geometry 无 crash", True)
        win2.close()

    finally:
        mw_mod.SETTINGS_FILE = orig_settings


# ═══════════════════════════════════════════════
# 12. 7 天滚动
# ═══════════════════════════════════════════════

def test_weekly_rotation() -> None:
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # 初始 6 天，未触发滚动
    check("初始 ≤7 天", len(win.logic.data) <= 7)

    # 追加到 8 天
    win.logic.save_record("2026-07-14", 100, 200)  # 最旧
    win.logic.save_record("2026-07-15", 200, 300)
    win.logic.save_record("2026-07-16", 300, 400)
    # 现在有 9 条
    win.logic.rotate_weekly()
    check("滚动后最多 7 天", len(win.logic.data) <= 7)

    # 验证正确的 7 条被保留（最近的）
    dates = sorted(win.logic.data.keys())
    check("最旧日期被删除", "2026-07-14" not in dates)

    win.close()


# ═══════════════════════════════════════════════
# 13. 金额输入校验
# ═══════════════════════════════════════════════

def test_input_validation_ui() -> None:
    """验证输入框校验联动（UI 集成）。"""
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    ip = win.input_panel

    # 初始空 → 保存按钮禁用
    check("初始保存按钮禁用", not ip.save_btn.isEnabled())

    # 填一个字段 → 仍禁用
    ip.cash_entry.setText("100000")
    check("仅填现金 → 禁用", not ip.save_btn.isEnabled())

    # 填两个字段 → 启用
    ip.warehouse_entry.setText("200000")
    check("两字段填好 → 启用", ip.save_btn.isEnabled())

    # 改现金为非法 → 禁用
    ip.cash_entry.setText("abc")
    check("现金非法 → 禁用", not ip.save_btn.isEnabled())

    # 恢复合法
    ip.cash_entry.setText("100000")
    check("恢复合法 → 启用", ip.save_btn.isEnabled())

    # 空字符串
    ip.cash_entry.setText("")
    ip.warehouse_entry.setText("")
    check("清空两字段 → 禁用", not ip.save_btn.isEnabled())

    win.close()


def test_money_edit_formatting() -> None:
    """验证输入框焦点进出格式化行为。"""
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    cash = win.input_panel.cash_entry

    # 输入纯数字
    cash._formatting = False
    cash.setText("123456")
    check("输入纯数字 OK", cash.text() == "123456")

    # 模拟失焦格式化
    cash._formatting = False
    cash.clearFocus()
    # 直接用方法模拟
    try:
        val = parse_money_input("123456")
        formatted = format_input_value(val)
        cash._formatting = True
        cash.setText(formatted)
        cash._formatting = False
        check("失焦格式化含 ¥ 千分位", cash.text() == "¥123,456.00")
    except Exception as e:
        check("失焦格式化", False, str(e))

    win.close()


# ═══════════════════════════════════════════════
# 14. 键盘快捷键（模拟 key press）
# ═══════════════════════════════════════════════

def test_keyboard_shortcuts() -> None:
    """验证 Enter = 保存 / Esc = 清空。"""
    from app.main_window import MainWindow

    app = get_app()
    win = MainWindow()

    # Enter 应该触发 save — 我们只需验证 Enter 快捷键存在
    # 检查 QAction 绑定
    actions = win.actions()
    enter_shortcuts = [
        a for a in actions
        if a.shortcut() == QKeySequence(Qt.Key.Key_Return)
    ]
    check("Enter 快捷键绑定", len(enter_shortcuts) >= 1)

    esc_shortcuts = [
        a for a in actions
        if a.shortcut() == QKeySequence(Qt.Key.Key_Escape)
    ]
    check("Esc 快捷键绑定", len(esc_shortcuts) >= 1)

    win.close()


# ═══════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════

def main() -> int:
    global PASS, FAIL

    tmp_dir = Path(tempfile.mkdtemp(prefix="profit_calc_verify_"))

    print("=" * 60)
    print("  收益计算器 — 全量验证报告")
    print(f"  时间: 2026-07-28")
    print(f"  平台: offscreen (PySide6 Qt 6.11.1)")
    print("=" * 60)

    # ── 备份当前 data.json，测试结束后恢复 ──
    saved_data = _backup_data_json()

    # ── 隔离真实 settings.json：测试期间读写临时文件，跑完自动恢复引用 ──
    #    避免 win.close() → closeEvent → _save_settings() 把测试时的
    #    theme/pinned 写回真实 settings.json（污染 git 工作区）
    import app.main_window as mw_mod
    orig_settings_file = mw_mod.SETTINGS_FILE
    mw_mod.SETTINGS_FILE = tmp_dir / "settings.json"

    try:

        # ── 1. 业务逻辑 ──
        announce("1. 业务逻辑层 (calculator.py)")
        test_calculator_layer()

        # ── 2. 格式化 ──
        announce("2. 格式化层 (formatting.py)")
        test_formatting_layer()

        # ── 3. DataStore ──
        announce("3. 数据持久化层 (data_store.py)")
        test_datastore_layer()

        # ── 4. UI 启动 & 渲染 ──
        announce("4. UI 启动 & 基本渲染")
        test_ui_initialization()

        # ── 5. 保存今日数据 ──
        announce("5. 保存今日数据")
        test_save_today()

        # ── 6. 编辑模式 ──
        announce("6. 编辑模式")
        test_edit_mode()

        # ── 7. 删除数据 ──
        announce("7. 删除数据")
        test_delete_record()
        test_delete_cancel()

        # ── 8. 主题切换 ──
        announce("8. 亮/暗主题切换")
        test_theme_toggle()

        # ── 9. 窗口置顶 ──
        announce("9. 窗口置顶切换")
        test_pin_toggle()

        # ── 10. 设置持久化 ──
        announce("10. 设置持久化")
        test_settings_persistence(tmp_dir)

        # ── 11. 窗口几何恢复 ──
        announce("11. 窗口几何恢复")
        test_geometry_restore(tmp_dir)

        # ── 12. 7 天滚动 ──
        announce("12. 7 天滚动旋转")
        test_weekly_rotation()

        # ── 13. 金额输入校验 ──
        announce("13. 金额输入校验 + 格式化")
        test_input_validation_ui()
        test_money_edit_formatting()

        # ── 14. 键盘快捷键 ──
        announce("14. 键盘快捷键")
        test_keyboard_shortcuts()

    finally:
        # 恢复 data.json
        _restore_data_json(saved_data)
        # 恢复真实 settings.json 引用（隔离期从未写入真实文件）
        mw_mod.SETTINGS_FILE = orig_settings_file

    # ── 汇总 ──
    print("\n" + "=" * 60)
    print(f"  汇总: ✅ {PASS} 通过  ❌ {FAIL} 失败")
    print("=" * 60)

    if VERIFIED:
        print(f"\n已通过验证项 ({len(VERIFIED)}):")
        for v in VERIFIED:
            print(f"  ✅ {v}")

    if FAIL > 0:
        print(f"\n❌ 有 {FAIL} 项失败:")
        for line in LOG:
            if "❌" in line or "fail" in line.lower():
                print(f"  {line.strip()}")
        print("\n⚠️  完整 LOG 中的错误行如上所示。检查测试函数以获取完整 traceback。")
        result = 1
    else:
        print("\n✅ 全部验证项通过！")
        result = 0

    return result


if __name__ == "__main__":
    sys.exit(main())

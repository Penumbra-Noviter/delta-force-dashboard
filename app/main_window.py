"""
主窗口：PySide6 QMainWindow。

管理窗口初始化、组件协调、数据流、主题切换、置顶与几何持久化。
"""

from __future__ import annotations

__all__ = ["MainWindow"]

import json
import logging
import platform
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.chart_widget import ChartWidget
from config import (
    DATA_DIR,
    DATE_FORMAT,
    SETTINGS_FILE,
    WEEK_DAYS,
)
from app.theme import (
    generate_qss,
    get_color,
    set_theme,
    signal_color,
)
from app.input_panel import InputPanel
from app.table_widget import TableWidget
from data_store import DataStore
from formatting import format_money, format_short_date
from calculator import DayRecord, ProfitCalculatorLogic

logger = logging.getLogger(__name__)

# DPI scaling on Windows
if platform.system() == "Windows":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


class MainWindow(QMainWindow):
    """收益计算器主窗口。"""

    def __init__(self, store: DataStore | None = None,
                 logic: ProfitCalculatorLogic | None = None) -> None:
        super().__init__()

        self.store = store or DataStore()
        self.logic = logic or ProfitCalculatorLogic(self.store.load())
        self.today = datetime.now().strftime(DATE_FORMAT)
        self._pinned = False
        self._settings = self._load_settings()
        self._theme = self._settings.get("theme", "light")
        set_theme(self._theme)

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._apply_qss()

        # 初始渲染
        self.refresh_display()

        # 恢复置顶状态
        if self._settings.get("pinned", False):
            self._toggle_pin()

        self.input_panel.focus_cash()

    # ═══════════════════════════════════════════════════════
    # 窗口设置
    # ═══════════════════════════════════════════════════════

    def _setup_window(self) -> None:
        self.setWindowTitle("收益计算器")

        # 基础大小（双栏表格需更宽）
        base_w, base_h = 820, 920
        self.setMinimumSize(680, 700)

        # 恢复上次几何
        saved_geo = self._settings.get("geometry", "")
        geo_ok = False
        if saved_geo:
            try:
                # 新格式：hex-encoded QByteArray
                if isinstance(saved_geo, str):
                    raw = bytes.fromhex(saved_geo)
                    if raw and len(raw) > 4:
                        geo_ok = self.restoreGeometry(raw)
            except Exception:
                pass
            # 旧格式兼容（Tkinter geometry string: WxH+X+Y）
            if not geo_ok and isinstance(saved_geo, str) and "+" in saved_geo:
                try:
                    parts = saved_geo.replace("+", " ").replace("x", " ").split()
                    if len(parts) == 4:
                        self.resize(int(parts[0]), int(parts[1]))
                        self.move(int(parts[2]), int(parts[3]))
                        geo_ok = True
                except Exception:
                    pass

        if not geo_ok:
            self.resize(base_w, base_h)
            screen = QApplication.primaryScreen()
            if screen:
                rect = screen.availableGeometry()
                x = (rect.width() - base_w) // 2
                y = (rect.height() - base_h) // 2
                self.move(x, y)

    # ═══════════════════════════════════════════════════════
    # 设置持久化
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _load_settings() -> dict:
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
                logger.warning("设置文件顶层非 dict（使用默认设置）")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("设置文件读取失败（使用默认设置）: %s", e)
        return {}

    def _save_settings(self) -> None:
        geo_bytes = self.saveGeometry()
        settings = {
            "geometry": bytes(geo_bytes).hex(),
            "pinned": self._pinned,
            "theme": self._theme,
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("设置文件写入失败: %s", e)

    def closeEvent(self, event) -> None:
        # O-13：编辑/复用模式未保存时弹确认框，No 则拦截关窗，避免改动静默丢失
        if self.input_panel.is_editing() or self.input_panel.is_reusing():
            reply = QMessageBox.question(
                self,
                "确认退出",
                "当前有未保存的编辑（编辑/复用模式），确定退出？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        self._save_settings()
        super().closeEvent(event)

    # ═══════════════════════════════════════════════════════
    # 构建界面
    # ═══════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(32, 20, 32, 12)
        root_layout.setSpacing(0)

        # ── 标题栏 ──
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel("收益计算器")
        self._title_label.setObjectName("titleLabel")
        title_layout.addWidget(self._title_label)

        # 今日未录入提醒（只读检查，今日有记录时隐藏）
        self._today_status_label = QLabel("今日未录入")
        self._today_status_label.setObjectName("todayStatusLabel")
        title_layout.addWidget(self._today_status_label)

        title_layout.addStretch()

        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.clicked.connect(self._toggle_theme)
        title_layout.addWidget(self.theme_btn)

        self.pin_btn = QPushButton("📌 置顶")
        self.pin_btn.setObjectName("pinBtn")
        self.pin_btn.clicked.connect(self._toggle_pin)
        title_layout.addWidget(self.pin_btn)

        self.export_btn = QPushButton("导出 CSV")
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.setToolTip("将数据导出为 CSV 文件（Excel 可直接打开）")
        self.export_btn.clicked.connect(self._export_csv)
        title_layout.addWidget(self.export_btn)

        root_layout.addWidget(title_bar)

        # ── 日期 ──
        self._date_label = QLabel(self.today)
        self._date_label.setObjectName("dateLabel")
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root_layout.addSpacing(4)
        root_layout.addWidget(self._date_label)
        root_layout.addSpacing(12)

        # ── 输入面板（卡片容器）──
        input_card = self._build_card()
        input_card_layout = QVBoxLayout(input_card)
        input_card_layout.setContentsMargins(12, 10, 12, 10)
        self.input_panel = InputPanel()
        input_card_layout.addWidget(self.input_panel)
        root_layout.addWidget(input_card)
        root_layout.addSpacing(8)

        # ── 7日汇总条 ──
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("summaryLabel")
        self._summary_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        root_layout.addWidget(self._summary_label)
        root_layout.addSpacing(6)

        # ── 表格（卡片容器）──
        table_card = self._build_card()
        table_card_layout = QVBoxLayout(table_card)
        table_card_layout.setContentsMargins(12, 10, 12, 10)
        self.table = TableWidget()
        table_card_layout.addWidget(self.table)
        root_layout.addWidget(table_card)
        root_layout.addSpacing(8)

        # ── 图表（卡片容器）──
        chart_card = self._build_card()
        chart_card_layout = QVBoxLayout(chart_card)
        chart_card_layout.setContentsMargins(12, 10, 12, 10)
        self.chart = ChartWidget()
        chart_card_layout.addWidget(self.chart)
        root_layout.addWidget(chart_card, 1)
        root_layout.addSpacing(8)

        # ── 底部提示栏 ──
        self._hint_label = QLabel(
            "Enter 保存 ｜ Ctrl+A 全选 ｜ Esc 清空 ｜ "
            "支持 K/M/B 后缀（如 1.5K = 1,500）"
        )
        self._hint_label.setObjectName("hintLabel")
        root_layout.addWidget(self._hint_label)

        # 更新主题按钮文本
        self._update_theme_btn_text()

    def _build_card(self) -> QFrame:
        """构建带边框的卡片 QFrame。"""
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        return card

    def _update_theme_btn_text(self) -> None:
        self.theme_btn.setText(
            "🌙 暗色" if self._theme == "light" else "☀️ 亮色"
        )

    # ═══════════════════════════════════════════════════════
    # 信号连接
    # ═══════════════════════════════════════════════════════

    def _connect_signals(self) -> None:
        self.input_panel.save_requested.connect(self.save_today)
        self.input_panel.cancel_requested.connect(self._cancel_edit)
        self.input_panel.reuse_requested.connect(self._reuse_last_record)
        self.input_panel.reuse_cancel_requested.connect(self._cancel_reuse)
        self.table.edit_requested.connect(self._start_edit)
        self.table.delete_requested.connect(self._delete_record)

        # 键盘快捷键
        save_shortcut = QAction(self)
        save_shortcut.setShortcut(QKeySequence(Qt.Key.Key_Return))
        save_shortcut.triggered.connect(self.save_today)
        self.addAction(save_shortcut)

        # Ctrl+A 全选由 QLineEdit 原生支持

        # Esc 清空聚焦的输入框
        esc_shortcut = QAction(self)
        esc_shortcut.setShortcut(QKeySequence(Qt.Key.Key_Escape))
        esc_shortcut.triggered.connect(self._clear_focused_input)
        self.addAction(esc_shortcut)

    def _clear_focused_input(self) -> None:
        widget = QApplication.focusWidget()
        if hasattr(widget, "clear") and hasattr(widget, "text"):
            widget.clear()
            self.input_panel.refresh_validity()

    # ═══════════════════════════════════════════════════════
    # QSS 主题
    # ═══════════════════════════════════════════════════════

    def _apply_qss(self) -> None:
        qss = generate_qss(self._theme)
        self.setStyleSheet(qss)

    def _toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        set_theme(self._theme)
        self._apply_qss()
        self._update_theme_btn_text()
        self._update_pin_btn_style()
        self.input_panel.apply_theme()
        # 图表在主题切换后标记清除，下次 draw 重建
        self.chart.apply_theme()
        self.refresh_display()
        self._save_settings()

    # ═══════════════════════════════════════════════════════
    # 置顶
    # ═══════════════════════════════════════════════════════

    def _toggle_pin(self) -> None:
        self._pinned = not self._pinned
        self.setWindowFlags(
            self.windowFlags() ^ Qt.WindowType.WindowStaysOnTopHint
        )
        self.show()  # 必须重新 show 以应用 flags 变更
        self._update_pin_btn_style()

    def _update_pin_btn_style(self) -> None:
        """更新置顶按钮外观（仅在状态变化时触发 style polish）。"""
        if self._pinned:
            self.pin_btn.setText("📌 已置顶")
            if self.pin_btn.property("active") != "true":
                self.pin_btn.setProperty("active", "true")
                self.pin_btn.style().unpolish(self.pin_btn)
                self.pin_btn.style().polish(self.pin_btn)
        else:
            self.pin_btn.setText("📌 置顶")
            if self.pin_btn.property("active") == "true":
                self.pin_btn.setProperty("active", "false")
                self.pin_btn.style().unpolish(self.pin_btn)
                self.pin_btn.style().polish(self.pin_btn)

    # ═══════════════════════════════════════════════════════
    # 数据获取
    # ═══════════════════════════════════════════════════════

    def _get_records(self) -> list:
        """返回最近 WEEK_DAYS 条实际录入的 (date_str, DayRecord) 列表。"""
        return self.logic.recent_records(WEEK_DAYS)

    # ═══════════════════════════════════════════════════════
    # 保存
    # ═══════════════════════════════════════════════════════

    def save_today(self) -> None:
        cash_raw = self.input_panel.get_cash_raw()
        warehouse_raw = self.input_panel.get_warehouse_raw()

        try:
            cash = self.input_panel.get_cash_value()
        except ValueError as e:
            self._show_parse_error("当前现金", cash_raw, str(e))
            return

        try:
            warehouse = self.input_panel.get_warehouse_value()
        except ValueError as e:
            self._show_parse_error("仓库价值", warehouse_raw, str(e))
            return

        if cash is None or warehouse is None:
            missing = []
            if cash is None:
                missing.append(f"当前现金（输入: {cash_raw!r}）")
            if warehouse is None:
                missing.append(f"仓库价值（输入: {warehouse_raw!r}）")
            QMessageBox.warning(
                self,
                "提示",
                f"请填写完整数据\n{', '.join(missing)} 无法识别为有效金额",
            )
            return

        # 不变式：现金 ⊆ 仓库（仓库价值已含现金）。违反时拦截保存（O-08）。
        if cash > warehouse:
            QMessageBox.warning(
                self,
                "数据不合逻辑",
                "当前现金不能大于仓库价值。\n\n"
                f"现金: {format_money(cash)}\n"
                f"仓库: {format_money(warehouse)}\n\n"
                "仓库价值已包含现金，请检查输入。",
            )
            return

        save_date = self.input_panel.get_editing_date() or self.today
        self.logic.save_record(save_date, cash, warehouse)
        deleted = self.logic.rotate_weekly()
        self.store.save(self.logic.data)

        was_editing = self.input_panel.is_editing()
        if was_editing:
            self._cancel_edit()

        self.refresh_display()

        if save_date == self.today:
            indicator = f"✓ 今日已保存 — 仓库总收益 {format_money(warehouse)}"
        else:
            indicator = (
                f"✓ {format_short_date(save_date)} 已更新 — "
                f"仓库总收益 {format_money(warehouse)}"
            )
        if deleted:
            # O-14/O-17：保留策略按「录入条数」轮转（保留最近 WEEK_DAYS 条），文案如实表述
            indicator += f"（已保留最近 {WEEK_DAYS} 条记录，自动清理 {len(deleted)} 条较早记录）"
        self.input_panel.set_saved_indicator(indicator)

        # 非编辑模式保存后清空输入框并回焦，便于连续录入
        if not was_editing:
            self.input_panel.clear_fields()
            self.input_panel.cancel_reuse()

    @staticmethod
    def _show_parse_error(field: str, raw: str, detail: str) -> None:
        QMessageBox.warning(
            None,
            "输入格式错误",
            f"{field} 无法解析为有效数字。\n\n"
            f"输入值: {raw!r}\n"
            f"错误详情: {detail}\n\n"
            f"请使用纯数字、K/M/B 后缀或 ¥xxx 格式。",
        )

    # ═══════════════════════════════════════════════════════
    # 编辑 / 删除
    # ═══════════════════════════════════════════════════════

    def _start_edit(self, date_str: str, record: DayRecord) -> None:
        self.input_panel.cancel_reuse()
        self.input_panel.set_edit_mode(date_str, record.cash, record.warehouse)

    def _cancel_edit(self) -> None:
        self.input_panel.cancel_edit()

    def _reuse_last_record(self) -> None:
        """复用最近一条历史记录填入输入框，便于微调后保存。"""
        result = self.logic.last_record_before(self.today)
        if result is None:
            # 今日之前无数据，退而取今日本身（极少见）
            today_record = self.logic.get_record(self.today)
            if today_record is None:
                self.input_panel.set_saved_indicator("暂无可复用的历史数据")
                return
            self.input_panel.fill_values(today_record.cash, today_record.warehouse)
            self.input_panel.set_saved_indicator(
                f"已复用今日数据，请微调后保存"
            )
            self.input_panel.set_reuse_mode()
            return
        date_str, record = result
        self.input_panel.fill_values(record.cash, record.warehouse)
        self.input_panel.set_saved_indicator(
            f"已复用 {format_short_date(date_str)} 数据，请微调后保存"
        )
        self.input_panel.set_reuse_mode()

    def _cancel_reuse(self) -> None:
        """取消复用：清空输入框，恢复按钮为「复用昨日」。"""
        self.input_panel.clear_fields()
        self.input_panel.cancel_reuse()

    def _delete_record(self, date_str: str) -> None:
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除 {date_str} 的数据吗？\n\n"
            f"此操作不可撤销，但可通过备份文件恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.logic.delete_record(date_str)
        self.store.save(self.logic.data)

        if self.input_panel.get_editing_date() == date_str:
            self._cancel_edit()

        self.refresh_display()

    # ═══════════════════════════════════════════════════════
    # 导出 CSV
    # ═══════════════════════════════════════════════════════

    def _export_csv(self) -> None:
        """导出 CSV：QFileDialog 选路径，utf-8-sig 编码写入（Excel 可直接打开）。

        写入失败时提示用户并记录日志，不静默；取消选择时直接返回。
        """
        default_path = str(DATA_DIR / f"收益数据_{self.today}.csv")
        path, _ = QFileDialog.getSaveFileName(
            self, "导出 CSV", default_path, "CSV 文件 (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                f.write(self.logic.export_csv())
        except OSError as e:
            logger.error("CSV 导出失败（%s）: %s", path, e)
            QMessageBox.warning(
                self,
                "导出失败",
                f"无法写入文件：\n{path}\n\n{e}",
            )
            return
        logger.info("CSV 已导出：%s", path)
        self.input_panel.set_saved_indicator("✓ CSV 已导出")

    # ═══════════════════════════════════════════════════════
    # 刷新展示
    # ═══════════════════════════════════════════════════════

    def refresh_display(self) -> None:
        records = self._get_records()
        self._update_summary()
        self._update_today_status()
        self.table.draw(records, self.today)
        self.chart.draw(records)

    def _update_today_status(self) -> None:
        """更新「今日未录入」提醒：今日无记录时显示，有记录时隐藏。

        纯读操作（logic.get_record），零数据写风险；挂在 refresh_display 上，
        启动/保存/删除后都会随刷新路径自动更新。
        """
        self._today_status_label.setVisible(
            self.logic.get_record(self.today) is None
        )

    def _update_summary(self) -> None:
        """读取 logic 的最近记录汇总（按录入条数），并格式化为标签展示。"""
        count, total = self.logic.summary(WEEK_DAYS)
        prefix = f"最近{WEEK_DAYS}条总盈亏："

        # 数据不足或仅一条记录：弱化提示（灰字小号）
        if total is None or count == 1:
            text = f"{prefix}数据不足" if total is None else (
                f"{prefix}{format_money(total)}（仅 1 条记录）"
            )
            self._summary_label.setText(text)
            self._summary_label.setStyleSheet(
                f"color: {get_color('FG_MUTED')}; font-size: 12px; font-weight: bold;"
            )
            return

        total_text, total_signal = ProfitCalculatorLogic.format_signed_money(total)
        text = f"{prefix}{total_text}"
        color = signal_color(total_signal)

        self._summary_label.setText(text)
        self._summary_label.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold;"
        )

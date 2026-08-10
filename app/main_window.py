"""
主窗口：PySide6 QMainWindow。

管理窗口初始化、组件协调、数据流、主题切换、置顶与几何持久化。
"""

from __future__ import annotations

__all__ = ["MainWindow"]

import logging
import platform
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.chart_widget import ChartWidget
from account_store import AccountStore
from config import (
    DATA_DIR,
    DATE_FORMAT,
    RETENTION_LIMIT,
    SETTINGS_FILE,
    VIEW_DAYS,
)
from app.theme import (
    generate_qss,
    get_color,
    set_theme,
    signal_color,
    summary_style,
)
from app.input_panel import InputPanel
from app.table_widget import TableWidget
from app.motion import animate_value, set_animations_enabled
from app.profit_page import ProfitPage
from app.registry import AppWidget, WidgetRegistry
from app.sidebar import Sidebar
from app.ui_text import EMOJI
from data_store import DataStore
from formatting import format_money, format_short_date
from calculator import DayRecord, ProfitCalculatorLogic
from presentation import (
    format_saved_indicator,
    format_signed_money,
    format_window_text,
)
from settings_store import (
    SettingsStore,
    decode_geometry_hex,
    decode_legacy_geometry,
    encode_settings,
)
from signals import RateSignal

logger = logging.getLogger(__name__)

# DPI scaling on Windows
if platform.system() == "Windows":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        logger.warning("DPI awareness 设置失败")


class DashboardPage(QWidget):
    """记账仪表盘页面（QStackedWidget Page 0）。

    包含标题栏、日期标签、以及通过 WidgetRegistry 注册的所有输入/展示组件。
    """

    def __init__(self, registry: WidgetRegistry, main_window: MainWindow,
                 today: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(0)

        # 标题栏（简化版：只保留标题 + 今日未录入提醒）
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        self._title_label = QLabel("Delta Force Dashboard")
        self._title_label.setObjectName("titleLabel")
        title_layout.addWidget(self._title_label)

        self._today_status_label = QLabel("今日未录入")
        self._today_status_label.setObjectName("todayStatusLabel")
        title_layout.addWidget(self._today_status_label)

        title_layout.addStretch()
        layout.addWidget(title_bar)

        # 日期
        self._date_label = QLabel(today)
        self._date_label.setObjectName("dateLabel")
        # U-07：与标题同侧左对齐，消除「标题左、日期居中」的轴线错位
        self._date_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addSpacing(4)
        layout.addWidget(self._date_label)
        layout.addSpacing(12)

        # 注册的 widgets（输入面板、汇总条、表格、图表、提示栏）
        registry.build_all(layout, main_window)


class MainWindow(QMainWindow):
    """Delta Force Dashboard 主窗口。"""

    def __init__(self, store: DataStore | None = None,
                 logic: ProfitCalculatorLogic | None = None,
                 settings_store: SettingsStore | None = None,
                 registry: WidgetRegistry | None = None,
                 account_store: AccountStore | None = None) -> None:
        super().__init__()

        self.settings_store = settings_store or SettingsStore(SETTINGS_FILE)
        self._settings = self.settings_store.load()
        self._theme = self._settings.get("theme", "light")
        set_theme(self._theme)
        # U-06：动效开关（settings `animations=false` 时全部动效失效，功能不受影响）
        set_animations_enabled(self._settings.get("animations", True))

        # Y-03：账号解析。注入 seam 定案——仅当未注入 store/logic 时才走账号解析
        # （生产默认路径，从 settings.current_account 解析并构造对应账号 DataStore）；
        # 注入 store/logic 保持现状（既有 ~15 个注入测试零改动、零真实目录触碰）。
        # 测试显式注入 account_store/settings_store 即可让完整解析链路落在 tmp_path。
        if store is None and logic is None:
            self._account_store = account_store or AccountStore()
            self.current_account = self._account_store.resolve_account(
                self._settings.get("current_account")
            )
            self.store = self._account_store.new_store(self.current_account)
            self.logic = ProfitCalculatorLogic(self.store.load())
        else:
            self._account_store = account_store  # 注入模式不参与解析
            self.current_account = None
            self.store = store or DataStore()
            self.logic = logic or ProfitCalculatorLogic(self.store.load())

        self._registry = registry or self._default_registry()
        self.today = datetime.now().strftime(DATE_FORMAT)
        # J 系列：当前视图条数，启动默认 7（会话内存生效，不持久化，Consensus §7.5）
        self._view_n = VIEW_DAYS[0]
        self._pinned = False
        # W-01：KPI count-up 的上一帧数值（None = 尚未渲染过/数据不足）
        self._last_summary_total: float | None = None
        self._last_cash_delta: float | None = None

        self._setup_window()
        self.sidebar = Sidebar()
        self._build_ui()
        self._connect_signals()
        self._apply_qss()
        # Y-03：标题栏显示当前账号名（注入模式无账号概念，保持原标题）
        self._update_account_title()
        # Y-04：账号区初始化——解析模式注入账号列表；注入模式隐藏账号区
        if self.current_account is not None:
            self._refresh_account_combo()
        else:
            self.sidebar.set_account_area_visible(False)

        # 初始渲染
        self.refresh_display()

        # 仪表盘渲染完成后，后台预加载利润页面数据
        self._preload_timer = QTimer(self)
        self._preload_timer.setSingleShot(True)
        self._preload_timer.timeout.connect(self._preload_profit_page)
        self._preload_timer.start(500)

        # 恢复置顶状态
        if self._settings.get("pinned", False):
            self._toggle_pin()

        self.input_panel.focus_cash()

    # ═══════════════════════════════════════════════════════
    # 窗口设置
    # ═══════════════════════════════════════════════════════

    @staticmethod
    def _window_preset(screen_h: int) -> tuple[int, int, int, int]:
        """按屏幕可用高度返回 (默认窗口宽, 默认窗口高, 图表最小高, 图表最大高)。

        U-09 实测反馈后：表格全量展示 + 图表不能太小，空间只能从屏幕高度找。
        屏幕可用高度 ≥1000（1080p 主流）→ 大档：窗口 1020 + 图表 [160,240]；
        小屏 → 紧凑档：窗口 920 + 图表 [140,150]。两档表格全量参数一致。
        """
        if screen_h >= 1000:
            return 820, 1020, 160, 240
        return 820, 920, 140, 150

    def _setup_window(self) -> None:
        self.setWindowTitle("Delta Force Dashboard")

        # 基础大小（双栏表格需更宽；高度按屏幕可用空间自适应，U-09）
        screen = QApplication.primaryScreen()
        screen_h = screen.availableGeometry().height() if screen else 0
        base_w, base_h, self._chart_min_h, self._chart_max_h = self._window_preset(
            screen_h
        )
        self.setMinimumSize(680, 650)

        # 恢复上次几何（候选 3：解析收敛到 settings_store 纯函数）
        saved_geo = self._settings.get("geometry", "")
        geo_ok = False
        if isinstance(saved_geo, str) and saved_geo:
            raw = decode_geometry_hex(saved_geo)
            if raw is not None:
                try:
                    geo_ok = self.restoreGeometry(raw)
                except Exception:
                    logger.warning("几何恢复（hex 格式）失败")
            if not geo_ok:
                legacy = decode_legacy_geometry(saved_geo)
                if legacy is not None:
                    w, h, x, y = legacy
                    self.resize(w, h)
                    self.move(x, y)
                    geo_ok = True

        if not geo_ok:
            self.resize(base_w, base_h)
            if screen:
                rect = screen.availableGeometry()
                x = (rect.width() - base_w) // 2
                y = (rect.height() - base_h) // 2
                self.move(x, y)

    # ═══════════════════════════════════════════════════════
    # 设置持久化
    # ═══════════════════════════════════════════════════════

    def _save_settings(self) -> None:
        """编码当前窗口状态并委托 SettingsStore 原子落盘（D-02）。

        MainWindow 只保留「编码」（窗口状态 → dict）；文件 I/O 收敛到
        self.settings_store（容错读 + 原子写）。几何/置顶/主题的 dict
        编码收敛到 settings_store.encode_settings 纯函数（候选 3）；
        Y-03：current_account 在纯函数输出上合并（注入模式无账号 → 不写 key）。
        """
        settings = encode_settings(
            bytes(self.saveGeometry()), self._pinned, self._theme
        )
        if self.current_account is not None:
            settings["current_account"] = self.current_account
        self.settings_store.save(settings)

    def _update_account_title(self) -> None:
        """记账页标题栏显示当前账号名（Y-03，随账号区状态同步）。

        注入模式（current_account is None，无账号概念）保持原标题，
        既有注入测试零破坏。
        """
        if self.current_account is not None:
            self._title_label.setText(
                f"Delta Force Dashboard · {self.current_account}"
            )
        else:
            self._title_label.setText("Delta Force Dashboard")

    # ═══════════════════════════════════════════════════════
    # 账号区（Y-04 / Y-05）
    # ═══════════════════════════════════════════════════════

    def _refresh_account_combo(self) -> None:
        """账号区下拉列表与当前选中同步业务层账号状态（不触发选择信号）。"""
        self.sidebar.set_accounts(
            self._account_store.list_accounts(), self.current_account
        )

    def _create_account(self) -> None:
        """新建账号：命名对话框 → 业务层校验 → 刷新下拉列表。

        决策 6：新建成功后当前账号不变（留在当前账号，需手动切换）；
        非法名（空/重名/禁用字符/首尾空格或点）由 account_store 校验
        并以可读提示拒绝，拒绝时不产生任何目录（H1）。
        """
        if self.current_account is None:
            return  # 注入模式无账号概念（账号区已隐藏，防御）
        name, ok = QInputDialog.getText(self, "新建账号", "输入新账号名称：")
        if not ok:
            return
        reason = self._account_store.create_account(name)
        if reason is not None:
            QMessageBox.warning(self, "无法新建账号", reason)
            return
        logger.info("已新建账号：%s", name)
        self._refresh_account_combo()

    def _on_account_selected(self, name: str) -> None:
        """切换账号：换 DataStore/logic → 取消编辑/复用 → 全量刷新 → 标题/落盘同步。

        决策链（spec）：切换时用目标账号路径构造新 DataStore 并重新加载 logic，
        随后整页刷新（表格 / 曲线 / 汇总 / 今日状态 / 标题栏账号名）；保存 /
        删除 / CSV 导出随后即时落盘到新 store；取消未保存的编辑 / 复用状态，
        防止跨账号污染。选择当前账号本身 → no-op（不重载、不落盘）。
        利润页零改动（本方法不触碰 profit_page 任何状态）。
        """
        if self.current_account is None:
            return  # 注入模式无账号概念（账号区已隐藏，防御）
        if name == self.current_account:
            return  # 同账号 no-op
        if name not in self._account_store.list_accounts():
            return  # 目标账号不存在（防御：下拉数据来自业务层，正常不会发生）

        self.current_account = name
        self.store = self._account_store.new_store(name)
        self.logic = ProfitCalculatorLogic(self.store.load())

        # 取消编辑/复用态，防止旧账号输入污染新账号视图（Y-05 验收标准 3）
        self.input_panel.cancel_edit()
        self.input_panel.clear_fields()
        self.input_panel.cancel_reuse()
        # KPI count-up 上一帧归零：账号切换是数据源更换，数字直接落终态
        # （不做「旧账号数值滚动到新账号数值」的误导动画，Y-05 风险点）
        self._last_summary_total = None
        self._last_cash_delta = None

        self.refresh_display()
        self._update_account_title()
        self._refresh_account_combo()  # 下拉选中态同步（set_accounts 不触发选择信号）
        self._save_settings()  # current_account 落盘，重启回到新账号

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
        # T-01：请求在途时安全回收后台线程，避免运行中的 QThread 随窗口销毁 abort
        self._preload_timer.stop()
        self.profit_page.shutdown()
        self._save_settings()
        super().closeEvent(event)

    # ═══════════════════════════════════════════════════════
    # 构建界面
    # ═══════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 左侧边栏 ──
        root_layout.addWidget(self.sidebar)

        # ── 右侧页面区（QStackedWidget）──
        self._stack = QStackedWidget()
        self._stack.setObjectName("pageStack")
        root_layout.addWidget(self._stack, 1)

        # ── Page 0：记账仪表盘 ──
        dashboard = DashboardPage(self._registry, self, self.today)
        self._title_label = dashboard._title_label
        self._today_status_label = dashboard._today_status_label
        self._date_label = dashboard._date_label
        self._stack.addWidget(dashboard)

        # ── Page 1：利润（制造产物 + 兑换利润）──
        self.profit_page = ProfitPage()
        self._stack.addWidget(self.profit_page)

        # ── 侧边栏导航切换 ──
        self.sidebar.nav_changed.connect(self._stack.setCurrentIndex)

        self._update_theme_btn_text()

    def _build_card(self) -> QFrame:
        """构建带阴影的卡片 QFrame（12px 圆角 + 微阴影）。"""
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setFrameShape(QFrame.Shape.StyledPanel)

        # 微阴影（QGraphicsDropShadowEffect，QSS 不支持 box-shadow）
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 20))
        card.setGraphicsEffect(shadow)

        return card

    def _update_theme_btn_text(self) -> None:
        self.sidebar.theme_btn.setText(
            f"{EMOJI['theme_dark']} 暗色"
            if self._theme == "light"
            else f"{EMOJI['theme_light']} 亮色"
        )

    # ═══════════════════════════════════════════════════════
    # 信号连接
    # ═══════════════════════════════════════════════════════

    def _connect_signals(self) -> None:
        # Widget 信号（从 registry 连接）
        self._registry.connect_all(self)

        # 侧边栏按钮
        self.sidebar.theme_btn.clicked.connect(self._toggle_theme)
        self.sidebar.pin_btn.clicked.connect(self._toggle_pin)
        self.sidebar.export_btn.clicked.connect(self._export_csv)
        # Y-04：账号区——新建账号（命名对话框）；下拉选择切换（Y-05 接线）
        self.sidebar.create_account_requested.connect(self._create_account)
        self.sidebar.account_selected.connect(self._on_account_selected)

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
        self.sidebar.apply_theme()

    def _toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        set_theme(self._theme)
        self.refresh_theme()
        self._save_settings()

    def refresh_theme(self) -> None:
        """仅刷新主题视觉样式，不重新加载数据。

        主题切换时，get_color() 已返回新主题色值，全部 UI 组件
        通过调用自身的 apply_theme 方法增量更新颜色，无需重新获取数据。
        """
        self._apply_qss()
        self._update_theme_btn_text()
        self._update_pin_btn_style()
        self.input_panel.apply_theme()
        self.chart.apply_theme()
        # 兑换页包标签为内联样式，构建期冻结——主题切换后需重解析（U-03 评审修复）
        self.profit_page.exchange_page.apply_theme()
        # 表格用当前数据重绘（get_color 自动取新主题色）
        records = self._get_records()
        self._update_summary()
        self._update_today_status()
        self.table.draw(records, self.today)

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
            self.sidebar.pin_btn.setText(f"{EMOJI['pin']} 已置顶")
            if self.sidebar.pin_btn.property("active") != "true":
                self.sidebar.pin_btn.setProperty("active", "true")
                self.sidebar.pin_btn.style().unpolish(self.sidebar.pin_btn)
                self.sidebar.pin_btn.style().polish(self.sidebar.pin_btn)
        else:
            self.sidebar.pin_btn.setText(f"{EMOJI['pin']} 置顶")
            if self.sidebar.pin_btn.property("active") == "true":
                self.sidebar.pin_btn.setProperty("active", "false")
                self.sidebar.pin_btn.style().unpolish(self.sidebar.pin_btn)
                self.sidebar.pin_btn.style().polish(self.sidebar.pin_btn)

    # ═══════════════════════════════════════════════════════
    # 数据获取
    # ═══════════════════════════════════════════════════════

    def _get_records(self) -> list:
        """返回最近 self._view_n 条实际录入的 (date_str, DayRecord) 列表。

        J 系列：视图条数由按钮组驱动（默认 VIEW_DAYS[0]=7），取代硬编码 7；
        存储保留上限（RETENTION_LIMIT=30）与视图解耦，这里只筛窗口。
        """
        return self.logic.recent_records(self._view_n)

    def _on_view_changed(self, n: int) -> None:
        """视图按钮组切换：更新当前视图条数并重绘（表格+曲线图+汇总联动）。

        Q9/Q10：单一开关驱动三处同变，数据流一致（同源自 recent_records(_view_n)）。
        """
        if n == self._view_n:
            return
        self._view_n = n
        self.refresh_display()

    @property
    def view_n(self) -> int:
        """当前视图条数（只读）。"""
        return self._view_n

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
        if not ProfitCalculatorLogic.is_cash_under_warehouse(cash, warehouse):
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
        self.store.save(self.logic.serialize())

        was_editing = self.input_panel.is_editing()
        if was_editing:
            self._cancel_edit()

        self.refresh_display()

        indicator = format_saved_indicator(
            save_date, warehouse, self.today, deleted, RETENTION_LIMIT
        )
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
        result = self.logic.reuse_candidate(self.today)
        if result is None:
            self.input_panel.set_saved_indicator("暂无可复用的历史数据")
            return
        date_str, record, is_today_fallback = result
        msg = "今日数据" if is_today_fallback else f"{date_str} 的数据"
        self.input_panel.set_reuse_hint(msg, record.cash, record.warehouse)

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
        self.store.save(self.logic.serialize())

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
        self.input_panel.set_saved_indicator(f"{EMOJI['ok']} CSV 已导出")

    # ═══════════════════════════════════════════════════════
    # 刷新展示
    # ═══════════════════════════════════════════════════════

    def refresh_display(self) -> None:
        records = self._get_records()
        self._update_summary()
        self._update_today_status()
        self.table.draw(records, self.today)
        self.chart.draw(records)

    def _preload_profit_page(self) -> None:
        """仪表盘渲染完成后，后台并行预加载利润页两个子模块数据。

        用户反馈：兑换利润此前等首次点击才拉取（10s 超时 HTTP），点击后
        才有卡顿感——改为启动即预加载制造产物 + 兑换利润（各自后台线程，
        kkrb 60s TTL 缓存复用）。导航到 ProfitPage 时数据已就绪，零闪烁。
        预加载失败不弹窗，仅由 preload() 内部记录日志，用户手动刷新即可；
        offscreen 测试模式跳过预加载的守卫同样在 preload() 内部。
        """
        self.profit_page.crafting_page.preload()
        self.profit_page.exchange_page.preload()

    def _update_today_status(self) -> None:
        """更新「今日未录入」提醒：今日无记录时显示，有记录时隐藏。

        纯读操作（logic.get_record），零数据写风险；挂在 refresh_display 上，
        启动/保存/删除后都会随刷新路径自动更新。
        """
        self._today_status_label.setVisible(
            self.logic.get_record(self.today) is None
        )

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

    def _update_summary(self) -> None:
        """读取 logic 的最近记录汇总，拆分为磁贴「说明 + 大数字」渲染。

        D-07：文本与信号由 format_summary / format_cash_summary 纯函数生成，
        本方法只做信号→颜色映射与样式落地（颜色映射留 UI）。
        总盈亏（_summary_label）与现金总变化（_cash_summary_label）双磁贴，
        同源 recent_records(_view_n)，随视图 7/30 联动。
        W-01：数值变化时数字从旧值滚动到新值（count-up，300ms），
        数据不足（total 为 None）或数值未变时直接落终态。
        """
        count, total = self.logic.summary(self._view_n)
        text, signal = format_window_text(count, total, "总盈亏", self._view_n)
        caption, value = self._split_kpi_text(text)
        self._summary_caption.setText(caption)
        self._set_kpi_value(self._summary_label, value, self._last_summary_total, total)
        self._last_summary_total = total
        self._summary_label.setStyleSheet(summary_style(signal))

        cash_count, cash_delta = self.logic.cash_summary(self._view_n)
        cash_text, cash_signal = format_window_text(
            cash_count, cash_delta, "现金总变化", self._view_n
        )
        caption, value = self._split_kpi_text(cash_text)
        self._cash_summary_caption.setText(caption)
        self._set_kpi_value(
            self._cash_summary_label, value, self._last_cash_delta, cash_delta
        )
        self._last_cash_delta = cash_delta
        self._cash_summary_label.setStyleSheet(summary_style(cash_signal))

    def _set_kpi_value(
        self, label: QLabel, value: str, old: float | None, new: float | None
    ) -> None:
        """KPI 磁贴数字落值：数值变化时 count-up 滚动（W-01），否则直接设置。

        动画复用 format_signed_money 逐帧格式化，终态与直接设置完全一致；
        动画对象挂 MainWindow 防 GC，动画中重复触发会替换旧动画。
        """
        if (
            old is not None
            and new is not None
            and old != new
            and value != "数据不足"
        ):
            self._kpi_countup_anim = animate_value(
                self,
                old,
                new,
                lambda v: label.setText(format_signed_money(v)[0]),
                duration_ms=300,
            )
        else:
            label.setText(value)

    # ═══════════════════════════════════════════════════════
    # 默认注册表
    # ═══════════════════════════════════════════════════════

    def _default_registry(self) -> WidgetRegistry:
        """创建默认 widget 注册表（InputPanel + TableWidget + ChartWidget + 汇总 + 提示）。"""
        registry = WidgetRegistry()

        # ── InputPanel ──
        input_panel = InputPanel()
        self.input_panel = input_panel

        # 顶部区域（U-01）：输入卡（左，限宽 520）+ KPI 磁贴卡（右，吃剩余空间）
        top_bar = QWidget()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(12)

        def setup_input(root_layout, mw):
            card = mw._build_card()
            card.setMaximumWidth(520)  # 限宽：宽窗口下输入框不再无限横向拉伸（U-01）
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.addWidget(input_panel)
            top_bar_layout.addWidget(card, 0)
            root_layout.addWidget(top_bar)
            root_layout.addSpacing(8)

        def connect_input(mw):
            input_panel.save_requested.connect(mw.save_today)
            input_panel.cancel_requested.connect(mw._cancel_edit)
            input_panel.reuse_requested.connect(mw._reuse_last_record)
            input_panel.reuse_cancel_requested.connect(mw._cancel_reuse)

        registry.register(AppWidget(input_panel, setup_input, connect_input))

        # ── KPI 磁贴卡（总盈亏 / 现金总变化）──
        # U-01：核心数字从裸 QLabel 升级为卡片磁贴——大数字（summary_style 22px
        # 信号色）+ 小字说明（caption），与输入卡并排，成为页面的读数锚点。
        self._summary_label = QLabel("")
        self._summary_label.setObjectName("summaryLabel")
        self._summary_label.setWordWrap(True)
        self._summary_caption = QLabel("")
        self._summary_caption.setObjectName("summaryCaption")

        self._cash_summary_label = QLabel("")
        self._cash_summary_label.setObjectName("cashSummaryLabel")
        self._cash_summary_label.setWordWrap(True)
        self._cash_summary_caption = QLabel("")
        self._cash_summary_caption.setObjectName("cashSummaryCaption")

        # KPI 卡片本体在 setup 时由 _build_card 创建（需要 mw）；
        # widget 字段仅为 registry 契约占位，布局由 setup 回调决定。
        kpi_card = QWidget()

        def setup_summary(root_layout, mw):
            kpi_card_real = mw._build_card()
            kcl = QVBoxLayout(kpi_card_real)
            kcl.setContentsMargins(14, 10, 14, 10)
            kcl.setSpacing(6)
            for caption, value in (
                (self._summary_caption, self._summary_label),
                (self._cash_summary_caption, self._cash_summary_label),
            ):
                tile = QVBoxLayout()
                tile.setSpacing(2)
                tile.addWidget(caption)
                tile.addWidget(value)
                kcl.addLayout(tile)
            kcl.addStretch()
            top_bar_layout.addWidget(kpi_card_real, 1)

        registry.register(AppWidget(kpi_card, setup_summary, None))

        # ── TableWidget ──
        table = TableWidget()
        self.table = table

        def setup_table(root_layout, mw):
            table_card = mw._build_card()
            tcl = QVBoxLayout(table_card)
            tcl.setContentsMargins(10, 8, 10, 8)
            tcl.addWidget(table)
            # 表格全量展示优先（H-01 语义，U-02 弹性翻转后用户实测回退）：
            # 表格吃窗口增长空间，超高时 _DaySubTable 内部滚动仅作极端兜底
            root_layout.addWidget(table_card, 1)
            root_layout.addSpacing(8)

        def connect_table(mw):
            table.edit_requested.connect(mw._start_edit)
            table.delete_requested.connect(mw._delete_record)
            table.view_changed.connect(mw._on_view_changed)

        registry.register(AppWidget(table, setup_table, connect_table))

        # ── ChartWidget ──
        chart = ChartWidget()
        self.chart = chart

        def setup_chart(root_layout, mw):
            chart_card = mw._build_card()
            ccl = QVBoxLayout(chart_card)
            ccl.setContentsMargins(10, 8, 10, 8)
            ccl.addWidget(chart)
            # 折线图固定小卡片（H-01 语义）：不随窗口扩张，为表格全量展示让位；
            # 高度区间按屏幕可用空间自适应（_window_preset，U-09 方案 A）
            chart.setMinimumHeight(mw._chart_min_h)
            chart.setMaximumHeight(mw._chart_max_h)
            root_layout.addWidget(chart_card, 0)
            root_layout.addSpacing(8)

        registry.register(AppWidget(chart, setup_chart, None))

        # ── 底部提示栏 ──
        self._hint_label = QLabel(
            "Enter 保存 ｜ Ctrl+A 全选 ｜ Esc 清空 ｜ "
            "支持 K/M/B 后缀（如 1.5K = 1,500）"
        )
        self._hint_label.setObjectName("hintLabel")

        def setup_hint(root_layout, mw):
            root_layout.addWidget(self._hint_label)

        registry.register(AppWidget(self._hint_label, setup_hint, None))

        return registry
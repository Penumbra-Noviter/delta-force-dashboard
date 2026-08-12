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
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from account_store import AccountStore, validate_account_name
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
)
from app.dashboard_page import build_dashboard
from app.kpi_presenter import KpiPresenter
from app.motion import set_animations_enabled
from app.profit_page import ProfitPage
from app.sidebar import Sidebar
from app.ui_text import EMOJI
from data_store import DataStore
from formatting import format_money, format_short_date
from calculator import DayRecord, ProfitCalculatorLogic
from kkrb_client import KkrbClient
from presentation import (
    format_saved_indicator,
    format_window_text,
)
from settings_store import (
    SettingsStore,
    decode_geometry_hex,
    decode_legacy_geometry,
    encode_window_state,
)
from signals import RateSignal

logger = logging.getLogger(__name__)

# ── 设置键模块常量（C3-11：窗口层设置读写收敛，键清单归 SettingsStore）──
_KEY_GEOMETRY = "geometry"
_KEY_PINNED = "pinned"
_KEY_THEME = "theme"
_KEY_ANIMATIONS = "animations"
_KEY_CURRENT_ACCOUNT = "current_account"

# DPI scaling on Windows
if platform.system() == "Windows":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        logger.warning("DPI awareness 设置失败")


def _kpi_signal(count: int, total: float | None, label: str, days: int) -> RateSignal:
    """KPI 磁贴信号的共享纯函数：经 format_window_text 取信号（AA-01）。

    _update_summary 与 _apply_kpi_styles 两处都以「logic.summary(_view_n) →
    format_window_text」重算 signal，此前各自内联同一段——抽取后信号判定
    只有本函数一个入口（判定规则仍归 presentation.format_window_text），
    消除 Divergent Change。纯函数：同输入必同输出，可安全双调用。
    """
    return format_window_text(count, total, label, days)[1]


class MainWindow(QMainWindow):
    """Delta Force Dashboard 主窗口。"""

    def __init__(self, store: DataStore | None = None,
                 logic: ProfitCalculatorLogic | None = None,
                 settings_store: SettingsStore | None = None,
                 account_store: AccountStore | None = None,
                 client: KkrbClient | None = None) -> None:
        super().__init__()

        self.settings_store = settings_store or SettingsStore(SETTINGS_FILE)
        self._settings = self.settings_store.load()
        self._theme = self._settings.get(_KEY_THEME, "light")
        set_theme(self._theme)
        # U-06：动效开关（settings `animations=false` 时全部动效失效，功能不受影响）
        set_animations_enabled(self._settings.get(_KEY_ANIMATIONS, True))

        # Y-03：账号解析。注入 seam 定案——仅当未注入 store/logic 时才走账号解析
        # （生产默认路径，从 settings.current_account 解析并构造对应账号 DataStore）；
        # 注入 store/logic 保持现状（既有 ~15 个注入测试零改动、零真实目录触碰）。
        # 测试显式注入 account_store/settings_store 即可让完整解析链路落在 tmp_path。
        if store is None and logic is None:
            self._account_store = account_store or AccountStore()
            self.current_account = self._account_store.resolve_account(
                self._settings.get(_KEY_CURRENT_ACCOUNT)
            )
            self.store = self._account_store.new_store(self.current_account)
            self.logic = ProfitCalculatorLogic(self.store.load())
        else:
            self._account_store = account_store  # 注入模式不参与解析
            self.current_account = None
            self.store = store or DataStore()
            self.logic = logic or ProfitCalculatorLogic(self.store.load())

        self.today = datetime.now().strftime(DATE_FORMAT)
        # J 系列：当前视图条数，启动默认 7（会话内存生效，不持久化，Consensus §7.5）
        self._view_n = VIEW_DAYS[0]
        self._pinned = False

        # C2-02：kkrb API 客户端注入 seam——None → 自建（生产唯一创建点）；
        # 注入 fake 后利润页两子模块共享同一实例（01 加锁保证并发安全）。
        self._client = client or KkrbClient()

        self._setup_window()
        self.sidebar = Sidebar()
        self._build_ui()
        self._connect_signals()
        self._apply_qss()
        # C1-08：仪表盘组件已全部入树后收集主题刷新器并首次应用
        # （E2：sidebar 首帧主题完整，不依赖首次切换）
        self._collect_theme_refreshers()
        self._apply_theme_refreshers()
        # Y-03：标题栏显示当前账号名（注入模式无账号概念，保持原标题）
        self._update_account_title()
        # Y-04：账号区初始化——解析模式注入账号列表；注入模式隐藏账号区
        if self.current_account is not None:
            self._refresh_account_combo()
        else:
            self.sidebar.hide_account_area()

        # 初始渲染
        self.refresh_display()

        # 仪表盘渲染完成后，后台预加载利润页面数据
        self._preload_timer = QTimer(self)
        self._preload_timer.setSingleShot(True)
        self._preload_timer.timeout.connect(self._preload_profit_page)
        self._preload_timer.start(500)

        # 恢复置顶状态
        if self._settings.get(_KEY_PINNED, False):
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
        saved_geo = self._settings.get(_KEY_GEOMETRY, "")
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
        """合并更新设置并原子落盘（C3-11：走 settings_store.update，未知键保留）。

        patch = 窗口状态编码（几何/置顶/主题）+ animations 启动值（运行期
        内存，启动值即运行值——纳入持久化闭环）+ current_account（账号模式
        才写，注入模式无账号概念不写 key）；update 返回值回写 self._settings，
        后续读取走运行期内存。文件中原有未知键（patch 之外）由 update 保留。
        """
        patch = encode_window_state(
            bytes(self.saveGeometry()), self._pinned, self._theme
        )
        patch[_KEY_ANIMATIONS] = self._settings.get(_KEY_ANIMATIONS, True)
        if self.current_account is not None:
            patch[_KEY_CURRENT_ACCOUNT] = self.current_account
        self._settings = self.settings_store.update(patch)

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
        F-P1 评审修复：切换前补 validate_account_name 校验——非法名（如手工
        创建的非法目录被绕过过滤直接触发）拒绝切换并给可读提示，与启动路径
        resolve_account 行为一致，杜绝「写入非法目录 → 重启静默失联」。
        """
        if self.current_account is None:
            return  # 注入模式无账号概念（账号区已隐藏，防御）
        if name == self.current_account:
            return  # 同账号 no-op
        if validate_account_name(name) is not None:
            QMessageBox.warning(
                self, "无法切换账号", f"账号「{name}」名称不合法，已忽略"
            )
            return
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
        self._kpi_presenter.reset()

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

        # ── Page 0：记账仪表盘（C4 块 1：build_dashboard 直构装配）──
        bundle = build_dashboard(self)
        self.input_panel = bundle.input_panel
        self.table = bundle.table
        self.chart = bundle.chart
        self._summary_label = bundle.summary_label
        self._summary_caption = bundle.summary_caption
        self._cash_summary_label = bundle.cash_summary_label
        self._cash_summary_caption = bundle.cash_summary_caption
        self._hint_label = bundle.hint_label
        # C4 块 2：KPI 双磁贴渲染收敛到 KpiPresenter（count-up 状态/动画归它管）
        self._kpi_presenter = KpiPresenter(
            summary_label=bundle.summary_label,
            summary_caption=bundle.summary_caption,
            cash_summary_label=bundle.cash_summary_label,
            cash_summary_caption=bundle.cash_summary_caption,
        )
        dashboard = self._dashboard_page
        self._title_label = dashboard._title_label
        self._today_status_label = dashboard._today_status_label
        self._date_label = dashboard._date_label
        self._stack.addWidget(dashboard)

        # ── Page 1：利润（制造产物 + 兑换利润，共享同一 client）──
        self.profit_page = ProfitPage(client=self._client)
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
        # 仪表盘组件信号已由 build_dashboard 显式连接（C4 块 1 直构）

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
        # C1-08：sidebar 由 _theme_refreshers 统一调用（启动期已应用，
        # E2）；此处不再直插，避免双路径

    def _collect_theme_refreshers(self) -> None:
        """启动期遍历子树收集具 apply_theme 的组件（自顶向下、父拥有子树）。

        节点有 apply_theme 即收集且不再下钻——profit_page 入列时
        crafting/exchange 不得重复入列（防双扇出）；新组件只要实现
        apply_theme 即自动纳入刷新（C1-08 契约）。
        """
        self._theme_refreshers: list[QWidget] = []

        def walk(widget: QWidget) -> None:
            if hasattr(widget, "apply_theme"):
                self._theme_refreshers.append(widget)
                return
            for obj in widget.children():
                if isinstance(obj, QWidget):
                    walk(obj)

        walk(self)

    def _apply_theme_refreshers(self) -> None:
        """统一调用全部主题刷新器（启动期与 refresh_theme 共用）。"""
        for widget in self._theme_refreshers:
            widget.apply_theme()

    def _toggle_theme(self) -> None:
        self._theme = "dark" if self._theme == "light" else "light"
        set_theme(self._theme)
        self.refresh_theme()
        self._save_settings()

    def refresh_theme(self) -> None:
        """仅刷新主题视觉样式，不重新加载数据（C1-08）。

        主题切换与数据刷新彻底解耦：QSS 重生成 + 按钮文字 + 置顶样式 +
        树遍历收集的 refreshers 统一调用；不再调用 table.draw /
        _update_summary / _update_today_status（数据渲染路径零触碰）。
        KPI 磁贴颜色由 _apply_kpi_styles 承担（signal 重算，不动文本/动画）。
        """
        self._apply_qss()
        self._update_theme_btn_text()
        self._update_pin_btn_style()
        self._apply_theme_refreshers()
        self._apply_kpi_styles()

    def _apply_kpi_styles(self) -> None:
        """重算两 KPI 磁贴的 signal 并重应用样式（C1-08 E1，委托 KpiPresenter）。

        纯内存读（logic.summary / cash_summary，零 I/O）；不动数值文本、
        不触发 count-up 动画——主题切换只换色（presenter.apply_theme_styles）。
        """
        self._kpi_presenter.apply_theme_styles(self.logic, self._view_n)

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
        C2-03：测试经构造注入 stub client 压制网络，preload 不再读取
        环境变量哨兵。
        """
        self.profit_page.preload()

    def _update_today_status(self) -> None:
        """更新「今日未录入」提醒：今日无记录时显示，有记录时隐藏。

        纯读操作（logic.get_record），零数据写风险；挂在 refresh_display 上，
        启动/保存/删除后都会随刷新路径自动更新。
        """
        self._today_status_label.setVisible(
            self.logic.get_record(self.today) is None
        )

    def _update_summary(self) -> None:
        """KPI 双磁贴全量渲染（说明 + 大数字 + count-up + 样式，委托 KpiPresenter）。

        D-07 / W-01 语义归 presenter：文本与信号由 format_summary 纯函数生成、
        数值变化时 count-up 滚动、数据不足直落终态；随视图 7/30 联动
        （同源 recent_records(_view_n)）。
        """
        self._kpi_presenter.update(self.logic, self._view_n)

"""
主题系统（PySide6 版）：色板定义 + QSS 样式生成 + 主题切换。

主题数据的单一真实来源。所有 UI 组件通过此模块获取颜色值。
"""

from __future__ import annotations

from signals import PnLSignal, RateSignal

__all__ = [
    "THEMES",
    "generate_qss",
    "get_color",
    "get_theme",
    "set_theme",
    "signal_color",
    "summary_style",
]

# ── 主题色板 ──────────────────────────────────────────
# 护眼配色：暖纸白底 + 温润青色（teal）主色调，降低蓝光刺激
# 语义色保留绿涨红跌（国际惯例），青色主色与语义色明确区分
THEMES = {
    "light": {
        "BG": "#faf9f6",            # 暖纸白，替代纯白降低刺眼感
        "FG_LABEL": "#4a5568",       # 软石板灰，对比度 6.8:1
        "FG_MUTED": "#718096",       # slate-500，对比度 4.6:1（达 WCAG AA）
        "FG_POS": "#16a34a",         # 绿涨（green-600）
        "FG_NEG": "#dc2626",         # 红跌（red-600）
        "FG_TODAY": "#0d9488",       # 今日用主色青
        "BTN_BG": "#0d9488",         # teal-600 主色
        "BTN_BG_HOVER": "#0f766e",   # teal-700 悬停加深
        "BTN_FG": "#ffffff",
        "BORDER_DEFAULT": "#d6d3cc",  # 暖灰边框
        "BORDER_VALID": "#16a34a",
        "BORDER_INVALID": "#dc2626",
        "BORDER_WARNING": "#d97706",  # 越界警告边框（amber-600，O-08）
        "SEPARATOR": "#e7e5e0",      # 暖浅灰分隔线
        "PLACEHOLDER": "#9ca3af",   # gray-400，占位文字豁免 AA
        "MUTED_BG": "#f4f2ed",      # 暖静音底
        "PIN_OFF_BG": "#f4f2ed",
        "PIN_ON_BG": "#0d9488",
        "CHART_CASH": "#0d9488",     # 青色（与主色一致）
        "CHART_WAREHOUSE": "#d97706",# 琥珀金（amber-600，更沉稳）
        "CHART_TOTAL": "#16a34a",
        "CHART_GRID": "#e7e5e0",
        "CHART_BG": "#fdfcf9",       # 图表区微暖底
        "CHART_AXIS": "#6b7280",
        "CHART_TEXT": "#374151",
        "TABLE_TEXT": "#3d4453",
        "TABLE_TEXT_BOLD": "#1a202c",
        "TABLE_ROW_EVEN_BG": "#ffffff",
        "TABLE_ROW_ODD_BG": "#f6f5f1",
        "TABLE_ROW_HOVER_BG": "#f4f2ed",
        "TABLE_ROW_TODAY_BG": "#e6f7f5",  # 今日行浅青底
        "TABLE_HEADER_BG": "#f4f2ed",
        "TABLE_HEADER_FG": "#3d4453",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "#e7e5e0",
        "INPUT_BG": "#ffffff",
        "INPUT_FG": "#1a202c",
        # 操作按钮语义色
        "DANGER_BG": "#fef2f2",
        "DANGER_FG": "#dc2626",
        "DANGER_BORDER": "#fecaca",
        "DANGER_HOVER_BG": "#dc2626",
    },
    "dark": {
        "BG": "#0a0a0d",             # 极暗炭灰底（接近纯黑但保留灰调，非死黑）
        "FG_LABEL": "#c4c4cc",       # 中冷灰，正文
        "FG_MUTED": "#7a7a84",       # 低对比灰，次级文字（参考图 #A0A0A5）
        "FG_POS": "#10B981",         # 薄荷绿涨（柔和不刺眼）
        "FG_NEG": "#EF4444",         # 玫瑰红跌（柔和不刺眼）
        "FG_TODAY": "#FF8C00",       # 电光琥珀橙（参考图主色）
        "BTN_BG": "#FF8C00",         # 琥珀橙主按钮
        "BTN_BG_HOVER": "#FFA940",   # 悬停提亮
        "BTN_FG": "#0a0a0d",         # 深底文字（橙色上显深字）
        "BORDER_DEFAULT": "#121217", # 与卡片底同色，肉眼不可见的边框
        "BORDER_VALID": "#10B981",
        "BORDER_INVALID": "#EF4444",
        "BORDER_WARNING": "#FF8C00",
        "SEPARATOR": "#0d0d11",      # 比基底亮半阶，表格网格线极淡
        "PLACEHOLDER": "#5a5a64",
        "MUTED_BG": "#131318",       # 次级按钮底，比基底亮一阶
        "PIN_OFF_BG": "#131318",
        "PIN_ON_BG": "#FF8C00",      # 琥珀橙钉选
        "CHART_CASH": "#FFA940",     # 暖琥珀虚线（现金）
        "CHART_WAREHOUSE": "#FF8C00",# 电光橙实线（仓库价值）
        "CHART_TOTAL": "#10B981",
        "CHART_GRID": "#0d0d11",     # 极暗网格，几乎不可见
        "CHART_BG": "#0a0a0d",       # 图表区与基底一致
        "CHART_AXIS": "#7a7a84",
        "CHART_TEXT": "#c4c4cc",
        "TABLE_TEXT": "#c4c4cc",
        "TABLE_TEXT_BOLD": "#e8e8ee",# 近白强调
        "TABLE_ROW_EVEN_BG": "#0a0a0d",
        "TABLE_ROW_ODD_BG": "#0f0f14",
        "TABLE_ROW_HOVER_BG": "#17171e",
        "TABLE_ROW_TODAY_BG": "#1a1410",  # 今日行暗暖橙底
        "TABLE_HEADER_BG": "#131318",
        "TABLE_HEADER_FG": "#7a7a84",
        "CARD_BG": "#121217",        # 卡片比基底亮一阶，靠色差而非边框区隔
        "CARD_BORDER": "#121217",    # 与卡片底同色，边框彻底隐形
        "INPUT_BG": "#14141a",       # 输入框比卡片微亮
        "INPUT_FG": "#c4c4cc",
        # 操作按钮语义色
        "DANGER_BG": "#1f1418",
        "DANGER_FG": "#EF4444",
        "DANGER_BORDER": "#2d1a20",
        "DANGER_HOVER_BG": "#dc3838",
    },
}

# ── 当前主题名称（运行时由 UI 切换） ─────────────────
_current_theme = "light"


def get_theme() -> dict:
    """返回当前主题的配色字典。"""
    return THEMES[_current_theme]


def set_theme(name: str) -> None:
    """切换当前主题（"light" | "dark"）。"""
    global _current_theme
    if name in THEMES:
        _current_theme = name


def get_color(key: str) -> str:
    """获取当前主题下指定颜色值。"""
    return THEMES[_current_theme].get(key, "")



# ── 信号 → 主题色映射 ───────────────────────────────
# 业务层只返回语义信号（RateSignal / PnLSignal），这里完成「信号 → 主题键」映射；
# 具体色值在调用 get_color() 时实时解析，避免 import 期冻结（C1）。
_SIGNAL_TO_KEY: dict[RateSignal | PnLSignal, str] = {
    RateSignal.POSITIVE: "FG_POS",
    PnLSignal.PROFIT: "FG_POS",
    RateSignal.NEGATIVE: "FG_NEG",
    PnLSignal.LOSS: "FG_NEG",
    RateSignal.NEUTRAL: "FG_MUTED",
    PnLSignal.NEUTRAL: "FG_MUTED",
    RateSignal.NONE: "FG_MUTED",
    PnLSignal.NONE: "FG_MUTED",
}


def signal_color(signal: RateSignal | PnLSignal) -> str:
    """信号 → 当前主题颜色（统一入口，两种信号类型共用）。

    收益率信号与盈亏标签的信号→颜色映射在同一张表，新增信号类型
    只需在 _SIGNAL_TO_KEY 加一项。
    """
    key = _SIGNAL_TO_KEY.get(signal, "FG_MUTED")
    return get_color(key)


def summary_style(signal: RateSignal) -> str:
    """汇总标签样式：根据信号返回 QSS 样式字符串（颜色+字号+粗细）。

    数据不足/仅 1 条 → 灰字小号；否则 → 信号色常规字号。
    """
    if signal is RateSignal.NONE:
        return f"color: {get_color('FG_MUTED')}; font-size: 12px; font-weight: bold;"
    return f"color: {signal_color(signal)}; font-size: 13px; font-weight: bold;"


def button_style(role: str) -> str:
    """按角色返回按钮 QSS 样式字符串（运行时解析，避免 import 期冻结）。

    角色：
    - ``edit_save``：编辑模式保存按钮（BTN_BG 色）
    - ``danger``：取消复用/危险操作按钮（DANGER_BG 色）
    """
    if role == "edit_save":
        bg = get_color("BTN_BG")
        fg = get_color("BTN_FG")
        hover_bg = get_color("BTN_BG_HOVER")
        return (
            f"QPushButton#saveBtn {{"
            f"background-color: {bg};"
            f"color: {fg};"
            f"padding: 8px 28px;"
            f"font-weight: bold;"
            f"}}"
            f"QPushButton#saveBtn:hover {{"
            f"background-color: {hover_bg};"
            f"}}"
        )
    if role == "danger":
        bg = get_color("DANGER_BG")
        fg = get_color("DANGER_FG")
        border = get_color("DANGER_BORDER")
        hover_bg = get_color("DANGER_HOVER_BG")
        return (
            f"QPushButton {{"
            f"background-color: {bg};"
            f"color: {fg};"
            f"border: 1px solid {border};"
            f"border-radius: 5px;"
            f"padding: 6px 14px;"
            f"font-size: 11px;"
            f"font-weight: bold;"
            f"}}"
            f"QPushButton:hover {{"
            f"background-color: {hover_bg};"
            f"color: #ffffff;"
            f"}}"
        )
    return ""


def generate_qss(theme_name: str) -> str:
    """根据主题名称生成完整 QSS 样式表。"""
    t = THEMES.get(theme_name, THEMES["light"])

    bg = t["BG"]
    fg_label = t["FG_LABEL"]
    fg_muted = t["FG_MUTED"]
    fg_pos = t["FG_POS"]
    fg_neg = t["FG_NEG"]
    fg_today = t["FG_TODAY"]
    btn_bg = t["BTN_BG"]
    btn_fg = t["BTN_FG"]
    btn_hover = t["BTN_BG_HOVER"]
    border_def = t["BORDER_DEFAULT"]
    border_valid = t["BORDER_VALID"]
    border_invalid = t["BORDER_INVALID"]
    border_warning = t["BORDER_WARNING"]
    placeholder = t["PLACEHOLDER"]
    muted_bg = t["MUTED_BG"]
    card_bg = t["CARD_BG"]
    card_border = t["CARD_BORDER"]
    input_bg = t["INPUT_BG"]
    input_fg = t["INPUT_FG"]
    table_text = t["TABLE_TEXT"]
    table_text_bold = t["TABLE_TEXT_BOLD"]
    table_row_even = t["TABLE_ROW_EVEN_BG"]
    table_row_odd = t["TABLE_ROW_ODD_BG"]
    table_header_bg = t["TABLE_HEADER_BG"]
    table_header_fg = t["TABLE_HEADER_FG"]
    chart_bg = t["CHART_BG"]
    separator = t["SEPARATOR"]

    return f"""
/* ═══════════════════════════════════════════
   全局
   ═══════════════════════════════════════════ */
QMainWindow {{
    background-color: {bg};
}}
QWidget#centralWidget {{
    background-color: {bg};
}}

/* ═══════════════════════════════════════════
   Label
   ═══════════════════════════════════════════ */
QLabel {{
    color: {fg_label};
    background-color: transparent;
}}
QLabel#titleLabel {{
    color: {table_text_bold};
    font-size: 18px;
    font-weight: bold;
}}
QLabel#dateLabel {{
    color: {fg_muted};
    font-size: 12px;
}}
QLabel#hintLabel {{
    color: {placeholder};
    font-size: 10px;
}}
QLabel#savedIndicator {{
    color: {fg_pos};
    font-size: 10px;
}}
QLabel#todayStatusLabel {{
    color: {fg_today};
    font-size: 10px;
    font-weight: bold;
}}

/* ═══════════════════════════════════════════
   LineEdit
   ═══════════════════════════════════════════ */
QLineEdit {{
    background-color: {input_bg};
    color: {input_fg};
    border: 1px solid {border_def};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 13px;
    selection-background-color: {btn_bg};
    selection-color: {btn_fg};
}}
QLineEdit:focus {{
    border-color: {btn_bg};
}}
QLineEdit[validity="valid"] {{
    border-color: {border_valid};
}}
QLineEdit[validity="invalid"] {{
    border-color: {border_invalid};
}}
QLineEdit[validity="warning"] {{
    border-color: {border_warning};
}}
QLineEdit::placeholder {{
    color: {placeholder};
}}

/* ═══════════════════════════════════════════
   PushButton
   ═══════════════════════════════════════════ */
QPushButton {{
    border: none;
    border-radius: 5px;
    padding: 6px 20px;
    font-size: 12px;
}}
QPushButton#saveBtn {{
    background-color: {btn_bg};
    color: {btn_fg};
    padding: 8px 28px;
    font-weight: bold;
}}
QPushButton#saveBtn:hover {{
    background-color: {btn_hover};
}}
QPushButton#saveBtn:pressed {{
    background-color: {btn_hover};
    padding: 9px 28px 7px 28px;
}}
QPushButton#saveBtn:disabled {{
    background-color: {muted_bg};
    color: {fg_muted};
}}
QPushButton#cancelEditBtn {{
    background-color: {muted_bg};
    color: {fg_label};
    padding: 8px 16px;
}}
QPushButton#cancelEditBtn:hover {{
    background-color: {separator};
}}
QPushButton#reuseBtn {{
    background-color: {muted_bg};
    color: {fg_label};
    padding: 6px 14px;
    font-size: 11px;
}}
QPushButton#reuseBtn:hover {{
    background-color: {separator};
    color: {table_text_bold};
}}
QPushButton#themeBtn, QPushButton#pinBtn, QPushButton#exportBtn {{
    background-color: {muted_bg};
    color: {fg_muted};
    padding: 4px 10px;
    font-size: 10px;
}}
QPushButton#themeBtn:hover, QPushButton#pinBtn:hover, QPushButton#exportBtn:hover {{
    background-color: {separator};
}}
QPushButton#pinBtn[active="true"] {{
    background-color: {btn_bg};
    color: {btn_fg};
}}

/* ═══════════════════════════════════════════
   表格
   ═══════════════════════════════════════════ */
QTableWidget {{
    background-color: {table_row_even};
    alternate-background-color: {table_row_odd};
    color: {table_text};
    gridline-color: {separator};
    border: none;
    font-size: 11px;
}}
QTableWidget::item {{
    padding: 6px 8px;
}}
QTableWidget::item:hover {{
    background-color: {t.get("TABLE_ROW_HOVER_BG", muted_bg)};
}}
QTableWidget::item:selected {{
    background-color: {btn_bg};
    color: {btn_fg};
}}
QHeaderView::section {{
    background-color: {table_header_bg};
    color: {table_header_fg};
    padding: 6px 4px;
    border: none;
    border-bottom: 1px solid {separator};
    font-weight: bold;
    font-size: 11px;
}}

/* ═══════════════════════════════════════════
   卡片容器
   ═══════════════════════════════════════════ */
QFrame#cardFrame {{
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 6px;
}}
QFrame#cardBorder {{
    background-color: {card_border};
}}

/* ═══════════════════════════════════════════
   状态栏 / 提示
   ═══════════════════════════════════════════ */
QStatusBar {{
    background-color: {bg};
    color: {placeholder};
    font-size: 8px;
}}

/* ═══════════════════════════════════════════
   ScrollBar
   ═══════════════════════════════════════════ */
QScrollBar:vertical {{
    background: {muted_bg};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {separator};
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

/* ═══════════════════════════════════════════
   ToolTip
   ═══════════════════════════════════════════ */
QToolTip {{
    background-color: {input_bg};
    color: {input_fg};
    border: 1px solid {border_def};
    border-radius: 4px;
    padding: 4px;
}}
"""

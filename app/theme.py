"""
主题系统（PySide6 版）：色板定义 + QSS 样式生成 + 主题切换。

主题数据的单一真实来源。所有 UI 组件通过此模块获取颜色值。
"""

from __future__ import annotations

__all__ = [
    "THEMES",
    "generate_qss",
    "get_color",
    "get_theme",
    "set_theme",
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
        "BG": "#0d1114",             # 极暗冷灰底，接近纯黑但保留冷调（oklch 0.08 0.006 230）
        "FG_LABEL": "#c8d6e5",       # 冷银白，高对比度
        "FG_MUTED": "#8395a7",       # 冷灰绿，次级文字
        "FG_POS": "#5eeea8",         # 荧光薄荷绿涨（高饱和，暗底醒目）
        "FG_NEG": "#ff6b7f",         # 珊瑚红跌（提亮，暗底可读）
        "FG_TODAY": "#00ddce",       # 冰青荧光（色相~178，亮而不刺）
        "BTN_BG": "#00ddce",         # 冰青主按钮
        "BTN_BG_HOVER": "#00f5e4",   # 悬停提亮
        "BTN_FG": "#0a0e12",         # 深底文字
        "BORDER_DEFAULT": "#1e2a33", # 暗蓝灰实色边框（Qt QSS 不支持 #AARRGGBB）
        "BORDER_VALID": "#5eeea8",
        "BORDER_INVALID": "#ff6b7f",
        "BORDER_WARNING": "#e5b04f",
        "SEPARATOR": "#1a2630",      # 比基底亮两阶分隔线
        "PLACEHOLDER": "#566677",    # 暗灰占位
        "MUTED_BG": "#141c23",       # 次级按钮底，比基底亮一阶
        "PIN_OFF_BG": "#141c23",
        "PIN_ON_BG": "#00ddce",      # 冰青钉选
        "CHART_CASH": "#00ddce",     # 冰青荧光虚线（现金）
        "CHART_WAREHOUSE": "#5eeea8",# 荧光薄荷绿实线（仓库价值）
        "CHART_TOTAL": "#5eeea8",
        "CHART_GRID": "#1a2630",     # 极暗网格
        "CHART_BG": "#0a0f12",       # 图表区比基底更暗
        "CHART_AXIS": "#8395a7",
        "CHART_TEXT": "#c8d6e5",
        "TABLE_TEXT": "#c8d6e5",
        "TABLE_TEXT_BOLD": "#e8eff5",# 近白强调
        "TABLE_ROW_EVEN_BG": "#0d1114",
        "TABLE_ROW_ODD_BG": "#121820",
        "TABLE_ROW_HOVER_BG": "#1a2630",
        "TABLE_ROW_TODAY_BG": "#0f2628",  # 今日行暗冰青底
        "TABLE_HEADER_BG": "#141c23",
        "TABLE_HEADER_FG": "#8395a7",
        "CARD_BG": "#121820",        # 卡片比基底亮一阶
        "CARD_BORDER": "#1e2a33",
        "INPUT_BG": "#161e27",       # 输入框比卡片微亮
        "INPUT_FG": "#c8d6e5",
        # 操作按钮语义色
        "DANGER_BG": "#261820",
        "DANGER_FG": "#ff6b7f",
        "DANGER_BORDER": "#3d1f28",
        "DANGER_HOVER_BG": "#e0556a",
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

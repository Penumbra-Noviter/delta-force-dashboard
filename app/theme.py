"""
主题系统（PySide6 版）：QSS 样式生成 + 主题色板。

从根目录 config.py 导入 THEMES 色板字典和主题切换函数，
专供 app/ 内的 PySide6 组件使用。
"""

from __future__ import annotations

import config as _base_config

__all__ = [
    "THEMES",
    "generate_qss",
    "get_color",
    "get_theme",
    "set_theme",
]

# ── 从根目录复用主题色板 ─────────────────────────────────
THEMES = _base_config.THEMES
get_theme = _base_config.get_theme
set_theme = _base_config.set_theme
get_color = _base_config.get_color


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
    font-size: 10px;
}}
QLabel#hintLabel {{
    color: {placeholder};
    font-size: 8px;
}}
QLabel#savedIndicator {{
    color: {fg_pos};
    font-size: 9px;
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
QLineEdit::placeholder {{
    color: {placeholder};
}}

/* ═══════════════════════════════════════════
   PushButton
   ═══════════════════════════════════════════ */
QPushButton {{
    border: none;
    border-radius: 4px;
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
QPushButton#themeBtn, QPushButton#pinBtn {{
    background-color: {muted_bg};
    color: {fg_muted};
    padding: 4px 10px;
    font-size: 9px;
}}
QPushButton#themeBtn:hover, QPushButton#pinBtn:hover {{
    background-color: {separator};
}}
QPushButton#pinBtn[active="true"] {{
    background-color: {btn_bg};
    color: #ffffff;
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
    font-size: 10px;
}}
QTableWidget::item {{
    padding: 4px 8px;
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
    font-size: 10px;
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

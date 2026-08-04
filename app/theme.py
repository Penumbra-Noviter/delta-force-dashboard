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
        # ── Sage Ledger（Set 1：forest green on sage paper）──
        # 亮色基调：暖灰绿纸底 + 森林绿主色，语义色脱离绿色域
        "BG": "#eef0ec",             # sage 暖纸，替代纯白
        "FG_LABEL": "#3c4a43",       # ink-2 正文
        "FG_MUTED": "#6d7d74",       # ink-3 次级（WCAG AA 4.5:1）
        "FG_POS": "#2C7A8C",         # 蓝绿涨（迁移语义色，避免与森林绿 accent 冲突）
        "FG_NEG": "#C0453C",         # 深红跌
        "FG_TODAY": "#2F6B4F",       # 森林绿主色（今日高亮）
        "BTN_BG": "#2F6B4F",         # 森林绿主按钮
        "BTN_BG_HOVER": "#3C8A63",   # 悬停提亮
        "BTN_FG": "#ffffff",         # 按钮文字
        "BORDER_DEFAULT": "rgba(20,32,26,.07)",  # 半透明 hairline
        "BORDER_VALID": "#2C7A8C",
        "BORDER_INVALID": "#C0453C",
        "BORDER_WARNING": "#B77A16",  # amber 警告
        "SEPARATOR": "#d6d3cc",       # 暖灰分隔线
        "PLACEHOLDER": "#6d7d74",
        "MUTED_BG": "#f3f5f1",        # panel-2 次级底
        "PIN_OFF_BG": "#f3f5f1",
        "PIN_ON_BG": "#2F6B4F",
        "CHART_CASH": "#C08A3E",      # 金色（accent-2 现金线）
        "CHART_WAREHOUSE": "#2F6B4F", # 森林绿（accent 仓库线）
        "CHART_TOTAL": "#2C7A8C",
        "CHART_GRID": "#e2e4df",
        "CHART_BG": "#f5f4f0",
        "CHART_AXIS": "#6d7d74",
        "CHART_TEXT": "#3c4a43",
        "TABLE_TEXT": "#3c4a43",
        "TABLE_TEXT_BOLD": "#14201a",   # ink-1 强调
        "TABLE_ROW_EVEN_BG": "#ffffff",
        "TABLE_ROW_ODD_BG": "#f3f5f1",
        "TABLE_ROW_HOVER_BG": "#e8ece4",
        "TABLE_ROW_TODAY_BG": "#e6f0e8",  # 今日行浅青绿底
        "TABLE_HEADER_BG": "#f3f5f1",
        "TABLE_HEADER_FG": "#6d7d74",
        "CARD_BG": "#ffffff",
        "CARD_BORDER": "rgba(20,32,26,.07)",
        "INPUT_BG": "#ffffff",
        "INPUT_FG": "#14201a",
        "PANEL_2": "#f3f5f1",
        # 操作按钮语义色
        "DANGER_BG": "#fef2f2",
        "DANGER_FG": "#C0453C",
        "DANGER_BORDER": "#fecaca",
        "DANGER_HOVER_BG": "#C0453C",
    },
    "dark": {
        # ── Midnight & Amber（Set 11：amber on midnight）──
        # 暗色基调：午夜蓝底 + 琥珀橙主色，适合金融工具夜间使用
        "BG": "#08090f",             # 午夜蓝底（非纯黑）
        "FG_LABEL": "#a8adbd",       # ink-2 正文
        "FG_MUTED": "#848aa0",       # ink-3 次级（WCAG AA 4.5:1 对 panel-2）
        "FG_POS": "#3FCB86",         # 薄荷绿涨
        "FG_NEG": "#FF5F56",         # 珊瑚红跌
        "FG_TODAY": "#E8A33D",       # 琥珀橙（主色/今日高亮）
        "BTN_BG": "#E8A33D",         # 琥珀主按钮
        "BTN_BG_HOVER": "#F0B555",   # 悬停提亮
        "BTN_FG": "#141008",         # 深底文字（琥珀色上显深字，AA）
        "BORDER_DEFAULT": "rgba(255,255,255,.07)",  # 半透明白 hairline
        "BORDER_VALID": "#3FCB86",
        "BORDER_INVALID": "#FF5F56",
        "BORDER_WARNING": "#E8A33D",
        "SEPARATOR": "rgba(255,255,255,.06)",
        "PLACEHOLDER": "#848aa0",
        "MUTED_BG": "#1a1d27",       # panel-2
        "PIN_OFF_BG": "#1a1d27",
        "PIN_ON_BG": "#E8A33D",
        "CHART_CASH": "#7B8CFF",     # 紫蓝色（accent-2 现金线）
        "CHART_WAREHOUSE": "#E8A33D",# 琥珀橙（accent 仓库线）
        "CHART_TOTAL": "#3FCB86",
        "CHART_GRID": "rgba(255,255,255,.05)",
        "CHART_BG": "#0c0e16",
        "CHART_AXIS": "#848aa0",
        "CHART_TEXT": "#a8adbd",
        "TABLE_TEXT": "#a8adbd",
        "TABLE_TEXT_BOLD": "#eceef5",  # ink-1
        "TABLE_ROW_EVEN_BG": "#12141c",
        "TABLE_ROW_ODD_BG": "#1a1d27",
        "TABLE_ROW_HOVER_BG": "#222536",
        "TABLE_ROW_TODAY_BG": "#1e1a14",  # 今日行暗暖橙底
        "TABLE_HEADER_BG": "#1a1d27",
        "TABLE_HEADER_FG": "#848aa0",
        "CARD_BG": "#12141c",
        "CARD_BORDER": "rgba(255,255,255,.07)",
        "INPUT_BG": "#1a1d27",
        "INPUT_FG": "#eceef5",
        "PANEL_2": "#1a1d27",
        # 操作按钮语义色
        "DANGER_BG": "#1f1418",
        "DANGER_FG": "#FF5F56",
        "DANGER_BORDER": "#2d1a20",
        "DANGER_HOVER_BG": "#FF5F56",
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
            f"padding: 10px 32px;"
            f"font-weight: 600;"
            f"border-radius: 8px;"
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
            f"border-radius: 8px;"
            f"padding: 8px 18px;"
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
    font-weight: 700;
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
    font-weight: 600;
}}
QLabel#summaryLabel, QLabel#cashSummaryLabel {{
    font-size: 14px;
    font-weight: 600;
}}

/* ═══════════════════════════════════════════
   LineEdit
   ═══════════════════════════════════════════ */
QLineEdit {{
    background-color: {input_bg};
    color: {input_fg};
    border: 1px solid {border_def};
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 13px;
    selection-background-color: {btn_bg};
    selection-color: {btn_fg};
}}
QLineEdit:focus {{
    border: 2px solid {btn_bg};
    padding: 5px 11px;
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
    border-radius: 8px;
    padding: 6px 20px;
    font-size: 12px;
    font-weight: 500;
}}
QPushButton#saveBtn {{
    background-color: {btn_bg};
    color: {btn_fg};
    padding: 10px 32px;
    font-weight: 600;
    font-size: 13px;
    border-radius: 8px;
}}
QPushButton#saveBtn:hover {{
    background-color: {btn_hover};
}}
QPushButton#saveBtn:pressed {{
    background-color: {btn_hover};
    padding: 11px 32px 9px 32px;
}}
QPushButton#saveBtn:disabled {{
    background-color: {muted_bg};
    color: {fg_muted};
}}
QPushButton#cancelEditBtn {{
    background-color: {muted_bg};
    color: {fg_label};
    padding: 10px 20px;
    border-radius: 8px;
}}
QPushButton#cancelEditBtn:hover {{
    background-color: {separator};
}}
QPushButton#reuseBtn {{
    background-color: {muted_bg};
    color: {fg_label};
    padding: 8px 16px;
    font-size: 11px;
    border-radius: 8px;
}}
QPushButton#reuseBtn:hover {{
    background-color: {separator};
    color: {table_text_bold};
}}
QPushButton#themeBtn, QPushButton#pinBtn, QPushButton#exportBtn {{
    background-color: {muted_bg};
    color: {fg_muted};
    padding: 6px 14px;
    font-size: 10px;
    border-radius: 8px;
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
    border-radius: 8px;
    font-size: 11px;
}}
QTableWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {separator};
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
    padding: 8px 6px;
    border: none;
    border-bottom: 1px solid {separator};
    font-weight: 600;
    font-size: 11px;
}}

/* ═══════════════════════════════════════════
   卡片容器
   ═══════════════════════════════════════════ */
QFrame#cardFrame {{
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
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
    width: 4px;
    border-radius: 2px;
}}
QScrollBar::handle:vertical {{
    background: {separator};
    border-radius: 2px;
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
    border-radius: 8px;
    padding: 6px 10px;
}}
"""

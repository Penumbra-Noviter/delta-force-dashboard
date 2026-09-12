"""
主题系统（PySide6 版）：色板定义 + QSS 样式生成 + 主题切换。

主题数据的单一真实来源。所有 UI 组件通过此模块获取颜色值。
"""

from __future__ import annotations

import logging
import re

from signals import PnLSignal, RateSignal

__all__ = [
    "THEMES",
    "PRESET_NAMES",
    "PRESET_LABELS",
    "CUSTOM",
    "ANCHOR_KEYS",
    "clean_overrides",
    "contrast_hints",
    "generate_qss",
    "get_color",
    "is_hex_color",
    "register_custom",
    "resolve_palette",
    "set_theme",
    "signal_color",
    "summary_style",
]

logger = logging.getLogger(__name__)

# 6 位 hex 颜色字面量（#RRGGBB，大小写均可，含 # 前缀）
_HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}")

# ── 主题色板 ──────────────────────────────────────────
# 护眼配色：暖纸白底 + 温润青色（teal）主色调，降低蓝光刺激
# 语义色保留绿涨红跌（国际惯例），青色主色与语义色明确区分
THEMES = {
    "light": {
        # ── Sage Ledger（Set 1：forest green on sage paper）──
        # 亮色基调：暖灰绿纸底 + 森林绿主色，语义色脱离绿色域
        # 柔和化（2026-08-15）：卡面由纯白改为暖白、主色与语义色降饱和提亮，
        # 全角色保持 WCAG AA 与 U-03 明度带契约（对 CARD_BG 均 ≥4.5:1）。
        "BG": "#eef1ec",             # sage 暖纸，替代纯白（微暖）
        "FG_LABEL": "#4a5a51",       # ink-2 正文（对比 →7.2:1，柔和）
        "FG_MUTED": "#75837b",       # ink-3 次级（WCAG AA 4.5:1）
        "FG_POS": "#307888",         # 蓝绿涨（降饱和保亮度，S 0.52→0.48）
        "FG_NEG": "#b54e46",         # 深红跌（降饱和，S 0.52→0.44）
        "FG_TODAY": "#3d8063",       # 森林绿主色（今日高亮，提亮）
        "BTN_BG": "#3d8063",         # 森林绿主按钮（提亮，白字 4.7:1）
        "BTN_BG_HOVER": "#4a8f6f",   # 悬停提亮
        "BTN_FG": "#ffffff",         # 按钮文字
        "BTN_HOVER_FG": "#ffffff",   # 按钮 hover 前景（操作列/危险按钮，双主题同值）
        "BORDER_DEFAULT": "rgba(20,32,26,.08)",  # 半透明 hairline
        "BORDER_VALID": "#307888",
        "BORDER_INVALID": "#b54e46",
        "BORDER_WARNING": "#b07d2a",  # amber 警告（降饱和）
        "SEPARATOR": "#d8d8d0",       # 暖灰分隔线
        "PLACEHOLDER": "#75837b",
        "MUTED_BG": "#f1f3f0",        # panel-2 次级底
        "CHART_CASH": "#c99a4e",      # 金色（accent-2 现金线，提亮降饱和）
        "CHART_WAREHOUSE": "#3d8063", # 森林绿（accent 仓库线）
        "CHART_TOTAL": "#307888",
        "CHART_GRID": "#e4e6e1",
        "CHART_BG": "#f5f6f2",
        "OVERLAY_BG": "rgba(0, 0, 0, 35)",    # 图表稀疏提示遮罩（双主题同值）
        "CHART_AXIS": "#75837b",
        "TABLE_TEXT": "#4a5a51",
        "TABLE_TEXT_BOLD": "#1e2b24",   # ink-1 强调
        "TABLE_ROW_EVEN_BG": "#fcfdfb",
        "TABLE_ROW_ODD_BG": "#f3f5f1",
        "TABLE_ROW_HOVER_BG": "#e9ede6",
        "TABLE_ROW_TODAY_BG": "#e4efe7",  # 今日行浅青绿底
        "TABLE_HEADER_BG": "#f1f3f0",
        "TABLE_HEADER_FG": "#75837b",
        "CARD_BG": "#fcfdfb",         # 暖白卡片（对装饰色 min 4.67:1）
        "CARD_BORDER": "rgba(20,32,26,.08)",
        "INPUT_BG": "#fdfefc",
        "INPUT_FG": "#1e2b24",
        # 新增：交互态
        "FOCUS_RING": "#5a9a78",
        "SELECTION_BG": "#3d8063",
        "SELECTION_FG": "#ffffff",
        "NAV_HOVER_BG": "rgba(128, 128, 128, 0.1)",  # 侧边栏导航 hover（浅色：中性灰 overlay）
        "NAV_SELECT_BG": "rgba(61, 128, 99, 0.13)",  # 导航选中浅底 pill（森林绿 13% 透明）
        # 新增：文字层级
        "TEXT_PRIMARY": "#1e2b24",
        "TEXT_SECONDARY": "#4a5a51",
        # 新增：边框
        "BORDER_HEAVY": "rgba(20,32,26,.15)",
        # 新增：语义扩展
        "WARNING_BG": "#f3ddab",   # 琥珀中调底（今日未录入 pill；与 sage 底亮度差 ≈0.11 可辨）
        "WARNING_FG": "#6e580a",   # 深琥珀文字（10px 小字对 #F1D9A0 对比 ≈7:1，AA）
        "BADGE_FG": "#ffffff",         # 盈亏标签文字（双主题同值，保持既有白字）
        # 新增：装饰色（兑换页 7 包标签，U-03 色彩角色系统化）
        # 角色规则：装饰色与语义色（FG_POS/FG_NEG）显式分离——包标签只做分类标识，
        # 涨跌色只做数值语义，二者不共用取值（dark 下曾与语义色完全同值，已修）。
        # 明度带：light 深墨带 L∈[0.20,0.32]（对白卡片 AA 4.5:1 的深字底线）；
        # 固定键清单 PACKAGE_COLOR_0~6，双主题各自定义取值（不抽常亮色，防 Locality 坑）。
        "PACKAGE_COLOR_0": "#1f167d",   # 蓝紫（通行证基础，降饱和）
        "PACKAGE_COLOR_1": "#78651c",   # 暗金（4 级）
        "PACKAGE_COLOR_2": "#176454",   # 青绿（3 级）
        "PACKAGE_COLOR_3": "#7c201d",   # 深红（5 级）
        "PACKAGE_COLOR_4": "#591764",   # 深紫（通行证高级）
        "PACKAGE_COLOR_5": "#573319",   # 橙褐（进阶物流，偏红橙）
        "PACKAGE_COLOR_6": "#601639",   # 莓红（特级物流）
        # 新增：滚动条
        "SCROLLBAR_BG": "#f1f3f0",
        "SCROLLBAR_HANDLE": "#d8d8d0",
        # 操作按钮语义色
        "DANGER_BG": "#fbeaea",
        "DANGER_FG": "#b54e46",
        "DANGER_BORDER": "#f2c2c0",
        "DANGER_HOVER_BG": "#b54e46",
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
        "BTN_HOVER_FG": "#ffffff",   # 按钮 hover 前景（双主题同值，保持既有白字）
        "BORDER_DEFAULT": "rgba(255,255,255,.07)",  # 半透明白 hairline
        "BORDER_VALID": "#3FCB86",
        "BORDER_INVALID": "#FF5F56",
        "BORDER_WARNING": "#E8A33D",
        "SEPARATOR": "rgba(255,255,255,.06)",
        "PLACEHOLDER": "#848aa0",
        "MUTED_BG": "#1a1d27",       # panel-2
        "CHART_CASH": "#7B8CFF",     # 紫蓝色（accent-2 现金线）
        "CHART_WAREHOUSE": "#E8A33D",# 琥珀橙（accent 仓库线）
        "CHART_TOTAL": "#3FCB86",
        "CHART_GRID": "#FFFFFF0D",        # RRGGBBAA（alpha 13≈5%）；pyqtgraph 不解析 rgba() 浮点 alpha
        "CHART_BG": "#0c0e16",
        "OVERLAY_BG": "rgba(0, 0, 0, 35)",
        "CHART_AXIS": "#848aa0",
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
        # 新增：交互态
        "FOCUS_RING": "#F0B555",
        "SELECTION_BG": "#E8A33D",
        "SELECTION_FG": "#141008",
        "NAV_HOVER_BG": "rgba(255, 255, 255, 0.1)",  # 侧边栏导航 hover（暗色：半透明白 overlay）
        "NAV_SELECT_BG": "rgba(232, 163, 61, 0.14)",  # 导航选中浅底 pill（琥珀 14% 透明）
        # 新增：文字层级
        "TEXT_PRIMARY": "#eceef5",
        "TEXT_SECONDARY": "#a8adbd",
        # 新增：边框
        "BORDER_HEAVY": "rgba(255,255,255,.12)",
        # 新增：语义扩展
        "WARNING_BG": "#3A2E1A",   # 琥珀淡底（今日未录入 pill；原 #261e14 在午夜底上过暗）
        "WARNING_FG": "#E8A33D",
        "BADGE_FG": "#ffffff",
        # 新增：装饰色（兑换页 7 包标签，U-03；角色规则同 light 主题注释）
        # 明度带：dark 亮彩带 L∈[0.72,0.84]（与涨跌语义色 FG_POS L≈0.52 / FG_NEG L≈0.67 拉开 ≥0.05）
        "PACKAGE_COLOR_0": "#BFA9F4",   # 蓝紫（通行证基础）
        "PACKAGE_COLOR_1": "#FAF080",   # 亮金（4 级）
        "PACKAGE_COLOR_2": "#ADEBE6",   # 青绿（3 级）
        "PACKAGE_COLOR_3": "#FB8387",   # 珊瑚红（5 级）
        "PACKAGE_COLOR_4": "#EC89F5",   # 亮紫（通行证高级）
        "PACKAGE_COLOR_5": "#F7CF97",   # 蜜桃（进阶物流）
        "PACKAGE_COLOR_6": "#F3A5C5",   # 粉红（特级物流）
        # 新增：滚动条
        "SCROLLBAR_BG": "#1a1d27",
        "SCROLLBAR_HANDLE": "rgba(255,255,255,.12)",
        # 操作按钮语义色
        "DANGER_BG": "#1f1418",
        "DANGER_FG": "#FF5F56",
        "DANGER_BORDER": "#2d1a20",
        "DANGER_HOVER_BG": "#FF5F56",
    },
    "nord": {
        # ── Nord（Set 12：极夜底 + frost 冷调主色）──
        # 暗色基调：Nord 极夜蓝灰底 + 冷调 frost 青主色；语义色保持绿涨红跌。
        # 装饰色「Nord 冷调但提饱和」亮彩集：原版 Nord aurora 饱和度全部 <0.55
        # 会撞 U-03 饱和度门槛，故重调为提饱和亮彩（实现期经 _hls/_contrast_ratio/
        # _delta_e76 实测，见 tests/test_theme_roles.py 角色阈值守卫）。
        "BG": "#2E3440",             # nord0 极夜（主背景）
        "FG_LABEL": "#D8DEE9",       # nord4 正文（frost 亮灰）
        "FG_MUTED": "#9AA7B8",       # 次级文字（对 CARD_BG ≥4.5:1）
        "FG_POS": "#A3BE8C",         # nord14 绿涨（语义色）
        "FG_NEG": "#BF616A",         # nord11 红跌（语义色）
        "FG_TODAY": "#88C0D0",       # nord8 frost 青（主色/今日高亮）
        "BTN_BG": "#88C0D0",         # nord8 frost 青主按钮（深字 AA）
        "BTN_BG_HOVER": "#A3D5E2",   # 悬停提亮
        "BTN_FG": "#2E3440",         # nord0 深底文字（青底显深字）
        "BTN_HOVER_FG": "#ECEFF4",   # 危险按钮 hover 前景（nord6 雪白）
        "BORDER_DEFAULT": "rgba(255,255,255,.08)",
        "BORDER_VALID": "#A3BE8C",
        "BORDER_INVALID": "#BF616A",
        "BORDER_WARNING": "#EBCB8B",  # nord13 黄（警告）
        "SEPARATOR": "rgba(255,255,255,.06)",
        "PLACEHOLDER": "#9AA7B8",
        "MUTED_BG": "#434C5E",        # nord2 panel-2 次级底
        "CHART_CASH": "#88C0D0",      # frost 青（现金线）
        "CHART_WAREHOUSE": "#EBCB8B", # nord13 黄（仓库线）
        "CHART_TOTAL": "#A3BE8C",     # nord14 绿（总盈亏线=涨色）
        "CHART_GRID": "#4C566A",      # nord3（6 位 hex；pyqtgraph 不解析 rgba）
        "CHART_BG": "#2E3440",
        "OVERLAY_BG": "rgba(0, 0, 0, 35)",
        "CHART_AXIS": "#9AA7B8",
        "TABLE_TEXT": "#D8DEE9",
        "TABLE_TEXT_BOLD": "#ECEFF4",
        "TABLE_ROW_EVEN_BG": "#3B4252",
        "TABLE_ROW_ODD_BG": "#434C5E",
        "TABLE_ROW_HOVER_BG": "#4C566A",
        "TABLE_ROW_TODAY_BG": "#3D4A5C",
        "TABLE_HEADER_BG": "#434C5E",
        "TABLE_HEADER_FG": "#9AA7B8",
        "CARD_BG": "#3B4252",         # nord1 卡片
        "CARD_BORDER": "rgba(255,255,255,.07)",
        "INPUT_BG": "#434C5E",
        "INPUT_FG": "#ECEFF4",
        "FOCUS_RING": "#88C0D0",
        "SELECTION_BG": "#88C0D0",
        "SELECTION_FG": "#2E3440",
        "NAV_HOVER_BG": "rgba(255, 255, 255, 0.1)",
        "NAV_SELECT_BG": "rgba(136, 192, 208, 0.14)",
        "TEXT_PRIMARY": "#ECEFF4",
        "TEXT_SECONDARY": "#D8DEE9",
        "BORDER_HEAVY": "rgba(255,255,255,.12)",
        "WARNING_BG": "#3B3623",
        "WARNING_FG": "#EBCB8B",
        "BADGE_FG": "#ECEFF4",
        # 装饰色（Nord 冷调提饱和亮彩，U-03 角色规则：S≥0.55 / 对 CARD_BG AA 4.5:1 /
        # 两两 ΔE76≥25 / 与 FG_POS·FG_NEG 亮度差≥0.05 / 明度带 NORD_BAND）
        "PACKAGE_COLOR_0": "#9AAEF2",   # 蓝紫（通行证基础）
        "PACKAGE_COLOR_1": "#F8EA7F",   # 金（4 级）
        "PACKAGE_COLOR_2": "#8FE3DF",   # 青绿（3 级）
        "PACKAGE_COLOR_3": "#F6A196",   # 珊瑚红（5 级）
        "PACKAGE_COLOR_4": "#D29BF5",   # 紫（通行证高级）
        "PACKAGE_COLOR_5": "#E4C797",   # 橙（进阶物流）
        "PACKAGE_COLOR_6": "#EF9AC0",   # 粉（特级物流）
        # 滚动条
        "SCROLLBAR_BG": "#434C5E",
        "SCROLLBAR_HANDLE": "rgba(255,255,255,.12)",
        # 操作按钮语义色
        "DANGER_BG": "#2E2326",
        "DANGER_FG": "#BF616A",
        "DANGER_BORDER": "#4A2C33",
        "DANGER_HOVER_BG": "#BF616A",
    },
}

# ── 预设主题名单（单一来源，DFD-8）─────────────────────
# 菜单顺序 / 显示标签 / base 下拉共用；新增预设需同步改 THEMES 与此处，
# 由 tests/test_theme_custom.py 集合守卫兜底（漏改名单即红）。
PRESET_NAMES: tuple[str, ...] = ("light", "dark", "nord")
PRESET_LABELS: dict[str, str] = {
    "light": "亮色",
    "dark": "暗色",
    "nord": "Nord",
}

# ── 自定义主题单槽位 + 六元锚点白名单 ─────────────────
# 自定义主题存「派生源 base + 锚点覆盖 overrides」，运行时合并为完整色板，
# 其余键继承 base（不展开 50 键快照，见 resolve_palette）。
CUSTOM: dict[str, dict[str, object]] = {}

# 可覆写锚点白名单：仅这 6 键允许覆盖；装饰色 / 表格行底 / 边框 / 图表色 /
# 图标色（FG_MUTED / FG_LABEL / BTN_FG）一律继承 base（spec · Implementation Decisions）。
ANCHOR_KEYS = (
    "BTN_BG",
    "BTN_BG_HOVER",
    "FG_TODAY",
    "BG",
    "FG_POS",
    "FG_NEG",
)


# ── 当前主题名称（运行时由 UI 切换） ─────────────────
_current_theme = "light"


def resolve_palette(name: str) -> dict[str, str]:
    """解析主题名 → 完整色板（只读视图语义，调用方不得原地改）。

    内置命中直返；自定义命中合并 `{**THEMES[base], **overrides}`；
    其余（含畸形自定义槽位）回退 `THEMES["light"]`。全函数永不 raise。
    """
    if name in THEMES:
        return THEMES[name]
    entry = CUSTOM.get(name)
    if isinstance(entry, dict):
        base = entry.get("base")
        overrides = entry.get("overrides")
        if base in THEMES and isinstance(overrides, dict):
            return {**THEMES[base], **overrides}
    return THEMES["light"]


def register_custom(name: str, base: str, overrides: dict[str, str]) -> None:
    """注册自定义主题槽位（name → base 派生源 + 锚点覆盖）。

    name 与内置主题重名、或 base 非内置主题时拒绝写入并记 warning
    （CUSTOM 保持原状，不 raise）；合法时写入 `{"base", "overrides"}`，
    overrides 经 `clean_overrides` 清洗（非法 hex / 非锚点键注册前剔除）。
    """
    if name in THEMES:
        logger.warning("register_custom 拒绝：name %r 与内置主题重名", name)
        return
    if base not in THEMES:
        logger.warning("register_custom 拒绝：base %r 非内置主题", base)
        return
    CUSTOM[name] = {"base": base, "overrides": clean_overrides(overrides)}


def is_hex_color(value: object) -> bool:
    """判断是否为 6 位 hex 颜色（`#RRGGBB`，大小写均可，含 # 前缀）。"""
    return isinstance(value, str) and bool(_HEX_COLOR_RE.fullmatch(value))


def clean_overrides(overrides: dict[str, str]) -> dict[str, str]:
    """清洗 override 覆盖：仅保留锚点白名单内且值为 6 位 hex 的键。

    非 dict 输入 / 非法 hex 值 / 非锚点键均被剔除（防手改坏 settings，
    不 raise）；返回新 dict，不原地改输入。
    """
    if not isinstance(overrides, dict):
        return {}
    return {
        key: value
        for key, value in overrides.items()
        if key in ANCHOR_KEYS and is_hex_color(value)
    }


def _lin(c: float) -> float:
    """sRGB 分量 → 线性光分量（WCAG 反 gamma）。"""
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _relative_luminance(color: str) -> float:
    """sRGB（#RRGGBB）→ WCAG 相对亮度（0~1）。"""
    c = color.lstrip("#")
    r, g, b = (int(c[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    r, g, b = (_lin(x) for x in (r, g, b))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(a: str, b: str) -> float:
    """两色 WCAG 对比度（(L1+0.05)/(L2+0.05)）。"""
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def contrast_hints(palette: dict[str, str]) -> list[str]:
    """计算 3 组文字对的 WCAG 对比度软提示（不硬拒）。

    检查 `BTN_BG` vs `BTN_FG`、`FG_TODAY` vs `BG`、`FG_POS` / `FG_NEG` vs
    `BG`；任一 <4.5:1 返回对应提示。非 6 位 hex 值跳过。返回提示列表
    （空列表 = 全部达标），由调用方决定如何展示。
    """
    hints: list[str] = []
    pairs = (
        ("BTN_BG", "BTN_FG", "按钮文字"),
        ("FG_TODAY", "BG", "今日高亮"),
        ("FG_POS", "BG", "涨色"),
        ("FG_NEG", "BG", "跌色"),
    )
    for fg_key, bg_key, label in pairs:
        fg = palette.get(fg_key, "")
        bg = palette.get(bg_key, "")
        if not is_hex_color(fg) or not is_hex_color(bg):
            continue
        ratio = _contrast_ratio(fg, bg)
        if ratio < 4.5:
            hints.append(f"{label}对比度 {ratio:.2f}:1 低于 4.5:1")
    return hints


def set_theme(name: str) -> None:
    """切换当前主题（内置 THEMES 或已注册的自定义 CUSTOM）。"""
    global _current_theme
    if name in THEMES or name in CUSTOM:
        _current_theme = name


def get_color(key: str) -> str:
    """获取当前主题下指定颜色值。

    未知键：记录 warning（含键名）后返回 ""（不 raise，防御语义保持）
    ——让「漏改键 → 静默失效」变成「漏改键 → 日志可见」（C1-06）。
    """
    palette = resolve_palette(_current_theme)
    value = palette.get(key, "")
    if value == "" and key not in palette:
        logger.warning("get_color 未知主题键: %r", key)
    return value



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
    """KPI 磁贴数字样式：数据不足/仅 1 条 → 灰字小号；否则 → 信号色大字号。

    磁贴化后汇总数字是页面核心读数（U-01）：正常态 22px 加粗信号色，
    数据不足态降为 16px 灰字。
    """
    if signal is RateSignal.NONE:
        return f"color: {get_color('FG_MUTED')}; font-size: 16px; font-weight: bold;"
    return f"color: {signal_color(signal)}; font-size: 22px; font-weight: 700;"


def generate_qss(theme_name: str) -> str:
    """根据主题名称生成完整 QSS 样式表。"""
    t = resolve_palette(theme_name)

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
    border_heavy = t["BORDER_HEAVY"]
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
/* U-02 排版刻度（全 app 统一）：
   - display 18-22px：应用名 18 / KPI 磁贴数字 22（内联样式）
   - section 15-16px：页面标题 16 / 卡片主角名 15-16
   - body 12-13px：正文 / 表格 / 常规控件
   - meta 10-11px：提示 / 状态 / 按钮次级
   按钮仅两级：primary 13px/600（saveBtn/queryBtn）、secondary 11px/500（其余） */
QWidget {{
    font-family: "Microsoft YaHei";
}}
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
QLabel#pageTitleLabel {{
    color: {table_text_bold};
    font-size: 16px;
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
    color: {t["WARNING_FG"]};
    background-color: {t["WARNING_BG"]};
    border: 1px solid {t["BORDER_WARNING"]};
    border-radius: 9px;
    padding: 2px 10px;
    font-size: 10px;
    font-weight: 600;
}}

/* ═══════════════════════════════════════════
   滚动区（利润页）
   ═══════════════════════════════════════════ */
/* U 系列修复：全局 QWidget 字体族规则使所有未显式设背景的 QWidget
   落入 palette.window 背景（不随主题）——用户系统深色 palette 时
   亮色主题下利润页背景纯黑、与亮色卡片违和。profitPage/container
   显式主题 BG；viewport 的透明由 profit_page.py 内联样式处理
   （QSS 选择器匹配不到 viewport）。 */
QWidget#profitPage, QWidget#profitContainer {{
    background-color: {bg};
}}
QLabel#summaryLabel, QLabel#cashSummaryLabel {{
    font-weight: 600;
}}
QLabel#summaryCaption, QLabel#cashSummaryCaption {{
    color: {fg_muted};
    font-size: 11px;
}}
QLabel#statusLabel {{
    color: {fg_label};
    font-size: 12px;
    padding: 8px;
}}
QLabel#craftStation {{
    color: {fg_muted};
    font-size: 11px;
    font-weight: 500;
}}
QLabel#schemeSummary {{
    font-size: 13px;
    font-weight: 600;
    color: {table_text_bold};
}}
QLabel#tierLabel {{
    font-size: 15px;
    font-weight: 600;
    color: {fg_today};
    padding: 4px 0;
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
    selection-background-color: {t["SELECTION_BG"]};
    selection-color: {t["SELECTION_FG"]};
}}
QLineEdit:focus {{
    border: 2px solid {t["FOCUS_RING"]};
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
    font-size: 11px;
    font-weight: 500;
}}
QPushButton:focus {{
    outline: 2px solid {t["FOCUS_RING"]};
    outline-offset: 1px;
}}
/* W-03：全局按下 1px 下沉反馈（saveBtn/refreshBtn/queryBtn 有各自的
   pressed padding 覆盖，此处补齐其余按钮的按压缩放一致性） */
QPushButton:pressed {{
    padding-top: 7px;
    padding-bottom: 5px;
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
QPushButton#reuseBtn[state="danger"] {{
    background-color: {t["DANGER_BG"]};
    color: {t["DANGER_FG"]};
    border: 1px solid {t["DANGER_BORDER"]};
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 11px;
    font-weight: bold;
}}
QPushButton#reuseBtn[state="danger"]:hover {{
    background-color: {t["DANGER_HOVER_BG"]};
    color: {t["BTN_HOVER_FG"]};
}}
QPushButton#themeBtn, QPushButton#pinBtn, QPushButton#exportBtn {{
    background-color: {muted_bg};
    color: {fg_muted};
    padding: 6px 14px;
    font-size: 11px;
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
   侧边栏账号区（Y-04）
   ═══════════════════════════════════════════ */
QLabel#accountAreaTitle {{
    color: {fg_muted};
    font-size: 10px;
    font-weight: 600;
}}
QComboBox#accountCombo {{
    background-color: {muted_bg};
    color: {fg_label};
    border: 1px solid {border_def};
    border-radius: 8px;
    padding: 3px 8px;
    font-size: 11px;
}}
QComboBox#accountCombo:hover {{
    border-color: {border_heavy};
}}
QComboBox#accountCombo QAbstractItemView {{
    background-color: {card_bg};
    color: {fg_label};
    border: 1px solid {border_def};
    border-radius: 8px;
    selection-background-color: {t["SELECTION_BG"]};
    selection-color: {t["SELECTION_FG"]};
    outline: none;
}}
QPushButton#newAccountBtn {{
    background-color: {muted_bg};
    color: {fg_label};
    padding: 5px 12px;
    font-size: 11px;
    border-radius: 8px;
}}
QPushButton#newAccountBtn:hover {{
    background-color: {separator};
}}

QPushButton#refreshBtn {{
    background-color: {muted_bg};
    color: {fg_label};
    padding: 6px 18px;
    font-size: 11px;
    border-radius: 8px;
}}
QPushButton#refreshBtn:hover {{
    background-color: {separator};
    color: {table_text_bold};
}}
QPushButton#refreshBtn:pressed {{
    background-color: {btn_hover};
    color: {btn_fg};
    padding: 7px 18px 5px 18px;
}}
QPushButton#refreshBtn:disabled {{
    background-color: {muted_bg};
    color: {fg_muted};
}}

/* ═══════════════════════════════════════════
   兑换利润页面卡片
   ═══════════════════════════════════════════ */
QFrame#exchangeCard {{
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
}}
QLabel#exchangeItemName {{
    color: {table_text_bold};
    font-size: 15px;
    font-weight: bold;
}}
QLabel#exchangeProfit {{
    color: {fg_pos};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#exchangePrice {{
    color: {fg_label};
    font-size: 11px;
}}
QLabel#exchangeTotal {{
    color: {fg_label};
    font-size: 11px;
}}
QLabel#exchangePackageLabel {{
    font-size: 15px;
    font-weight: 700;
}}
QLabel#exchangeGradeAndCount {{
    color: {fg_muted};
    font-size: 11px;
}}

QPushButton#queryBtn {{
    background-color: {btn_bg};
    color: {btn_fg};
    padding: 8px 24px;
    font-size: 13px;
    font-weight: 600;
    border-radius: 8px;
}}
QPushButton#queryBtn:hover {{
    background-color: {btn_hover};
}}
QPushButton#queryBtn:pressed {{
    background-color: {btn_hover};
    padding: 9px 24px 7px 24px;
}}
QPushButton#queryBtn:disabled {{
    background-color: {muted_bg};
    color: {fg_muted};
}}

/* ═══════════════════════════════════════════
   密码门页面卡片（BD-02）
   ═══════════════════════════════════════════ */
QFrame#bonusDoorCard {{
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
}}
QLabel#bonusDoorMap {{
    color: {fg_muted};
    font-size: 13px;
}}
QLabel#bonusDoorPassword {{
    color: {t["TEXT_PRIMARY"]};
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
    padding: 2px 8px;
    border-bottom: 1px solid {separator};
}}
QTableWidget::item:hover {{
    background-color: {t.get("TABLE_ROW_HOVER_BG", muted_bg)};
}}
QTableWidget::item:selected {{
    background-color: {t["SELECTION_BG"]};
    color: {t["SELECTION_FG"]};
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
QFrame#cardFrame, QFrame#craftingCard {{
    background-color: {card_bg};
    border: 1px solid {card_border};
    border-radius: 12px;
}}

/* ═══════════════════════════════════════════
   ScrollBar
   ═══════════════════════════════════════════ */
QScrollBar:vertical {{
    background: {t["SCROLLBAR_BG"]};
    width: 4px;
    border-radius: 2px;
}}
QScrollBar::handle:vertical {{
    background: {t["SCROLLBAR_HANDLE"]};
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
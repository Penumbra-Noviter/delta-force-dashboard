"""
格式化与输入清洗工具（金额、日期短格式）。
"""

from __future__ import annotations

__all__ = [
    "format_compact",
    "format_money",
    "format_short_date",
    "parse_money_input",
    "is_valid_money_input",
    "format_input_value",
    "unformat_input_value",
]


# 财务单位因子（K/M/B）——解析与格式化共用，避免各处硬编码漂移
_K = 1_000
_M = 1_000_000
_B = 1_000_000_000

# 后缀→因子升序表（K/M/B）：parse_money_input 正向迭代匹配后缀，
# format_compact 反向迭代（大单位优先）；新增单位只需改这一处
_UNITS = (("K", _K), ("M", _M), ("B", _B))


def format_compact(value: float, *, prefix: str = "") -> str:
    """把数值格式化为紧凑的 K/M/B 财务单位（SI 阈值）。

    与 format_money 的表格展示约定不同：此处 K ≥ 1e3、M ≥ 1e6、B ≥ 1e9，
    低于 1e3 显示为整数。图表 Y 轴刻度（prefix=""）与 hover/端点标注
    （prefix="¥"）共用此实现，保证两处阈值与精度不再各自漂移。

    示例：
        format_compact(1_500)                     → "1.5K"
        format_compact(460_900_000)               → "460.9M"
        format_compact(88_541_000, prefix="¥")    → "¥88.5M"
    """
    for unit, factor in reversed(_UNITS):
        if value >= factor:
            return f"{prefix}{value / factor:.1f}{unit}"
    return f"{prefix}{value:.0f}"


def format_short_date(date_str: str) -> str:
    """把完整日期 "YYYY-MM-DD" 截取为短格式 "MM-DD"（表格/图表标题展示用）。"""
    return date_str[-5:]


def format_money(value: float | None) -> str:
    """把数字格式化为易读形式。

    - None → "—"
    - < 1,000,000 → ¥x,xxx.xx
    - ≥ 1,000,000 → ¥x,xxx.xK
    - ≥ 100,000,000 → ¥x,xxx.xM

    与 `format_compact` 不同，此处 K 阈值为 1,000,000 而非 1,000。
    """
    if value is None:
        return "—"

    sign = "-" if value < 0 else ""
    abs_v = abs(value)

    if abs_v >= 100 * _M:
        return f"¥{sign}{abs_v / _M:,.1f}M"
    if abs_v >= _M:
        return f"¥{sign}{abs_v / _K:,.1f}K"
    return f"¥{sign}{abs_v:,.2f}"


def parse_money_input(text: str) -> float | None:
    """
    把用户输入清洗为浮点数。
    支持：首尾空格、千分位逗号、人民币/美元符号、空值、K/M/B 单位后缀。
    空值/纯空白返回 None；无法解析则抛出 ValueError。

    单位后缀（大小写不敏感）：
      K → ×1,000
      M → ×1,000,000
      B → ×1,000,000,000
    """
    text = _strip_invisible(text).strip()

    multiplier = 1
    upper = text.upper()
    for suffix, factor in _UNITS:
        if upper.endswith(suffix):
            multiplier = factor
            text = text[:-1].strip()
            break

    cleaned = _normalize_numeric_string(text)
    if cleaned == "":
        return None
    return float(cleaned) * multiplier


def is_valid_money_input(text: str) -> bool:
    """判断输入是否可以解析为金额。

    空字符串视为合法占位（用户尚未输入），非空但无法解析的文本（如 "abc"）视为非法。
    """
    try:
        result = parse_money_input(text)
        return result is not None or text.strip() == ""
    except ValueError:
        return False


def format_input_value(value: float) -> str:
    """输入框失去焦点时显示的金额格式（带货币符号）。"""
    return format_money(value)


def unformat_input_value(text: str) -> str:
    """输入框获得焦点时还原为可编辑的纯数字字符串。"""
    value = parse_money_input(text)
    if value is None:
        return ""
    # f"{value:.2f}" 恒含小数点 → 原三元 else 分支（:.0f）是死代码
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _normalize_numeric_string(text: str) -> str:
    """去除货币符号、逗号、空格以及不可见 Unicode 字符。

    使用 ASCII 数字字面量而非 str.isdigit()，因为后者对 ² ³ ¹
    等上标数字及 ١ 等阿拉伯-印度数字返回 True，而 float() 无法解析它们。
    """
    text = _strip_invisible(text)
    cleaned = "".join(ch for ch in text if ch in "0123456789.-")
    if cleaned.count(".") > 1 or cleaned.count("-") > 1:
        raise ValueError(f"非法数字格式: {text!r}")
    if "-" in cleaned and not cleaned.startswith("-"):
        raise ValueError(f"非法数字格式: {text!r}")
    return cleaned


def _strip_invisible(text: str) -> str:
    """移除 Unicode 不可见字符（零宽空格、BOM、方向标记等）。"""
    import unicodedata

    result: list[str] = []
    for ch in text:
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N", "P", "S", "Z"):
            result.append(ch)
    return "".join(result)

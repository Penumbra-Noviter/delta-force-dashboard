"""
金额格式化与输入清洗工具。
"""

from __future__ import annotations

__all__ = [
    "format_money",
    "parse_money_input",
    "is_valid_money_input",
    "format_input_value",
    "unformat_input_value",
]


def format_money(value: float | None) -> str:
    """把数字格式化为易读形式。

    - None → "—"
    - < 1,000,000 → ¥x,xxx.xx
    - ≥ 1,000,000 → ¥x,xxx.xK
    - ≥ 100,000,000 → ¥x,xxx.xM
    """
    if value is None:
        return "—"

    sign = "-" if value < 0 else ""
    abs_v = abs(value)

    if abs_v >= 100_000_000:
        return f"¥{sign}{abs_v / 1_000_000:,.1f}M"
    if abs_v >= 1_000_000:
        return f"¥{sign}{abs_v / 1_000:,.1f}K"
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
    for suffix, factor in [("K", 1_000), ("M", 1_000_000), ("B", 1_000_000_000)]:
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
    return f"{value:.2f}".rstrip("0").rstrip(".") if "." in f"{value:.2f}" else f"{value:.0f}"


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

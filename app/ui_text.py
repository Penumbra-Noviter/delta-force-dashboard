"""
UI 文案统一字符表（U-05）：全 app emoji 收敛为单一来源，避免散落变体。

emoji 作为装饰图标保留（游戏感方向），但含义与字符必须固定：
新增界面文案需要 emoji 前缀时，先查本表复用；确需新字符再扩展本表。
Windows 下配合 theme.py 全局 font-family 的 "Segoe UI Emoji" 保证基线一致。
"""

from __future__ import annotations

__all__ = ["EMOJI"]

EMOJI: dict[str, str] = {
    "nav_ledger": "📒",   # 侧边栏：记账页
    "nav_profit": "🔧",   # 侧边栏：利润页
    "nav_bonus_door": "🔑",  # 侧边栏：密码门页（BD-03，门/钥匙语义）
    "account": "👤",      # 侧边栏账号区标题（Y-04）
    "new_account": "➕",  # 侧边栏：新建账号按钮（Y-04）
    "theme_dark": "🌙",   # 主题切换：切到暗色
    "theme_light": "☀️",  # 主题切换：切到亮色
    "pin": "📌",          # 窗口置顶
    "loading": "🔄",      # 数据加载中
    "warn": "⚠️",         # 错误/失败提示
    "save": "💾",         # 导出/保存动作
    "ok": "✓",            # 成功提示（business 层 presentation.py 同款，UI 层复用）
}

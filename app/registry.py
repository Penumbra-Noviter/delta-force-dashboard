"""
插件式 Widget 注册系统：让 MainWindow 的 widget 列表可配置。

使用方式：
    from app.registry import WidgetRegistry, AppWidget

    registry = WidgetRegistry()
    registry.register(AppWidget(...))
    win = MainWindow(registry=registry)
"""

from __future__ import annotations

__all__ = ["AppWidget", "WidgetRegistry"]

from dataclasses import dataclass
from typing import Any, Callable, Optional

from PySide6.QtWidgets import QLayout, QWidget


@dataclass
class AppWidget:
    """单个 widget 注册项。

    widget:  QWidget 实例
    setup:   接收 (root_layout, main_window) 的回调，负责将 widget 加入布局
    connect: 可选，接收 main_window 的回调，负责连接信号
    """
    widget: QWidget
    setup: Callable[[QLayout, Any], None]
    connect: Optional[Callable[[Any], None]] = None


class WidgetRegistry:
    """管理 widget 列表，支持注册、批量构建和信号连接。"""

    def __init__(self) -> None:
        self._widgets: list[AppWidget] = []

    def register(self, entry: AppWidget) -> None:
        """注册一个 widget。"""
        self._widgets.append(entry)

    def build_all(self, root_layout: QLayout, main_window: Any) -> None:
        """遍历所有注册的 widget，执行 setup 回调。"""
        for entry in self._widgets:
            entry.setup(root_layout, main_window)

    def connect_all(self, main_window: Any) -> None:
        """遍历所有注册的 widget，执行 connect 回调。"""
        for entry in self._widgets:
            if entry.connect is not None:
                entry.connect(main_window)

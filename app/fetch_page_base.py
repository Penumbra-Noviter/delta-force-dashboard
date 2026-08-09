"""
数据获取页面的公共基类：懒加载、标题栏、加载状态机与后台线程管理。

制造产物（CraftingPage）与兑换利润（ExchangePage）两页共享的
showEvent 懒加载、加载/成功/错误三件套、refresh/preload/shutdown
与 _loaded_once/_loading/_worker/_client 状态机全部收敛于此；
子类只需提供数据获取函数、页面主体构建与数据渲染。
"""

from __future__ import annotations

__all__ = ["FetchPageBase"]

import logging
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QShowEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.fetch_worker import FetchWorker
from kkrb_client import KkrbClient, KkrbError

logger = logging.getLogger(__name__)


class _ClickableLabel(QLabel):
    """可点击标签：错误状态「点击重试」文案真正可点（U-07）。"""

    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class FetchPageBase(QWidget):
    """数据获取页面基类（标题栏 + 状态标签 + 懒加载状态机）。

    子类需实现：
    - ``_title`` / ``_page_name``：页面标题与日志文案前缀
    - ``_fetch()``：返回数据列表的可调用实现（在后台线程执行）
    - ``_build_body(layout)``：在标题栏下方构建页面主体
    - ``_render_data(data)``：将数据渲染到已构建的主体
    """

    #: 标题栏文案（子类覆盖）
    _title = "数据页面"
    #: 日志文案前缀（子类覆盖，如「制造产物」「弹药包」）
    _page_name = "数据页面"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = KkrbClient()
        self._loading = False
        self._loaded_once = False
        self._shut_down = False
        self._worker: FetchWorker | None = None
        self._data: list[Any] = []

        self._build_ui()

    def showEvent(self, event: QShowEvent) -> None:
        """首次显示时自动加载数据。"""
        super().showEvent(event)
        if not self._loaded_once:
            self._loaded_once = True
            self._load_data()

    # ── UI 构建 ─────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 16)
        layout.setSpacing(16)

        # 标题栏
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(self._title)
        title.setObjectName("titleLabel")
        title_layout.addWidget(title)

        title_layout.addStretch()

        self._refresh_btn = QPushButton("🔄 刷新")
        self._refresh_btn.setObjectName("refreshBtn")
        self._refresh_btn.clicked.connect(self._load_data)
        title_layout.addWidget(self._refresh_btn)

        layout.addWidget(title_bar)

        # 状态提示（错误时变为可点击重试）
        self._status_label = _ClickableLabel("")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setVisible(False)
        self._status_label.clicked.connect(self._load_data)
        layout.addWidget(self._status_label)

        # 页面主体（子类构建）
        self._build_body(layout)

        layout.addStretch()

    def _fetch(self) -> list[Any]:
        """后台线程执行的取数函数（子类实现）。"""
        raise NotImplementedError

    def _build_body(self, layout: QVBoxLayout) -> None:
        """在标题栏下方构建页面主体（子类实现）。"""
        raise NotImplementedError

    def _render_data(self, data: list[Any]) -> None:
        """将数据渲染到已构建的主体（子类实现）。"""
        raise NotImplementedError

    # ── 数据加载 ────────────────────────────────────────

    def _load_data(self) -> None:
        if self._loading:
            return
        self._loading = True
        self._status_label.setText("🔄 加载中…")
        self._status_label.setVisible(True)
        self._status_label.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self._refresh_btn.setEnabled(False)

        self._worker = FetchWorker(self._fetch)
        self._worker.done.connect(self._on_fetch_done)
        self._worker.error.connect(self._on_fetch_error)
        self._worker.start()

    def _on_fetch_done(self, data: list[Any]) -> None:
        self._loaded_once = True
        self._data = data
        self._status_label.setVisible(False)
        self._loading = False
        self._refresh_btn.setEnabled(True)
        self._render_data(data)

    def _on_fetch_error(self, e: Exception) -> None:
        if isinstance(e, KkrbError):
            logger.warning("%s数据获取失败: %s", self._page_name, e)
            self._status_label.setText("⚠️ 数据获取失败，点击重试")
        else:
            logger.error("%s数据获取异常: %s", self._page_name, e)
            self._status_label.setText("⚠️ 网络异常，请检查连接后重试")
        # 错误状态：label 可点击重试（U-07，文案与行为一致）
        self._status_label.setVisible(True)
        self._status_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._data = []
        self._loading = False
        self._refresh_btn.setEnabled(True)
        self._render_data([])

    # ── 公开接口 ────────────────────────────────────────

    def refresh(self) -> None:
        """公开刷新方法（供外部调用）。"""
        self._load_data()

    def preload(self) -> None:
        """后台预加载数据（启动时调用，消除首次展示的加载闪烁）。

        幂等：测试（offscreen）模式、已加载、加载中或已关闭均直接返回；
        预加载失败不弹窗，仅记录日志，用户可手动刷新重试。
        """
        import os

        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return
        if self._shut_down or self._loaded_once or self._loading:
            return
        self._load_data()

    def shutdown(self) -> None:
        """关闭时回收后台线程（必须从 GUI 线程调用）。

        请求在途时等待其退出，超时后由 FetchWorker 转入逃生舱托管；
        此后本页不再启动新的预加载（_shut_down 守卫）。
        """
        self._shut_down = True
        if self._worker is not None and self._worker.isRunning():
            self._worker.shutdown()

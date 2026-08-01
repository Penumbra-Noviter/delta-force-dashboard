"""
收益计算器 — PySide6 版入口。

启动 PySide6 QApplication 并打开主窗口。
保证同时只有一个实例在运行。
运行方式：python main.py
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from config import APP_DIR

# 单实例锁名称（全局唯一）
_SERVER_NAME = "profit_calculator_singleton_lock"



def _icon_path() -> str:
    """定位应用图标路径。

    - 打包版（PyInstaller 单文件）：从 `sys._MEIPASS` 解压目录读取
    - 源码版：从项目根目录读取
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return str(base / "app_icon.ico")

def _is_already_running() -> QLocalServer | None:
    """
    尝试连接已有的 LocalServer。

    - 如果连接成功 → 说明已有实例在运行，返回 None
    - 如果连接失败 → 说明没有其他实例，创建新的 Server 并返回
    """
    socket = QLocalSocket()
    socket.connectToServer(_SERVER_NAME)

    # 如果连接成功，说明已有实例在运行
    if socket.waitForConnected(500):
        socket.disconnectFromServer()
        return None

    # 连接失败（没有已有实例），创建新的 Server
    socket.abort()
    server = QLocalServer()
    # 清理可能残留的旧 socket 文件（进程崩溃后可能残留）
    QLocalServer.removeServer(_SERVER_NAME)
    if not server.listen(_SERVER_NAME):
        return None
    return server


def main() -> None:
    # 日志：打包版为窗口化 exe 无 stderr，文件日志是唯一可见通道。
    # O-15：RotatingFileHandler 轮转（单文件 1MB、保留 3 份备份），防单文件无限增长。
    root_logger = logging.getLogger()
    if not root_logger.handlers:  # 已有配置时不重复添加（与 basicConfig 幂等语义一致）
        handler = RotatingFileHandler(
            APP_DIR / "profit_calculator.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO)
    # 高 DPI 支持
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("收益计算器")
    app.setWindowIcon(QIcon(_icon_path()))

    # ── 单实例检查 ──
    server = _is_already_running()
    if server is None:
        # 已有实例在运行，静默退出
        sys.exit(0)

    window = MainWindow()
    window.show()

    exit_code = app.exec()

    # 退出前清理 LocalServer
    server.close()
    QLocalServer.removeServer(_SERVER_NAME)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

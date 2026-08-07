"""
Delta Force Dashboard — PySide6 版入口。

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

from app import MainWindow
from config import (
    DATA_DIR,
    _APP_DIR as APP_DIR,
    _LEGACY_DATA_DIR as LEGACY_DATA_DIR,
    _LOG_FILE as LOG_FILE,
)
from data_store import log_legacy_cleanup_hint, migrate_legacy_data

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
    # O-20：500ms → 100ms。本地 socket 探测毫秒级完成，100ms 足够判定；
    # 无已有实例时免去 500ms 启动白等。
    if socket.waitForConnected(100):
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
    # 统一数据目录（O-22）必须先行创建：日志 handler、迁移、数据/设置写入
    # 都落在 DATA_DIR 下，目录不存在时 RotatingFileHandler 打开日志文件即抛
    # FileNotFoundError。空启动（无旧数据、无用户目录）也需保证目录存在。
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 日志：打包版为窗口化 exe 无 stderr，文件日志是唯一可见通道。
    # O-15：RotatingFileHandler 轮转（单文件 1MB、保留 3 份备份），防单文件无限增长。
    root_logger = logging.getLogger()
    if not root_logger.handlers:  # 已有配置时不重复添加（与 basicConfig 幂等语义一致）
        handler = RotatingFileHandler(
            LOG_FILE,
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
    app.setApplicationName("Delta Force Dashboard")
    app.setWindowIcon(QIcon(_icon_path()))

    # ── 单实例检查 ──
    server = _is_already_running()
    if server is None:
        # 已有实例在运行，静默退出
        sys.exit(0)

    # ── 旧数据一次性迁移（O-22 / 更名）：运行态数据统一到 ~/Delta Force Dashboard ──
    # 目标目录已有数据则跳过；旧数据保留原位置（复制非移动）。
    # 迁移源：① 更名前数据目录 ~/收益计算器（较新权威，先迁）；
    #         ② 项目根 APP_DIR（远古旧源，后迁）。migrate_legacy_data 对目标已有
    #            data.json 幂等跳过，故权威源必须在前，避免旧数据覆盖新数据。
    migrate_legacy_data(LEGACY_DATA_DIR, DATA_DIR)
    migrate_legacy_data(APP_DIR, DATA_DIR)
    # 迁移完成后提示旧数据源可手动清理（F-02）：仅打日志，删除须用户手动确认。
    log_legacy_cleanup_hint(LEGACY_DATA_DIR, DATA_DIR)
    log_legacy_cleanup_hint(APP_DIR, DATA_DIR)

    window = MainWindow()
    window.show()

    exit_code = app.exec()

    # 退出前清理 LocalServer
    server.close()
    QLocalServer.removeServer(_SERVER_NAME)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

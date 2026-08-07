# -*- mode: python ; coding: utf-8 -*-

# =============================================================================
# O-20（2026-08-01）打包方案重构：onefile → onedir + 体积瘦身
#
# A. onefile → onedir：
#    单文件模式每次启动要把整包解压到 %TEMP%\_MEI*（实测 181MB），是启动
#    慢（2~4s）的根因。onedir 免解压，启动约 0.7s。交付形态变为
#    dist/Delta Force Dashboard/（exe + _internal/），可整目录分发或 zip 压缩。
#    运行路径逻辑（config.APP_DIR 的 sys.executable、main._icon_path 的
#    sys._MEIPASS）在 onedir 下行为与 onefile 一致，无需改源码。
#
# B. 体积瘦身（80MB → 预计 ~45MB）：
#    1. excludes 剔除纯 Python 死重：matplotlib/PIL 及其依赖（pyqtgraph 的
#       Matplotlib 导出器仅在 try/except 中 import，运行时从不加载——实测
#       import pyqtgraph 后 matplotlib 不在 sys.modules）。
#    2. Qt 模块白名单过滤：PyInstaller 的 Qt hooks 会收集 PySide6 整包
#       （含全部 Qt6*.dll 与绑定 .pyd）。用 bindepend 实测各保留 DLL/.pyd 的
#       link-time 依赖闭包，确认剔除项无人引用后，白名单过滤只保留：
#         Core/Gui/Widgets/Network（应用实际使用）
#         OpenGL/OpenGLWidgets/Svg/Test（pyqtgraph import 时实际加载）
#    3. 剔除全部 Qt translations（*.qm，约 6.6MB）：应用不安装 QTranslator，
#       界面文案硬编码中文，翻译文件是纯死重。
#    4. 剔除软件 OpenGL 渲染器 opengl32sw.dll（约 20MB）：应用从不创建
#       GL 上下文（pyqtgraph PlotWidget 为 QPainter 光栅渲染），永不加载。
#    5. 剔除未使用插件：tls（无 SSL）、networkinformation（无网络状态查询）。
#
# upx=True：UPX 5.2.0 已安装（D:/Desktop/tools/UPX/upx.exe），onedir 内 exe/DLL 经 UPX 压缩瘦身。
# 若换机器未装 UPX，PyInstaller 会回退为不压缩，不影响产物正确性。
# =============================================================================

# 保留的 Qt 二进制（DLL）：运行所需 + link-time 依赖闭包
_QT_KEEP_BINARIES = {
    "Qt6Core.dll",
    "Qt6Gui.dll",
    "Qt6Widgets.dll",
    "Qt6Network.dll",
    "Qt6OpenGL.dll",
    "Qt6OpenGLWidgets.dll",
    "Qt6Svg.dll",
    "Qt6Test.dll",
    # shiboken 绑定层（PySide6 全部模块依赖）
    "shiboken6.abi3.dll",
}

# 保留的 Qt 绑定扩展（.pyd）：与应用 / pyqtgraph 实际 import 的模块一一对应
_QT_KEEP_PYD = {
    "QtCore.pyd",
    "QtGui.pyd",
    "QtWidgets.pyd",
    "QtNetwork.pyd",
    "QtOpenGL.pyd",
    "QtOpenGLWidgets.pyd",
    "QtSvg.pyd",
    "QtTest.pyd",
}

# 剔除的 Qt 插件目录（仅按插件功能判定，与平台无关）：
#   tls  —— QtNetwork TLS 后端；单实例锁走 QLocalSocket，不用 SSL
#   networkinformation —— 网络状态后端；应用不查询网络状态
_DROP_PLUGIN_DIRS = {"tls", "networkinformation"}


def _keep_qt_binary(dest: str) -> bool:
    """白名单过滤 PySide6 包内的 Qt 二进制；其余（插件、系统 DLL）按需放行。"""
    path = dest.replace("\\", "/")
    name = path.rsplit("/", 1)[-1]

    # 软件 OpenGL 渲染器（约 20MB）：应用从不创建 GL 上下文
    # （pyqtgraph PlotWidget 用 QPainter 光栅渲染），该 DLL 永不加载
    if name == "opengl32sw.dll":
        return False

    # Qt 插件：剔除未使用的插件目录
    if "/plugins/" in path:
        return path.split("/plugins/", 1)[1].split("/", 1)[0] not in _DROP_PLUGIN_DIRS

    if name.startswith("Qt6") and name.endswith(".dll"):
        return name in _QT_KEEP_BINARIES
    if name.startswith("Qt") and name.endswith(".pyd"):
        return name in _QT_KEEP_PYD
    return True


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app_icon.ico', '.')],
    hiddenimports=[
        'PySide6.QtNetwork',      # QLocalServer / QLocalSocket（单实例锁）
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 纯 Python 死重（pyqtgraph 静态引用但不加载，见文件头注释）
        'matplotlib', 'PIL', 'pyparsing', 'dateutil',
        'cycler', 'contourpy', 'kiwisolver', 'fonttools', 'six',
        'pandas', 'scipy',
    ],
    noarchive=False,
    optimize=1,
)

# B：剔除未使用的 Qt DLL 与绑定模块
a.binaries = [
    entry for entry in a.binaries if _keep_qt_binary(entry[0])
]

# B：剔除全部 Qt translations（*.qm）
a.datas = [
    (dest, src, typ)
    for dest, src, typ in a.datas
    if 'translations' not in dest.replace('\\', '/')
]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Delta Force Dashboard',
    icon='app_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Delta Force Dashboard',
)

# 收益计算器 (Profit Calculator) — Code Wiki

> 版本：PySide6 版（三阶段 + Phase 4 + C 系列 + O 系列全部完成）  
> 生成日期：2026-07-29  
> 测试状态：204 项 pytest 全部通过（含 UI 烟测，C5 迁移后 verify_all.py 已删除）

---

## 一、项目概述

**收益计算器**是一款 Windows 桌面工具，面向个人投资者。用户每天记录「当前现金」和「仓库价值（含现金）」两个数字，工具自动保留最近 7 条实际录入记录（间断录入不丢历史），以表格展示每日盈亏变化，并以双曲线图可视化趋势。

| 属性 | 说明 |
|------|------|
| 语言 | Python 3.10+ |
| UI 框架 | PySide6（Qt 官方绑定，LGPL 协议） |
| 图表库 | pyqtgraph（原生 Qt 渲染，高性能） |
| 数据存储 | 本地 JSON 文件（原子写入 + 滚动备份） |
| 打包方式 | PyInstaller → onedir 目录（`dist/收益计算器/`，O-20 起） |
| 测试框架 | pytest（204 项） |
| 开发阶段 | 三阶段 + Phase 4（T-01~T-05）+ C 系列（C1~C9）+ O 系列（O-01~O-22，O-07 YAGNI 关闭）全部完成 |

---

## 二、项目架构总览

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                     UI 层 (app/)                         │
│  ┌───────────────┐ ┌──────────────┐ ┌────────────────┐  │
│  │  MainWindow   │ │  InputPanel  │ │   TableWidget  │  │
│  │ (QMainWindow) │ │  (QWidget)   │ │   (QWidget)    │  │
│  └───────┬───────┘ └──────┬───────┘ └───────┬────────┘  │
│          │                │                  │           │
│  ┌───────┴────────────────┴──────────────────┴────────┐  │
│  │                  ChartWidget (pyqtgraph)           │  │
│  │             双曲线图 + PNG 导出                     │  │
│  └────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                   业务逻辑层                              │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ ProfitCalculator │  │  formatting.py                │ │
│  │ Logic + DayRecord│  │  金额格式化 / 输入解析 / 校验  │ │
│  └──────────────────┘  └──────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                    数据持久化层                           │
│  ┌──────────────────────────────────────────────────────┐│
│  │  DataStore — JSON 原子写入 + 滚动备份 + 损坏恢复      ││
│  └──────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────┤
│                    配置 / 主题层                          │
│  ┌──────────────┐  ┌───────────────────────────────────┐ │
│  │  config.py   │  │ app/theme.py — 主题色板 + QSS    │ │
│  │  路径/日期/  │  │ THEMES/get_color 定义于此（T-02） │ │
│  │  保留条数    │  │                                    │ │
│  └──────────────┘  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入 → MoneyLineEdit (实时校验/去抖)
    → InputPanel (合法性校验 → 启用保存按钮)
    → MainWindow.save_today() (解析 → 验证 → 保存)
    → ProfitCalculatorLogic.save_record() (写入内存 dict)
    → ProfitCalculatorLogic.rotate_weekly() (保留最近 7 条实际录入记录，超出删除最旧)
    → DataStore.save() (原子写入 JSON + 滚动备份)
    → refresh_display() → TableWidget.draw() + ChartWidget.draw()
```

---

## 三、文件结构

```
Profit Calculator/
├── main.py                  ← [主入口] PySide6 QApplication + 单实例保证 + 应用图标
├── app/
│   ├── __init__.py          ← app 包标记
│   ├── main_window.py       ← [UI 骨架] QMainWindow，组件协调与数据流
│   ├── input_panel.py       ← 输入面板：MoneyLineEdit + 校验 + 编辑模式
│   ├── table_widget.py      ← 双栏最近 7 条数据表格（7 列）
│   ├── chart_widget.py      ← pyqtgraph 双曲线图 + PNG 导出 + 稀疏数据提示
│   └── theme.py             ← QSS 样式表生成（从 config.py 复用 THEMES 色板）
├── calculator.py            ← [业务逻辑] DayRecord 数据类 + ProfitCalculatorLogic
├── config.py                ← [基础配置] 路径、日期格式、字体、THEMES 色板
├── data_store.py            ← [持久化] DataStore — JSON 原子写入 + 滚动备份
├── json_file.py             ← [持久化 seam] JSON 原子写 + 容错读（D-02）
├── settings_store.py        ← [持久化] SettingsStore — 设置容错读 + 原子写（D-02）
├── formatting.py            ← [工具] 金额格式化、输入解析、校验
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py   ← 65 个测试（DayRecord + 业务逻辑 + CSV 导出 + 带符号金额 D-01 + serialize/加载时过滤 D-03）
│   ├── test_data_store.py   ← 18 个测试（保存/加载/备份/恢复/日志）
│   ├── test_formatting.py   ← 58 个测试（格式化/解析/校验）
│   ├── test_input_panel.py  ← 18 个测试（C4 seam + C9 静态守卫 + O-02 seam + O-08 不变式）
│   ├── test_table_theme.py  ← 4 个测试（C1 主题色实时解析 + D-01 零差值）
│   ├── test_settings_store.py ← 15 个测试（D-02 json_file seam + SettingsStore 容错）
│   ├── test_migration.py    ← 7 个测试（O-22 数据目录迁移 + mkdir 顺序回归）
│   └── test_ui_smoke.py     ← 23 个测试（C5 UI 烟测 + O-04/05/06/08/09/13/14，offscreen）
├── app_icon.ico             ← 应用图标（exe 文件 + 运行窗口，PyInstaller datas 内嵌）
├── 收益计算器.spec           ← PyInstaller 打包配置（onedir + 图标，O-20 瘦身）
├── data.json                ← 运行态数据（日期 → {cash, warehouse}，已 gitignore）
├── settings.json            ← 窗口几何 + 置顶 + 主题持久化
├── requirements.txt         ← PySide6==6.11.1, pyqtgraph==0.14.0（O-12 版本锁定）
├── requirements-dev.txt     ← -r requirements.txt + pytest==9.1.1
├── .gitignore
├── CONSENSUS.md             ← 开发共识文档（三阶段任务记录）
└── PROJECT_REFERENCE.md     ← 项目介绍书（架构说明）
```

---

## 四、核心模块详细说明

### 4.1 `main.py` — 程序入口（~92 行）

**职责**：启动 PySide6 应用，单实例保证，应用图标，事件循环管理。

| 元素 | 说明 |
|------|------|
| `_SERVER_NAME` | 单实例锁名称 `"profit_calculator_singleton_lock"` |
| `_is_already_running()` | 通过 QLocalServer 检测是否已有实例运行 |
| `main()` | 高 DPI 设置 → 创建 QApplication → 单实例检查 → 创建 MainWindow → 事件循环 → 清理 |

**单实例机制**：使用 QLocalServer（Qt 原生方案），崩溃后自动清理残留 socket 文件。若已有实例运行则静默 `sys.exit(0)`。

---

### 4.2 `app/main_window.py` — 主窗口（~456 行）

**核心类**：`MainWindow(QMainWindow)`

**职责**：管理整个应用的生命周期，协调所有子组件，处理数据流。

#### 关键方法

| 方法 | 说明 |
|------|------|
| `__init__()` | 加载 DataStore → 加载数据 → 初始化逻辑 → 恢复设置 → 构建 UI → 连接信号 → 应用 QSS |
| `_setup_window()` | 窗口标题、最小尺寸（680×700）、几何恢复（兼容 Tkinter 旧格式）、DPI 感知 |
| `_build_ui()` | 构建标题栏（含今日未录入提醒、主题/置顶/导出 CSV 按钮）、日期、输入面板卡片、表格卡片、图表卡片、底部提示栏 |
| `_connect_signals()` | 连接信号槽（Enter→保存, Esc→清空, 编辑/删除请求, 导出按钮→_export_csv） |
| `save_today()` | 解析输入 → 验证 → 保存到 logic → 轮转保留最近 7 条 → 持久化 → 刷新显示 |
| `refresh_display()` | 获取 records → 刷新汇总/今日未录入/表格/图表 |
| `_export_csv()` | QFileDialog 选路径，utf-8-sig 写入 `logic.export_csv()`（O-04） |
| `_update_today_status()` | 今日无记录时显示「今日未录入」，有则隐藏（O-05） |
| `_start_edit(date_str, record)` | 进入编辑模式，回填数据到输入面板 |
| `_cancel_edit()` | 退出编辑模式，清空输入框 |
| `_delete_record(date_str)` | 确认对话框 → 删除数据 → 持久化 → 刷新 |
| `_toggle_theme()` | 切换亮/暗主题，增量更新 QSS + 图表颜色 |
| `_toggle_pin()` | 切换窗口置顶状态 |
| `_save_settings()` | 编码窗口状态（geometry/theme/pinned）→ 委托 `settings_store.save()`（D-02） |

#### 信号连接

| 信号源 | 信号 | 槽 |
|--------|------|-----|
| `InputPanel` | `save_requested` | `MainWindow.save_today()` |
| `InputPanel` | `cancel_requested` | `MainWindow._cancel_edit()` |
| `TableWidget` | `edit_requested` | `MainWindow._start_edit()` |
| `TableWidget` | `delete_requested` | `MainWindow._delete_record()` |
| QAction (Enter) | `triggered` | `MainWindow.save_today()` |
| QAction (Esc) | `triggered` | `MainWindow._clear_focused_input()` |

---

### 4.3 `app/input_panel.py` — 输入面板（~294 行）

#### 类：`MoneyLineEdit(QLineEdit)`

自定义金额输入框，继承自 QLineEdit。

| 方法 | 说明 |
|------|------|
| `__init__()` | 设置占位文本、右对齐、150ms 去抖 QTimer |
| `_on_text_changed(text)` | 文本变化时重启去抖计时器 |
| `_update_validity()` | 校验当前输入：空 → normal / 合法 → valid / 非法 → invalid |
| `refresh_validity()` | 立即同步重校验当前文本（公开 seam，委托 `_update_validity()`，O-02） |
| `_set_validity_state(state)` | 设置 `validity` 属性，触发 QSS 重绘边框 |
| `focusInEvent()` | 聚焦时反格式化：`¥1,234.56` → `1234.56`，全选 |
| `focusOutEvent()` | 失焦时格式化：`1234.56` → `¥1,234.56` |

**信号**：`validity_changed(bool)`

#### 类：`InputPanel(QWidget)`

| 方法 | 说明 |
|------|------|
| `_build()` | 构建现金/仓库输入行 + 保存按钮 + 取消编辑按钮 + 指示器 |
| `_update_save_btn_state()` | 两个输入框都合法且非空时启用保存按钮 |
| `set_edit_mode(date_str, cash, warehouse)` | 切换编辑模式，填充数据，改变按钮样式（橙色） |
| `cancel_edit()` | 退出编辑模式，恢复默认状态 |
| `is_editing()` / `get_editing_date()` | 编辑状态查询（**单方归属 InputPanel**，C4） |
| `get_cash_value()` / `get_warehouse_value()` | 解析当前输入返回金额；空→`None`，非法→`ValueError`（C4 seam） |
| `get_cash_raw()` / `get_warehouse_raw()` | 返回输入框原始文本（供解析失败提示） |
| `refresh_validity()` | 立即重新校验两个输入框的有效性（经公开 seam，O-02） |
| `fill_values(cash, warehouse)` | 填入金额并选中现金框（不触发焦点格式化） |
| `clear_fields()` | 清空输入框，保留已保存指示器 |
| `set_saved_indicator(text)` | 设置保存成功提示文本 |
| `focus_cash()` | 聚焦现金输入框 |
| `apply_theme()` | 更新标签颜色 |

---

### 4.4 `app/table_widget.py` — 数据表格（~332 行）

#### 类：`PnLBadge(QWidget)`

盈亏标签 Badge 组件。

| 参数 | 说明 |
|------|------|
| `label` | "盈" / "亏" / "—" |
| `bg_color` | 绿色 / 红色 / 灰色 |
| `fg_color` | 文字颜色（默认白色） |

#### 类：`_DaySubTable(QTableWidget)`

双栏布局中的单栏表格（7 列）。

| 方法 | 说明 |
|------|------|
| `draw(records, today, prev_warehouse)` | 逐行绘制：日期、现金、仓库、较前日差值、收益率、盈亏标签、操作按钮 |
| `_create_action_buttons(date_str, record)` | 创建"编辑"+"删除"按钮，带 hover 样式 |

**7 列定义**：

| 列索引 | 列名 | 宽度 | 说明 |
|--------|------|------|------|
| 0 | 日期 | 80 | 显示 `MM-DD`，今日加蓝色"今天"后缀 |
| 1 | 现金 | 100 | 格式化金额，右对齐 |
| 2 | 仓库（总收益） | 110 | 格式化金额，粗体，右对齐 |
| 3 | 较前日 | 100 | 差值，红涨绿跌，零值显示"¥0.00"（无 + 前缀），无前日数据显示"—" |
| 4 | 收益率 | 80 | 1 位小数百分比，红涨绿跌 |
| 5 | 盈亏 | 55 | PnLBadge 组件 |
| 6 | 操作 | 120 | 编辑 + 删除按钮 |

#### 类：`TableWidget(QWidget)`

双栏布局容器：左栏前 4 天 + 右栏后 3 天。

| 方法 | 说明 |
|------|------|
| `draw(records, today)` | 拆分 records 为左右两栏，传递跨栏的 prev_warehouse 给右栏 |

---

### 4.5 `app/chart_widget.py` — 图表组件（~413 行）

#### 类：`KMBAxisItem(pg.AxisItem)`

自定义 Y 轴刻度标签，将数值显示为 K/M/B 财务单位。

#### 类：`ChartWidget(QWidget)`

pyqtgraph 双曲线图组件。

| 方法 | 说明 |
|------|------|
| `draw(records)` | n≥2 时渲染图表，n<2 时显示占位提示文字；2≤n≤3 时叠加半透明「数据较少」提示 |
| `_create_chart(records)` | 从零创建上下双图 PlotWidget（仓库价值 + 现金） |
| `_update_chart(records)` | 原地更新曲线数据（不重建 PlotWidget / FillBetweenItem） |
| `_set_adaptive_ylim(plot_widget, values)` | 自适应 Y 轴范围（底部留 10%，顶部留 8%） |
| `_setup_context_menu()` | 绑定右键菜单（导出 PNG） |
| `export_png()` | 导出当前图表为 PNG 文件 |
| `_clear_all()` | 销毁图表及占位组件 |
| `apply_theme()` | 主题切换时增量更新颜色，不重建图表 |
| `_update_theme_colors()` | 更新曲线/填充/背景/轴颜色 |

**图表结构**：

```
┌─────────────────────────────────┐
│  上图：仓库价值（总收益）        │
│  琥珀色实线 + 方块标记 + 填充    │
│  Y 轴：K/M/B 单位               │
├─────────────────────────────────┤
│  下图：现金（子项）              │
│  蓝色虚线 + 圆点标记 + 填充      │
│  Y 轴：K/M/B 单位               │
│  X 轴：日期标签（MM-DD）         │
└─────────────────────────────────┘
```

**性能优化**：使用持久化的 `PlotCurveItem` + `FillBetweenItem`，更新时仅调用 `setData()`，避免重建。填充边界曲线 `_fill_curve_top` / `_fill_curve_bottom` 也持久化，消除了 Phase 3 之前的 FillBetweenItem 重建开销。

---

### 4.6 `app/theme.py` — 主题系统（~371 行）

主题数据的单一真实来源：内联定义 `THEMES` 色板字典与 `get_color`/`get_theme`/`set_theme`（T-02 迁入，不再从 config.py 导入），并生成 QSS 样式表，专供 `app/` 内的 PySide6 组件使用。

| 函数 | 说明 |
|------|------|
| `generate_qss(theme_name)` | 根据主题名生成完整 QSS 样式表（全局/标签/输入框/按钮/表格/卡片/滚动条/提示框） |

**QSS 覆盖范围**：QMainWindow, QLabel, QLineEdit, QPushButton, QTableWidget, QHeaderView, QFrame, QStatusBar, QScrollBar, QToolTip。

---

### 4.7 `calculator.py` — 业务逻辑（~140 行）

#### 类：`DayRecord` (frozen dataclass)

| 属性 | 类型 | 说明 |
|------|------|------|
| `cash` | float | 当前现金 |
| `warehouse` | float | 仓库价值（含现金） |
| `date` | str | 日期 YYYY-MM-DD |
| `total` | property → float | 总收益 = warehouse（现金是仓库的组成部分） |

#### 类：`ProfitCalculatorLogic`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `__init__` | `data: dict` | — | 解析并持有 `dict[str, DayRecord]`（兼容裸 dict / 已解析 dict；加载时跳过损坏条目，ADR-0001） |
| `get_record` | `date_str: str` | `DayRecord \| None` | 一行查询；不存在返回 None（非法条目已由加载时解析过滤） |
| `save_record` | `date_str, cash, warehouse` | `DayRecord` | 保存某日记录（内部存 DayRecord 实例） |
| `serialize` | — | `dict` | 转磁盘持久化形态裸 dict（`{日期: {cash, warehouse}}`）；返回**新 dict**，与内部 data 断共享（ADR-0001） |
| `last_record_before` | `date_str, max_days=365` | `(str, DayRecord) \| None` | 向前回溯最近有效记录（跳过空/无效日） |
| `recent_records` | `days=7` | `list[(str, DayRecord)]` | 最近 days 条实际录入记录（录入条数语义，无空位占位），按日期升序 |
| `calculate_rate` | `prev_warehouse, current_warehouse` | `float \| None` | 计算收益率百分比，前值 None 或为零返回 None |
| `format_rate` | `rate: float \| None` | `(str, str)` | 格式化收益率显示文本和颜色 |
| `format_signed_money` | `value: float \| None` | `(str, str)` | 带符号金额（较前日差值/总盈亏）：正数 `+¥…`、负数 `¥-…`、零 `¥0.00` 无前缀、None `—`（D-01） |
| `get_pnl_label` | `prev_warehouse, current_warehouse` | `(str, str)` | 判断盈亏标签和颜色 |
| `delete_record` | `date_str: str` | `bool` | 删除单日记录，不存在返回 False |
| `rotate_weekly` | `days=7` | `list[str]` | 保留最近 days 条实际录入记录，超过上限删除最旧；返回被删除日期列表（升序，O-14） |
| `summary` | `days=7` | `(int, float \| None)` | 最近 days 条记录总盈亏（最新−最旧，录入条数语义） |
| `export_csv` | — | `str` | 生成 CSV 导出文本（日期/现金/仓库/较前日/收益率，日期升序，O-04） |

**关键业务规则**：
- `data` 为 `dict[str, DayRecord]`（ADR-0001）；磁盘持久化走 `serialize()` 单向导出（返回新 dict，消灭 logic 与磁盘共享别名）；MainWindow 不直接触碰内部 data 形态
- `total` = `warehouse`（非 `warehouse + cash`）
- 收益率 = `(今日warehouse - 前日warehouse) / 前日warehouse × 100%`，精度 1 位小数
- 盈亏标签：盈（绿底）/ 亏（红底）/ —（灰底，无前日数据或持平）
- 较前日差值 / 总盈亏展示统一走 `format_signed_money`：正数 `+¥…`、负数 `¥-…`、零 `¥0.00`（无 + 前缀）、无前值 `—`（D-01）
- CSV「较前日」= 当日仓库值 − 前一有记录日仓库值；无前日数据为 `—`；总收益 = 仓库已含现金

---

### 4.8 `config.py` — 基础配置（~20 行）

| 常量 | 值 | 说明 |
|------|-----|------|
| `APP_DIR` | Path | 应用所在目录（打包版为 exe 目录，源码版为项目根）；O-22 起仅作「旧数据源」供一次性迁移 |
| `DATA_DIR` | `Path.home()/收益计算器` | 统一数据目录（开发版与 exe 共用，O-22） |
| `DATA_FILE` | `DATA_DIR/data.json` | 数据文件路径 |
| `BACKUP_FILE` | `DATA_DIR/data.json.bak` | 备份文件基础路径 |
| `SETTINGS_FILE` | `DATA_DIR/settings.json` | 设置文件路径 |
| `LOG_FILE` | `DATA_DIR/profit_calculator.log` | 日志文件路径 |
| `DATE_FORMAT` | `"%Y-%m-%d"` | 日期格式 |
| `WEEK_DAYS` | `7` | 保留最近记录条数（录入条数语义，非日历天数） |

> 主题色板（`THEMES` / `get_theme` / `set_theme` / `get_color`）已于 T-02 迁至 `app/theme.py`（见 §4.6），config.py 不再包含主题数据。

---

### 4.9 `data_store.py` — 数据持久化（~113 行）

#### 类：`DataStore`

| 方法 | 说明 |
|------|------|
| `__init__(data_file, backup_file, max_backups=3)` | 初始化存储路径和备份数量 |
| `load()` | 加载数据：主文件 → 损坏则依次尝试 bak.1 → bak.2 → bak.3 → bak → 空字典 |
| `save(data)` | 保存数据：滚动备份 → 原子写入 |
| `_try_load(path)` | 安全读取 JSON 文件，损坏返回 None |
| `_atomic_write(data, target)` | 原子写入：先写 `.tmp`，再 `os.replace` 覆盖 |
| `_rotate_backups()` | 滚动备份：bak.2→bak.3, bak.1→bak.2, 当前→bak.1 + bak；复制失败记日志不中断（O-01） |

**关键机制**：
- **原子写入**：`.tmp` → `os.replace`，保证写入过程中进程崩溃不会损坏原文件
- **滚动备份**：最多保留 3 份历史备份（`data.json.bak.1` 为最新）
- **兼容性**：同时保留旧版单文件 `.bak`（与 `.bak.1` 内容相同）
- **损坏恢复**：主文件 JSON 解析失败时自动从最近可用备份恢复，全部损坏则返回空字典
- **日志**：备份复制失败仅记 `logger.warning`，不影响主流程保存（O-01）

---

### 4.10 `formatting.py` — 金额格式化工具（~116 行）

| 函数 | 说明 |
|------|------|
| `format_money(value)` | 格式化显示：None→"—"，<1M→`¥x,xxx.xx`，≥1M→`¥x,xxx.xK`，≥100M→`¥x,xxx.xM` |
| `parse_money_input(text)` | 解析输入：支持 `¥/￥/$`、千分位逗号、`K/M/B` 后缀、负号、空格；空值返回 None；非法格式抛 ValueError |
| `is_valid_money_input(text)` | 校验输入合法性（空字符串为合法占位） |
| `format_input_value(value)` | 输入框失焦时格式化（调用 `format_money`） |
| `unformat_input_value(text)` | 输入框聚焦时反格式化：`¥1,234.56` → `1234.56`，尾零去除 |
| `_normalize_numeric_string(text)` | 去除货币符号、逗号、空格，保留 `0-9`、`.`、`-` |
| `_strip_invisible(text)` | 移除 Unicode 不可见字符（零宽空格、BOM 等） |

**单位后缀映射**（大小写不敏感）：
- `K` → ×1,000
- `M` → ×1,000,000
- `B` → ×1,000,000,000

---

### 4.11 `json_file.py` — JSON 原子写 seam（D-02，~40 行）

| 函数 | 说明 |
|------|------|
| `atomic_write_json(path, data)` | 原子写入：先写 `.tmp` 再 `os.replace`；失败清理临时文件并抛出 OSError，由调用方决定告警/降级 |
| `try_load_json(path)` | 容错读取：返回解析值（形状校验交由调用方）；文件缺失/解析失败返回 None |

**范围**：通用 JSON 持久化 seam（当前消费方为 `SettingsStore`）。`DataStore` 保留其更丰富的写路径（滚动备份 + 损坏恢复），未改用本 seam；**CSV 不走本 seam**（CSV 是导出格式而非持久化状态，D-02 拍板）。

---

### 4.12 `settings_store.py` — 设置持久化（D-02，~45 行）

#### 类：`SettingsStore`

| 方法 | 说明 |
|------|------|
| `__init__(settings_file=SETTINGS_FILE)` | 设置文件路径 |
| `load()` | 容错读：文件缺失 → `{}`（首次运行静默）；解析失败 → warning + `{}`；顶层非 dict → warning + `{}` |
| `save(settings)` | 经 `atomic_write_json` 原子落盘；失败仅记 warning，不抛异常（不阻断关窗/切换主题） |

**职责边界**：MainWindow 只保留「编码/解码」（窗口状态 ↔ dict），文件 I/O 全部收敛到此处。

---

## 五、依赖关系

### 5.1 外部依赖

| 包 | 版本要求 | 用途 |
|-----|----------|------|
| PySide6 | ==6.11.1 | Qt 官方 Python 绑定，UI 框架 |
| pyqtgraph | ==0.14.0 | 高性能 Qt 原生图表渲染 |
| numpy | (pyqtgraph 的传递依赖) | 数值计算（图表数据） |
| pytest | ==9.1.1（requirements-dev.txt） | 单元测试框架 |

### 5.2 模块间依赖关系图

```
main.py
  └── app/main_window.py
        ├── app/input_panel.py ──┐
        ├── app/table_widget.py  ├── formatting.py
        ├── app/chart_widget.py  │
        ├── app/theme.py          （无外部依赖）
        ├── data_store.py ───────┼── config.py
        ├── settings_store.py ───┼── json_file.py, config.py
        ├── json_file.py          （无外部依赖）
        ├── calculator.py ───────┼── config.py, formatting.py
        └── config.py
```

### 5.3 导入清单

| 模块 | 导入来源 |
|------|----------|
| `main.py` | `app.main_window`, `config`, `PySide6`（QtCore/QtGui/QtNetwork/QtWidgets） |
| `app/main_window.py` | `app.input_panel`, `app.table_widget`, `app.chart_widget`, `app.theme`, `config`, `data_store`, `settings_store`, `formatting`, `calculator`, `PySide6` |
| `app/input_panel.py` | `app.theme`, `formatting`, `PySide6` |
| `app/table_widget.py` | `app.theme`, `formatting`, `calculator`, `PySide6` |
| `app/chart_widget.py` | `app.theme`, `numpy`, `pyqtgraph`, `PySide6` |
| `app/theme.py` | 无外部依赖（仅标准库） |
| `calculator.py` | `config`, `formatting` |
| `data_store.py` | `config` |
| `settings_store.py` | `json_file`, `config` |
| `json_file.py` | 无外部依赖（仅标准库） |
| `formatting.py` | 无外部依赖（仅标准库） |

---

## 六、数据模型

### 6.1 `data.json` 格式

```json
{
  "2026-07-27": {
    "cash": 88541000.0,
    "warehouse": 460900000.0
  }
}
```

- 日期为 key（`YYYY-MM-DD` 格式）
- `cash` 为当前现金（float）
- `warehouse` 为仓库价值（float，已包含现金）
- 最多保留最近 7 条记录（超出删除最旧，按记录数而非日历天数）

### 6.2 `settings.json` 格式

```json
{
  "geometry": "hex-encoded QByteArray",
  "pinned": false,
  "theme": "light"
}
```

### 6.3 备份文件

| 文件 | 说明 |
|------|------|
| `data.json.bak` | 兼容旧版单文件备份（与 `.bak.1` 内容相同） |
| `data.json.bak.1` | 最新滚动备份（保存前一刻的状态） |
| `data.json.bak.2` | 第二份滚动备份 |
| `data.json.bak.3` | 最旧滚动备份 |

---

## 七、测试体系

### 7.1 单元测试（pytest）

| 测试文件 | 用例数 | 覆盖范围 |
|----------|--------|----------|
| `tests/test_calculator.py` | 61 | DayRecord 属性、冻结、CRUD、日期回溯、记录滚动（recent_records/rotate_weekly）、收益率计算、格式化、盈亏标签、删除、滚动旋转（含删除日志 O-14）、汇总、CSV 导出（含金额统一格式化 O-11）、现金>仓库保存告警（O-08）、带符号金额 format_signed_money（D-01） |
| `tests/test_data_store.py` | 18 | 空加载、保存/加载回环、备份创建、备份编号、滚动旋转、主文件损坏恢复、滚动备份恢复、全部损坏恢复、原子写入无残留、Unicode 支持、备份失败日志、顶层 list 视为损坏（O-09） |
| `tests/test_formatting.py` | 58 | 格式化（各种量级/零/负/None）、输入解析（纯数字/逗号/¥/￥/$/后缀/空格/非法格式）、校验边界、焦点格式化/反格式化 |
| `tests/test_settings_store.py` | 15 | json_file seam（原子写/容错读/失败清理）+ SettingsStore（缺失静默/损坏告警/非 dict 兜底/原子落盘/失败不抛，D-02） |

**运行方式**：在项目根目录执行 `pytest`

### 7.2 UI 烟测（pytest offscreen）

UI 烟测并入 pytest（C5 迁移，2026-08-01 删除影子脚本 `verify_all.py`），
offscreen 模式下覆盖原 14 个模块中的 UI 部分：

| 测试文件 | 用例数 | 覆盖范围 |
|----------|--------|----------|
| `tests/test_ui_smoke.py` | 23 | UI 启动/渲染、保存、编辑、删除（确认/取消）、主题切换、窗口置顶、设置持久化、几何恢复（兼容旧 Tkinter 格式）、输入校验联动、失焦格式化、快捷键（Enter/Esc）、CSV 导出按钮、今日未录入提醒、图表稀疏提示（O-06）、编辑态关窗确认（O-13）、自动清理提示（O-14） |
| `tests/test_input_panel.py` | 18 | InputPanel getter 语义 / raw getter / refresh_validity 公开 seam / 编辑状态归属 / C9 静态守卫 / save_today 走公开 API / cash≤warehouse 不变式警告与保存拦截（O-08） |
| `tests/test_table_theme.py` | 3 | 表格主题色实时解析（非 import 期冻结）+ AST 防复发 |

**运行方式**：在项目根目录执行 `pytest`（所有 Qt 用例均自动使用 offscreen 平台）

---

## 八、项目运行方式

### 8.1 环境准备

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows: venv\Scripts\activate
# Linux/macOS: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 8.2 开发模式运行

```bash
python main.py
```

### 8.3 运行测试

```bash
# 全部测试（含 UI 烟测，Qt 用例自动使用 offscreen 平台）
pytest
```

### 8.4 打包为可执行文件

```bash
pip install pyinstaller
python -m PyInstaller 收益计算器.spec --noconfirm
```

**产物**（O-20 起为 onedir）：`dist/收益计算器/收益计算器.exe` + `dist/收益计算器/_internal/`。整目录分发或 zip 压缩，双击 exe 即运行；运行态数据（`data.json`/`settings.json`/日志）统一生成在用户目录 `~/收益计算器`（O-22），与 exe 位置/重建解耦——`dist/` 每次构建整体覆盖也不影响用户数据。旧版 exe 目录/项目根内的数据在首次启动时由 `migrate_legacy_data` 自动复制（复制非移动，源保留）。

**为什么是 onedir 而非单文件**（O-20）：单文件模式每次启动需把整包解压到 `%TEMP%\_MEI*`（实测 181MB），是启动慢（~2-4s）的根因；onedir 免解压，冷启动实测 ~1.5s。`config.APP_DIR`（`sys.executable`）与 `main._icon_path`（`sys._MEIPASS`）在 onedir 下行为一致；O-22 后运行态数据不再依赖 `APP_DIR`，改走 `DATA_DIR`（`Path.home()/收益计算器`）。

**体积瘦身**（O-20，80MB 单文件 → 117MB 目录）：spec 内 `excludes` 剔除 matplotlib/PIL 及其纯 Python 依赖（pyqtgraph 的 Matplotlib 导出器运行时从不加载，importtime 实测）；Qt 二进制白名单过滤（bindepend 校验依赖闭包后，仅保留 Core/Gui/Widgets/Network/OpenGL/OpenGLWidgets/Svg/Test——后二者为 pyqtgraph import 时实际加载）；剔除全部 Qt translations（应用不装 QTranslator，文案硬编码中文）；剔除 opengl32sw.dll 软件渲染器（从不创建 GL 上下文）与 tls/networkinformation 插件。`upx=False`（本机未装 UPX，此前为空转）。

**图标**：`收益计算器.spec` 中 `EXE(icon='app_icon.ico')` 设置 exe 文件图标；`datas=[('app_icon.ico', '.')]` 将图标随包内嵌，供 `main.py` 的 `setWindowIcon` 运行时加载（窗口/任务栏图标）。源码版从项目根目录读取同一文件（`_icon_path()`）。

---

## 九、关键决策记录

| # | 决策 | 选择 | 理由 |
|---|------|------|------|
| 1 | UI 框架 | PySide6 | LGPL 协议 + Qt 官方绑定 + Python 原生集成 |
| 2 | 图表库 | pyqtgraph | 原生 Qt 渲染，无 WebView 开销，交互流畅 |
| 3 | 开发顺序 | 分阶段 | 先 Tkinter 增强功能，再 PySide6 迁移，互不阻塞 |
| 4 | 收益率精度 | 1 位小数 | 紧凑，足够判断趋势 |
| 5 | 盈亏标签 | 单字 + 圆角 Badge | 简洁，红绿底色一眼可辨 |
| 6 | 单实例保证 | QLocalServer | Qt 原生方案，PyInstaller 兼容，崩溃后自动清理 |
| 7 | 数据格式 | JSON 本地文件 | 无数据库依赖，简单可靠 |
| 8 | 持久化策略 | 原子写入 + 3 份滚动备份 | 防崩溃数据丢失，可回溯 |
| 9 | 主题系统 | 两套完整色板 + QSS 动态生成 | 一键切换，增量更新不重建图表 |

---

## 十、常见注意事项

1. **主题切换**：运行时必须用 `get_color(key)` 而非模块级常量，因为常量在 `import` 时固定为 light 主题
2. **DayRecord.total**：`total` = `warehouse`（不是 `warehouse + cash`），现金是仓库的组成部分
3. **保留条数限制**：`ProfitCalculatorLogic.rotate_weekly()` 在每次 `save_today()` 后执行，按「录入条数」超过上限时从最旧开始删除；表格/图表/汇总（`recent_records`/`summary`）同以最近 7 条实际录入记录为基准，而非最近 7 个日历天
4. **编辑模式**：编辑回填时使用 `unformat_input_value()` 转为纯数字，保存时用原日期覆盖写入
5. **图表更新**：`_update_chart()` 使用持久化的 `PlotCurveItem` + `FillBetweenItem`，仅 `setData()` 更新，避免重建
6. **输入框去抖**：`MoneyLineEdit` 使用 150ms 去抖的 QTimer，快速输入时避免每次按键都触发校验
7. **DPI 感知**：Windows 下通过 `SetProcessDpiAwareness(1)` 配合 `Qt.HighDpiScaleFactorRoundingPolicy.PassThrough`
8. **几何格式兼容**：`_setup_window()` 同时兼容新格式（hex QByteArray）和旧格式（Tkinter `WxH+X+Y` 字符串）

---

*本文档由 AI 基于项目源码自动生成，覆盖所有模块、类、函数及关键实现细节。*
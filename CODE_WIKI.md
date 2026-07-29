# 收益计算器 (Profit Calculator) — Code Wiki

> 版本：PySide6 版（第二阶段迁移完成 + 第三阶段架构优化完成）  
> 生成日期：2026-07-29  
> 测试状态：103 项 pytest 全部通过，verify_all.py 全部通过

---

## 一、项目概述

**收益计算器**是一款 Windows 桌面工具，面向个人投资者。用户每天记录「当前现金」和「仓库价值（含现金）」两个数字，工具自动记录最近 7 天数据，以表格展示每日盈亏变化，并以双曲线图可视化趋势。

| 属性 | 说明 |
|------|------|
| 语言 | Python 3.10+ |
| UI 框架 | PySide6（Qt 官方绑定，LGPL 协议） |
| 图表库 | pyqtgraph（原生 Qt 渲染，高性能） |
| 数据存储 | 本地 JSON 文件（原子写入 + 滚动备份） |
| 打包方式 | PyInstaller → 单 .exe |
| 测试框架 | pytest（103 项） |
| 开发阶段 | 三阶段全部完成（Tkinter 增强 → PySide6 迁移 → 架构优化） |

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
│  │  config.py   │  │ app/theme.py — QSS 样式表生成     │ │
│  │  路径/字体/  │  │ 复用 config.py 的 THEMES 色板     │ │
│  │  THEMES 色板 │  │                                    │ │
│  └──────────────┘  └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入 → MoneyLineEdit (实时校验/去抖)
    → InputPanel (合法性校验 → 启用保存按钮)
    → MainWindow.save_today() (解析 → 验证 → 保存)
    → ProfitCalculatorLogic.save_record() (写入内存 dict)
    → _rotate_weekly() (保持最多 7 天)
    → DataStore.save() (原子写入 JSON + 滚动备份)
    → refresh_display() → TableWidget.draw() + ChartWidget.draw()
```

---

## 三、文件结构

```
Profit Calculator/
├── main.py                  ← [主入口] PySide6 QApplication + 单实例保证
├── app/
│   ├── __init__.py          ← app 包标记，重导出 get_color/get_theme/set_theme
│   ├── main_window.py       ← [UI 骨架] QMainWindow，组件协调与数据流
│   ├── input_panel.py       ← 输入面板：MoneyLineEdit + 校验 + 编辑模式
│   ├── table_widget.py      ← 双栏 7 日数据表格（7 列）
│   ├── chart_widget.py      ← pyqtgraph 双曲线图 + PNG 导出
│   ├── theme.py             ← QSS 样式表生成（从 config.py 复用 THEMES 色板）
│   └── config.py            ← 空文件（路径常量已迁移至根 config.py）
├── calculator.py            ← [业务逻辑] DayRecord 数据类 + ProfitCalculatorLogic
├── config.py                ← [基础配置] 路径、日期格式、字体、THEMES 色板
├── data_store.py            ← [持久化] DataStore — JSON 原子写入 + 滚动备份
├── formatting.py            ← [工具] 金额格式化、输入解析、校验
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py   ← 21 个测试（DayRecord + 业务逻辑）
│   ├── test_data_store.py   ← 18 个测试（保存/加载/备份/恢复）
│   └── test_formatting.py   ← 31 个测试（格式化/解析/校验）
├── verify_all.py            ← 全量集成验证脚本（offscreen 模式，14 个模块）
├── data.json                ← 运行态数据（日期 → {cash, warehouse}）
├── settings.json            ← 窗口几何 + 置顶 + 主题持久化
├── requirements.txt         ← PySide6>=6.6.0, pyqtgraph>=0.13.0
├── .gitignore
├── CONSENSUS.md             ← 开发共识文档（三阶段任务记录）
└── PROJECT_REFERENCE.md     ← 项目介绍书（架构说明）
```

---

## 四、核心模块详细说明

### 4.1 `main.py` — 程序入口（~74 行）

**职责**：启动 PySide6 应用，单实例保证，事件循环管理。

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
| `_build_ui()` | 构建标题栏、日期、输入面板卡片、表格卡片、图表卡片、底部提示栏 |
| `_connect_signals()` | 连接信号槽（Enter→保存, Esc→清空, 编辑/删除请求） |
| `save_today()` | 解析输入 → 验证 → 保存到 logic → 滚动 7 日 → 持久化 → 刷新显示 |
| `_rotate_weekly()` | 保持最多 7 天数据，排序后从最旧开始删除 |
| `refresh_display()` | 获取 records → 刷新表格 + 图表 |
| `_start_edit(date_str, record)` | 进入编辑模式，回填数据到输入面板 |
| `_cancel_edit()` | 退出编辑模式，清空输入框 |
| `_delete_record(date_str)` | 确认对话框 → 删除数据 → 持久化 → 刷新 |
| `_toggle_theme()` | 切换亮/暗主题，增量更新 QSS + 图表颜色 |
| `_toggle_pin()` | 切换窗口置顶状态 |
| `_save_settings()` / `_load_settings()` | 设置持久化（geometry/theme/pinned） |

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
| `is_editing()` / `get_editing_date()` | 状态查询 |
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
| 3 | 较前日 | 100 | 差值，红涨绿跌，无前日数据显示"—" |
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
| `draw(records)` | n≥2 时渲染图表，n<2 时显示占位提示文字 |
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

### 4.6 `app/theme.py` — 主题系统（~243 行）

从根目录 `config.py` 导入 `THEMES` 色板字典和主题切换函数，专供 `app/` 内的 PySide6 组件使用。

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
| `__init__` | `data: dict` | — | 绑定数据字典引用 |
| `get_record` | `date_str: str` | `DayRecord \| None` | 查单日数据，字段缺失/格式异常返回 None |
| `save_record` | `date_str, cash, warehouse` | `DayRecord` | 保存某日记录 |
| `last_record_before` | `date_str, max_days=365` | `(str, DayRecord) \| None` | 向前回溯最近有效记录（跳过空/无效日） |
| `get_weekly_records` | `end_date, days=7` | `list[(str, DayRecord\|None)]` | 获取连续 N 天数据，按日期升序 |
| `calculate_rate` | `prev_warehouse, current_warehouse` | `float \| None` | 计算收益率百分比，前值 None 或为零返回 None |
| `format_rate` | `rate: float \| None` | `(str, str)` | 格式化收益率显示文本和颜色 |
| `get_pnl_label` | `prev_warehouse, current_warehouse` | `(str, str)` | 判断盈亏标签和颜色 |

**关键业务规则**：
- `total` = `warehouse`（非 `warehouse + cash`）
- 收益率 = `(今日warehouse - 前日warehouse) / 前日warehouse × 100%`，精度 1 位小数
- 盈亏标签：盈（绿底）/ 亏（红底）/ —（灰底，无前日数据或持平）

---

### 4.8 `config.py` — 基础配置（~127 行）

| 常量 | 值 | 说明 |
|------|-----|------|
| `APP_DIR` | Path | 应用根目录（打包后为 exe 所在目录） |
| `DATA_FILE` | `data.json` | 数据文件路径 |
| `BACKUP_FILE` | `data.json.bak` | 备份文件基础路径 |
| `SETTINGS_FILE` | `settings.json` | 设置文件路径 |
| `DATE_FORMAT` | `"%Y-%m-%d"` | 日期格式 |
| `WEEK_DAYS` | `7` | 数据保留天数 |
| `FONT_TITLE` | `("Microsoft YaHei", 18, "bold")` | 标题字体 |
| `FONT_LABEL` | `("Microsoft YaHei", 11)` | 标签字体 |
| `FONT_INPUT` | `("Microsoft YaHei", 13)` | 输入字体 |
| `FONT_TABLE_HEADER` | `("Microsoft YaHei", 10, "bold")` | 表头字体 |
| `FONT_TABLE_CELL` | `("Microsoft YaHei", 10)` | 表格字体 |
| `THEMES` | `dict` | `light` / `dark` 两套色板，各 ~30 个语义化 token |

**主题 color token 说明**：

| Token | 用途 |
|-------|------|
| `BG` | 全局背景 |
| `FG_LABEL` / `FG_MUTED` / `FG_TODAY` | 标签/灰显/今日文字颜色 |
| `FG_POS` / `FG_NEG` | 涨/跌颜色 |
| `BTN_BG` / `BTN_BG_HOVER` / `BTN_FG` | 按钮颜色 |
| `BORDER_DEFAULT` / `BORDER_VALID` / `BORDER_INVALID` | 输入框边框颜色 |
| `CHART_CASH` / `CHART_WAREHOUSE` / `CHART_TOTAL` / `CHART_GRID` / `CHART_BG` / `CHART_AXIS` / `CHART_TEXT` | 图表颜色 |
| `TABLE_TEXT` / `TABLE_TEXT_BOLD` / `TABLE_ROW_EVEN_BG` / `TABLE_ROW_ODD_BG` / `TABLE_ROW_HOVER_BG` / `TABLE_HEADER_BG` / `TABLE_HEADER_FG` | 表格颜色 |
| `CARD_BG` / `CARD_BORDER` / `INPUT_BG` / `INPUT_FG` | 卡片/输入框颜色 |
| `MUTED_BG` / `SEPARATOR` / `PLACEHOLDER` | 辅助颜色 |

**函数**：

| 函数 | 说明 |
|------|------|
| `get_theme()` | 返回当前主题配色字典 |
| `set_theme(name)` | 切换主题（`"light"` \| `"dark"`） |
| `get_color(key)` | 获取当前主题下指定颜色值（运行时安全） |

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
| `_rotate_backups()` | 滚动备份：bak.2→bak.3, bak.1→bak.2, 当前→bak.1 + bak |

**关键机制**：
- **原子写入**：`.tmp` → `os.replace`，保证写入过程中进程崩溃不会损坏原文件
- **滚动备份**：最多保留 3 份历史备份（`data.json.bak.1` 为最新）
- **兼容性**：同时保留旧版单文件 `.bak`（与 `.bak.1` 内容相同）
- **损坏恢复**：主文件 JSON 解析失败时自动从最近可用备份恢复，全部损坏则返回空字典

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

## 五、依赖关系

### 5.1 外部依赖

| 包 | 版本要求 | 用途 |
|-----|----------|------|
| PySide6 | ≥6.6.0 | Qt 官方 Python 绑定，UI 框架 |
| pyqtgraph | ≥0.13.0 | 高性能 Qt 原生图表渲染 |
| numpy | (pyqtgraph 的传递依赖) | 数值计算（图表数据） |
| pytest | (开发依赖) | 单元测试框架 |

### 5.2 模块间依赖关系图

```
main.py
  └── app/main_window.py
        ├── app/input_panel.py ──┐
        ├── app/table_widget.py  ├── formatting.py
        ├── app/chart_widget.py  │
        ├── app/theme.py ────────┼── config.py
        ├── data_store.py ───────┼── config.py
        ├── calculator.py ───────┼── config.py, formatting.py
        └── config.py
```

### 5.3 导入清单

| 模块 | 导入来源 |
|------|----------|
| `main.py` | `app.main_window`, `PySide6` |
| `app/main_window.py` | `app.input_panel`, `app.table_widget`, `app.chart_widget`, `app.theme`, `config`, `data_store`, `formatting`, `calculator`, `PySide6` |
| `app/input_panel.py` | `app.theme`, `formatting`, `PySide6` |
| `app/table_widget.py` | `app.theme`, `formatting`, `calculator`, `PySide6` |
| `app/chart_widget.py` | `app.theme`, `numpy`, `pyqtgraph`, `PySide6` |
| `app/theme.py` | `config`（根目录） |
| `calculator.py` | `config`, `formatting` |
| `data_store.py` | `config` |
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
- 最多保留 7 天数据

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
| `tests/test_calculator.py` | 21 | DayRecord 属性、冻结、CRUD、日期回溯、7 日滚动、收益率计算、格式化、盈亏标签 |
| `tests/test_data_store.py` | 18 | 空加载、保存/加载回环、备份创建、备份编号、滚动旋转、主文件损坏恢复、滚动备份恢复、全部损坏恢复、原子写入无残留、Unicode 支持 |
| `tests/test_formatting.py` | 31 | 格式化（各种量级/零/负/None）、输入解析（纯数字/逗号/¥/￥/$/后缀/空格/非法格式）、校验边界、焦点格式化/反格式化 |

**运行方式**：在项目根目录执行 `pytest`

### 7.2 全量集成验证（verify_all.py）

`verify_all.py` 在 offscreen 模式下运行，覆盖 14 个模块：

1. 业务逻辑层（calculator.py）
2. 格式化层（formatting.py）
3. 数据持久化层（data_store.py）
4. UI 启动 & 基本渲染
5. 保存今日数据
6. 编辑模式
7. 删除数据（确认/取消）
8. 亮/暗主题切换
9. 窗口置顶切换
10. 设置持久化
11. 窗口几何恢复（兼容旧 Tkinter 格式）
12. 7 天滚动旋转
13. 金额输入校验 + 格式化
14. 键盘快捷键（Enter/Esc）

**运行方式**：`QT_QPA_PLATFORM=offscreen python verify_all.py`

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
# 单元测试
pytest

# 全量集成验证（offscreen 模式，无需 GUI）
QT_QPA_PLATFORM=offscreen python verify_all.py
```

### 8.4 打包为可执行文件

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "收益计算器" main.py
```

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
3. **7 日限制**：`_rotate_weekly()` 在每次 `save_today()` 后执行，排序后从最旧开始删除
4. **编辑模式**：编辑回填时使用 `unformat_input_value()` 转为纯数字，保存时用原日期覆盖写入
5. **图表更新**：`_update_chart()` 使用持久化的 `PlotCurveItem` + `FillBetweenItem`，仅 `setData()` 更新，避免重建
6. **输入框去抖**：`MoneyLineEdit` 使用 150ms 去抖的 QTimer，快速输入时避免每次按键都触发校验
7. **DPI 感知**：Windows 下通过 `SetProcessDpiAwareness(1)` 配合 `Qt.HighDpiScaleFactorRoundingPolicy.PassThrough`
8. **几何格式兼容**：`_setup_window()` 同时兼容新格式（hex QByteArray）和旧格式（Tkinter `WxH+X+Y` 字符串）

---

*本文档由 AI 基于项目源码自动生成，覆盖所有模块、类、函数及关键实现细节。*
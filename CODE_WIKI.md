# Delta Force Dashboard — Code Wiki

> 版本：PySide6 版（三阶段 + Phase 4 + C 系列 + O 系列 + D 系列 + F 系列运维 + G/H/J 系列 + K 系列 + L 系列全部完成）  
> 生成日期：2026-08-08  
> 测试状态：<!--AUTO:tests_total:total-->527<!--/AUTO--> 项 pytest 全部通过（含 UI 烟测 + 制造产物推荐 + 兑换利润）

---

## 一、项目概述

**Delta Force Dashboard**是一款 Windows 桌面工具，面向个人投资者。用户每天记录「当前现金」和「仓库价值（含现金）」两个数字，工具自动保留最近 30 条实际录入记录（间断录入不丢历史），视图 7/30 可切换，以表格展示每日盈亏变化，并以双曲线图可视化趋势。

| 属性 | 说明 |
|------|------|
| 语言 | Python 3.10+ |
| UI 框架 | PySide6（Qt 官方绑定，LGPL 协议） |
| 图表库 | pyqtgraph（原生 Qt 渲染，高性能） |
| 数据存储 | 本地 JSON 文件（原子写入 + 滚动备份） |
| 打包方式 | PyInstaller → onedir 目录（`dist/Delta Force Dashboard/`，O-20 起） |
| 测试框架 | pytest（<!--AUTO:tests_total:total-->527<!--/AUTO--> 项） |
| 开发阶段 | 三阶段 + Phase 4（T-01~T-05）+ C 系列（C1~C9）+ O 系列（O-01~O-22，O-07 YAGNI 关闭）+ D 系列（D-01~D-08）+ F 系列运维（F-01 文档同步 / F-02 迁移源清理标记）+ J 系列（J-01 保留上限 30 / J-02 视图 7/30 切换，ADR-0003）全部完成 |

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
│  │  保留条数    │  │ signal_color：信号→主题色（D-01） │ │
│  └──────────────┘  └───────────────────────────────────┘ │
│  ┌───────────────────────────────────────────────────┐ │
│  │ signals.py — 信号枚举叶子（零依赖）               │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 2.2 数据流

```
用户输入 → MoneyLineEdit (实时校验/去抖)
    → InputPanel (合法性校验 → 启用保存按钮)
    → MainWindow.save_today() (解析 → 验证 → 保存)
    → ProfitCalculatorLogic.save_record() (写入内存 dict)
    → ProfitCalculatorLogic.rotate_weekly() (保留最近 30 条实际录入记录，超出删除最旧)
    → DataStore.save() (原子写入 JSON + 滚动备份)
    → refresh_display() → TableWidget.draw() + ChartWidget.draw()
```

---

## 三、文件结构

```
Delta Force Dashboard/
├── main.py                  ← [主入口] PySide6 QApplication + 单实例保证 + 应用图标
├── app/
│   ├── __init__.py          ← app 包标记
│   ├── main_window.py       ← [UI 骨架] QMainWindow，组件协调与数据流（含账号区 Y-03/Y-04/Y-05）
│   ├── sidebar.py           ← 左侧导航栏（记账 / 利润 + 底部操作按钮 + 顶部账号区 Y-04，L-01，~98 行）
│   ├── registry.py          ← 插件式 Widget 注册系统（AppWidget + WidgetRegistry，~54 行）
│   ├── crafting_page.py     ← 制造产物推荐页面（4 台位卡片，L-03）
│   ├── exchange_page.py     ← 兑换利润页面（7 种子弹自选包，X 系列）
│   ├── fetch_worker.py      ← 后台请求 worker（QThread，网络调用移出 UI 线程，~41 行）
│   ├── profit_page.py       ← 利润页面单页滚动容器（制造产物 + 兑换利润纵向堆叠）
│   ├── input_panel.py       ← 输入面板：MoneyLineEdit + 校验 + 编辑模式
│   ├── table_widget.py      ← 双栏数据表格（视图 7/30 按钮组切换，7 列）
│   ├── chart_widget.py      ← pyqtgraph 双 Y 轴曲线图（单坐标系）+ PNG 导出 + 稀疏数据提示
│   └── theme.py             ← QSS 样式表生成（从 config.py 复用 THEMES 色板）
├── calculator.py            ← [业务逻辑] DayRecord 数据类 + ProfitCalculatorLogic
├── account_store.py         ← [多账号（Y 系列）] AccountStore 账号目录管理 + 校验 + v2 迁移（ADR-0005）
├── signals.py               ← [领域信号] RateSignal + PnLSignal 共享叶子（零依赖，D-01 收敛点）
├── config.py                ← [基础配置] 路径、日期格式、字体、THEMES 色板
├── data_store.py            ← [持久化] DataStore — JSON 原子写入 + 滚动备份
├── json_file.py             ← [持久化 seam] JSON 原子写 + 容错读（D-02）
├── kkrb_client.py           ← [Delta Force] kkrb.net API 客户端，零外部依赖（L-02）
├── settings_store.py        ← [持久化] SettingsStore — 设置容错读 + 原子写（D-02）
├── formatting.py            ← [工具] 金额格式化、输入解析、校验
├── scripts/                 ← [F-01 文档同步工具链] CODE_WIKI 机械标记生成/校验
│   ├── doc_sync.py          ← 三类机械标记（lines/tests/sig）生成 + `--check` 校验（stdlib）
│   ├── pre-commit.sh        ← pre-commit 钩子源：跑 `doc_sync.py --check` 拦截漂移
│   └── install-hooks.bat    ← 把 pre-commit.sh 复制到 `.git/hooks/pre-commit`
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py
│   ├── test_presentation.py ← <!--AUTO:tests:tests/test_presentation.py-->23<!--/AUTO--> 个测试（展示文本生成：format_rate / format_signed_money / format_window_text / format_saved_indicator / get_pnl_label）
│   ├── test_calculator.py   ← <!--AUTO:tests:tests/test_calculator.py-->81<!--/AUTO--> 个测试（DayRecord + 业务逻辑 + CSV 导出 + serialize/加载时过滤 D-03 + 不变式/汇总/窗口变化量 D-05/06 + 跳过记录 warning）
│   ├── test_data_store.py   ← <!--AUTO:tests:tests/test_data_store.py-->18<!--/AUTO--> 个测试（保存/加载/备份/恢复/日志）
│   ├── test_account_store.py ← <!--AUTO:tests:tests/test_account_store.py-->52<!--/AUTO--> 个测试（Y-01 多账号存储层：扫描/新建校验/resolve 兜底/DataStore 路径注入继承）
│   ├── test_formatting.py   ← <!--AUTO:tests:tests/test_formatting.py-->58<!--/AUTO--> 个测试（格式化/解析/校验）
│   ├── test_input_panel.py  ← <!--AUTO:tests:tests/test_input_panel.py-->22<!--/AUTO--> 个测试（C4 seam + C9 静态守卫 + O-02 seam + O-08 不变式 + D-04 真实事件/焦点链路）
│   ├── test_table_theme.py  ← <!--AUTO:tests:tests/test_table_theme.py-->8<!--/AUTO--> 个测试（C1 主题色实时解析 + D-01 零差值）
│   ├── test_settings_store.py ← <!--AUTO:tests:tests/test_settings_store.py-->34<!--/AUTO--> 个测试（D-02 json_file seam + SettingsStore 容错 + on_error 回调/异常详情回归）
│   ├── test_migration.py    ← <!--AUTO:tests:tests/test_migration.py-->14<!--/AUTO--> 个测试（O-22 数据目录迁移 + mkdir 顺序回归 + F-02 .migrated 标记/清理提示）
│   ├── test_ui_smoke.py     ← <!--AUTO:tests:tests/test_ui_smoke.py-->95<!--/AUTO--> 个测试（C5 UI 烟测 + O-04/05/06/08/09/13/14，offscreen）
│   ├── test_kkrb_client.py  ← <!--AUTO:tests:tests/test_kkrb_client.py-->28<!--/AUTO--> 个测试（数据模型 + 客户端会话/传输/缓存 + 解析收敛验证）
│   ├── test_kkrb_parsing.py ← <!--AUTO:tests:tests/test_kkrb_parsing.py-->28<!--/AUTO--> 个测试（解析纯函数 + 畸形输入矩阵：非 dict/缺字段/类型异常/排序/回退 key）
│   ├── test_load_state.py   ← <!--AUTO:tests:tests/test_load_state.py-->8<!--/AUTO--> 个测试（LoadState 四态转移矩阵：防重入/失败重试/loaded 手动刷新）
│   ├── test_theme_qss.py    ← <!--AUTO:tests:tests/test_theme_qss.py-->4<!--/AUTO--> 个测试（主题双轨收敛：reuseBtn danger 属性选择器/button_style 删除守卫/属性切换）
│   ├── test_theme_roles.py  ← <!--AUTO:tests:tests/test_theme_roles.py-->14<!--/AUTO--> 个测试（U-03 色彩角色：键名如实/键引用完整/装饰≠语义/明度带/饱和度/两两色差/标签对比度）
│   ├── test_fetch_pages.py  ← <!--AUTO:tests:tests/test_fetch_pages.py-->30<!--/AUTO--> 个测试（T-01 FetchWorker 安全关闭/逃生舱托管 + T-02 preload 幂等/失败日志 + T-03 基类提炼回归）
│   ├── test_chart_geometry.py ← <!--AUTO:tests:tests/test_chart_geometry.py-->6<!--/AUTO--> 个测试（adaptive_range 纯函数）
│   ├── test_json_file.py    ← <!--AUTO:tests:tests/test_json_file.py-->3<!--/AUTO--> 个测试（JSON 原子写 + 容错读）
		│   └── test_doc_sync.py     ← <!--AUTO:tests:tests/test_doc_sync.py-->1<!--/AUTO--> 个测试（F-01 冒烟：`doc_sync.py --check` 通过即 CODE_WIKI 基线同步）
├── app_icon.ico             ← 应用图标（exe 文件 + 运行窗口，PyInstaller datas 内嵌）
├── delta_force_dashboard.spec           ← PyInstaller 打包配置（onedir + 图标，O-20 瘦身）
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

### 4.1 `main.py` — 程序入口（<!--AUTO:lines:main.py-->~148 行<!--/AUTO-->）

**职责**：启动 PySide6 应用，单实例保证，应用图标，事件循环管理。

| 元素 | 说明 |
|------|------|
| `_SERVER_NAME` | 单实例锁名称 `"profit_calculator_singleton_lock"` |
| <!--AUTO:sig:main.py:_is_already_running-->`_is_already_running()`<!--/AUTO--> | 通过 QLocalServer 检测是否已有实例运行 |
| <!--AUTO:sig:main.py:main-->`main()`<!--/AUTO--> | 高 DPI 设置 → 创建 QApplication → 单实例检查 → 创建 MainWindow → 事件循环 → 清理 |

**单实例机制**：使用 QLocalServer（Qt 原生方案），崩溃后自动清理残留 socket 文件。若已有实例运行则静默 `sys.exit(0)`。

---

### 4.2 `app/main_window.py` — 主窗口（<!--AUTO:lines:app/main_window.py-->~832 行<!--/AUTO-->）

**核心类**：`MainWindow(QMainWindow)`

**职责**：管理整个应用的生命周期，协调所有子组件，处理数据流。

#### 关键方法

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:app/main_window.py:MainWindow.__init__-->`__init__(store=None, logic=None, settings_store=None, registry=None, account_store=None, client=None)`<!--/AUTO--> | 加载 DataStore → 加载数据 → 初始化逻辑 → 恢复设置 → 构建 UI → 连接信号 → 应用 QSS |
| <!--AUTO:sig:app/main_window.py:MainWindow._setup_window-->`_setup_window()`<!--/AUTO--> | 窗口标题、最小尺寸（680×700）、几何恢复（兼容 Tkinter 旧格式）、DPI 感知 |
| <!--AUTO:sig:app/main_window.py:MainWindow._build_ui-->`_build_ui()`<!--/AUTO--> | 构建标题栏（含今日未录入提醒、主题/置顶/导出 CSV 按钮）、日期、输入面板卡片、表格卡片、图表卡片、底部提示栏 |
| <!--AUTO:sig:app/main_window.py:MainWindow._connect_signals-->`_connect_signals()`<!--/AUTO--> | 连接信号槽（Enter→保存, Esc→清空, 编辑/删除请求, 导出按钮→_export_csv） |
| <!--AUTO:sig:app/main_window.py:MainWindow.save_today-->`save_today()`<!--/AUTO--> | 解析输入 → 验证 → 保存到 logic → 轮转保留最近 30 条（RETENTION_LIMIT）→ 持久化 → 刷新显示 |
| <!--AUTO:sig:app/main_window.py:MainWindow.refresh_display-->`refresh_display()`<!--/AUTO--> | 获取 records → 刷新汇总/今日未录入/表格/图表 |
| <!--AUTO:sig:app/main_window.py:MainWindow._export_csv-->`_export_csv()`<!--/AUTO--> | QFileDialog 选路径，utf-8-sig 写入 `logic.export_csv()`（O-04） |
| <!--AUTO:sig:app/main_window.py:MainWindow._update_today_status-->`_update_today_status()`<!--/AUTO--> | 今日无记录时显示「今日未录入」，有则隐藏（O-05） |
| <!--AUTO:sig:app/main_window.py:MainWindow._start_edit-->`_start_edit(date_str, record)`<!--/AUTO--> | 进入编辑模式，回填数据到输入面板 |
| <!--AUTO:sig:app/main_window.py:MainWindow._cancel_edit-->`_cancel_edit()`<!--/AUTO--> | 退出编辑模式，清空输入框 |
| <!--AUTO:sig:app/main_window.py:MainWindow._delete_record-->`_delete_record(date_str)`<!--/AUTO--> | 确认对话框 → 删除数据 → 持久化 → 刷新 |
| <!--AUTO:sig:app/main_window.py:MainWindow._toggle_theme-->`_toggle_theme()`<!--/AUTO--> | 切换亮/暗主题，增量更新 QSS + 图表颜色 |
| <!--AUTO:sig:app/main_window.py:MainWindow._toggle_pin-->`_toggle_pin()`<!--/AUTO--> | 切换窗口置顶状态 |
| <!--AUTO:sig:app/main_window.py:MainWindow._save_settings-->`_save_settings()`<!--/AUTO--> | 编码窗口状态（geometry/theme/pinned）→ 委托 `settings_store.save()`（D-02）；Y-03：注入模式外合并 `current_account` 落盘（Y-03，重启回到当前账号） |
| <!--AUTO:sig:app/main_window.py:MainWindow._update_account_title-->`_update_account_title()`<!--/AUTO--> | 记账页标题栏显示「Delta Force Dashboard · <账号名>」（Y-03；注入模式保持原标题） |
| <!--AUTO:sig:app/main_window.py:MainWindow._refresh_account_combo-->`_refresh_account_combo()`<!--/AUTO--> | 账号区下拉列表与业务层账号状态同步（`sidebar.set_accounts`，blockSignals 不触发选择信号，Y-04） |
| <!--AUTO:sig:app/main_window.py:MainWindow._create_account-->`_create_account()`<!--/AUTO--> | 新建账号：QInputDialog 命名 → `AccountStore.create_account` 校验（非法名可读提示、零目录）→ 刷新下拉；当前账号不变（决策 6）；注入模式防御 return（Y-04） |
| <!--AUTO:sig:app/main_window.py:MainWindow._on_account_selected-->`_on_account_selected(name)`<!--/AUTO--> | 切换账号（Y-05）：目标账号 new_store + 重载 logic → cancel_edit/clear_fields/cancel_reuse 防跨账号污染 → count-up 归零 → refresh_display 全量刷新 → 标题/下拉同步 → `_save_settings` 落盘；同账号 no-op；利润页零触碰 |

#### 信号连接

| 信号源 | 信号 | 槽 |
|--------|------|-----|
| `InputPanel` | `save_requested` | `MainWindow.save_today()` |
| `InputPanel` | `cancel_requested` | `MainWindow._cancel_edit()` |
| `TableWidget` | `edit_requested` | `MainWindow._start_edit()` |
| `TableWidget` | `delete_requested` | `MainWindow._delete_record()` |
| QAction (Enter) | `triggered` | `MainWindow.save_today()` |
| QAction (Esc) | `triggered` | `MainWindow._clear_focused_input()` |
| `Sidebar` | `account_selected(str)` | `MainWindow._on_account_selected()`（Y-05 账号切换） |
| `Sidebar` | `create_account_requested()` | `MainWindow._create_account()`（Y-04 新建账号） |

---

### 4.3 `app/input_panel.py` — 输入面板（<!--AUTO:lines:app/input_panel.py-->~362 行<!--/AUTO-->）

#### 类：`MoneyLineEdit(QLineEdit)`

自定义金额输入框，继承自 QLineEdit。

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:app/input_panel.py:MoneyLineEdit.__init__-->`__init__(parent=None)`<!--/AUTO--> | 设置占位文本、右对齐、150ms 去抖 QTimer |
| <!--AUTO:sig:app/input_panel.py:MoneyLineEdit._on_text_changed-->`_on_text_changed(text)`<!--/AUTO--> | 文本变化时重启去抖计时器 |
| <!--AUTO:sig:app/input_panel.py:MoneyLineEdit._update_validity-->`_update_validity()`<!--/AUTO--> | 校验当前输入：空 → normal / 合法 → valid / 非法 → invalid |
| <!--AUTO:sig:app/input_panel.py:MoneyLineEdit.refresh_validity-->`refresh_validity()`<!--/AUTO--> | 立即同步重校验当前文本（公开 seam，委托 `_update_validity()`，O-02；D-04 保留为同步 seam，行为用例走真实事件链路） |
| <!--AUTO:sig:app/input_panel.py:MoneyLineEdit._set_validity_state-->`_set_validity_state(state)`<!--/AUTO--> | 设置 `validity` 属性，触发 QSS 重绘边框 |
| <!--AUTO:sig:app/input_panel.py:MoneyLineEdit.focusInEvent-->`focusInEvent(event)`<!--/AUTO--> | 聚焦时反格式化：`¥1,234.56` → `1234.56`，全选 |
| <!--AUTO:sig:app/input_panel.py:MoneyLineEdit.focusOutEvent-->`focusOutEvent(event)`<!--/AUTO--> | 失焦时格式化：`1234.56` → `¥1,234.56` |

**信号**：`validity_changed(bool)`

#### 类：`InputPanel(QWidget)`

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:app/input_panel.py:InputPanel.__init__-->`__init__(parent=None)`<!--/AUTO--> | 初始化两个输入框与状态标志（C4 起单方归属输入状态） |
| <!--AUTO:sig:app/input_panel.py:InputPanel._build-->`_build()`<!--/AUTO--> | 构建现金/仓库输入行 + 保存按钮 + 取消编辑按钮 + 指示器 |
| <!--AUTO:sig:app/input_panel.py:InputPanel._update_save_btn_state-->`_update_save_btn_state()`<!--/AUTO--> | 两个输入框都合法且非空时启用保存按钮 |
| <!--AUTO:sig:app/input_panel.py:InputPanel._update_invariant_state-->`_update_invariant_state()`<!--/AUTO--> | 现金>仓库时置红框警告并禁用保存（O-08，不变式 D-05） |
| <!--AUTO:sig:app/input_panel.py:InputPanel.set_edit_mode-->`set_edit_mode(date_str, cash, warehouse)`<!--/AUTO--> | 切换编辑模式，填充数据，改变按钮样式（橙色） |
| <!--AUTO:sig:app/input_panel.py:InputPanel.cancel_edit-->`cancel_edit()`<!--/AUTO--> | 退出编辑模式，恢复默认状态 |
| <!--AUTO:sig:app/input_panel.py:InputPanel.is_editing-->`is_editing()`<!--/AUTO--> / `get_editing_date()` | 编辑状态查询（**单方归属 InputPanel**，C4） |
| <!--AUTO:sig:app/input_panel.py:InputPanel.get_cash_value-->`get_cash_value()`<!--/AUTO--> / `get_warehouse_value()` | 解析当前输入返回金额；空→`None`，非法→`ValueError`（C4 seam） |
| <!--AUTO:sig:app/input_panel.py:InputPanel.get_cash_raw-->`get_cash_raw()`<!--/AUTO--> / `get_warehouse_raw()` | 返回输入框原始文本（供解析失败提示） |
| <!--AUTO:sig:app/input_panel.py:InputPanel.refresh_validity-->`refresh_validity()`<!--/AUTO--> | 立即重新校验两个输入框的有效性（经公开 seam，O-02；D-04 后仅供程序化改动，测试不再当后门） |
| <!--AUTO:sig:app/input_panel.py:InputPanel.fill_values-->`fill_values(cash, warehouse)`<!--/AUTO--> | 填入金额并选中现金框（不触发焦点格式化） |
| <!--AUTO:sig:app/input_panel.py:InputPanel.clear_fields-->`clear_fields()`<!--/AUTO--> | 清空输入框，保留已保存指示器 |
| <!--AUTO:sig:app/input_panel.py:InputPanel.set_saved_indicator-->`set_saved_indicator(text)`<!--/AUTO--> | 设置保存成功提示文本 |
| <!--AUTO:sig:app/input_panel.py:InputPanel.focus_cash-->`focus_cash()`<!--/AUTO--> | 聚焦现金输入框 |
| <!--AUTO:sig:app/input_panel.py:InputPanel.apply_theme-->`apply_theme()`<!--/AUTO--> | 更新标签颜色 |

---

### 4.4 `app/table_widget.py` — 数据表格（<!--AUTO:lines:app/table_widget.py-->~507 行<!--/AUTO-->

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
| <!--AUTO:sig:app/table_widget.py:_DaySubTable.draw-->`draw(records, today, prev_warehouse=None)`<!--/AUTO--> | 逐行绘制（复用 widget）：日期、现金、仓库、较前日差值、收益率、盈亏标签、操作按钮 |

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

双栏布局容器：顶部按钮组视图 7/30 可切换（默认 7，emit `view_changed(int)`；
MainWindow 订阅后改 `_view_n` 重拉 records，Q8 深模块）。分栏均分
`mid=ceil(n/2)`——7→4+3、30→15+15。

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:app/table_widget.py:TableWidget.__init__-->`__init__(parent=None, default_view)`<!--/AUTO--> | 构建视图切换按钮组（7/30）+ 左右两栏容器（各含标题 + _DaySubTable） |
| `current_view()` | 返回当前视图条数（7 / 30） |
| `view_changed = Signal(int)` | 按钮组切换时 emit 当前视图条数；MainWindow 订阅 → `_on_view_changed` → `refresh_display`（Q9 表格/曲线图/汇总全联动） |
| <!--AUTO:sig:app/table_widget.py:TableWidget.draw-->`draw(records, today)`<!--/AUTO--> | 拆分 records 为左右两栏（均分），传递跨栏的 prev_warehouse 给右栏 |

---

### 4.5 `app/chart_widget.py` — 图表组件（<!--AUTO:lines:app/chart_widget.py-->~573 行<!--/AUTO-->）

#### 函数：`adaptive_range(values)`

自适应 Y 轴范围（底部留 10%，顶部留 8%）；仓库/现金两轴各自量纲独立调用。空列表返回 `(0.0, 1.0)`。

#### 类：`KMBAxisItem(pg.AxisItem)`

自定义 Y 轴刻度标签，将数值显示为 K/M/B 财务单位（左/右轴共用）。

#### 类：`ChartWidget(QWidget)`

单坐标系双 Y 轴曲线图：仓库价值（左轴，主色实线）与现金（右轴，副色虚线）合并进
同一个 PlotWidget。主 ViewBox 承载仓库序列，副 ViewBox（右轴）承载现金序列，
副 ViewBox 经 `setXLink` + `linkToView` 与主 ViewBox 共享 X 轴，两 Y 轴各自按
自身量纲自适应——避免现金量级远小于仓库时被压成直线（ADR-0002，G-01）。
合并前的上下双图结构（T-05 的 `_ChartPanel`）已删除。

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:app/chart_widget.py:ChartWidget.draw-->`draw(records)`<!--/AUTO--> | n≥2 时渲染双 Y 轴曲线，n<2 时显示占位提示文字；2≤n≤3 时叠加半透明「数据较少」提示 |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._create-->`_create(x, warehouse_vals, cash_vals, dates)`<!--/AUTO--> | 从零创建 PlotWidget + 双 ViewBox + 曲线/端点/hover/图例/右键菜单 |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._update_data-->`_update_data(x, warehouse_vals, cash_vals, dates)`<!--/AUTO--> | 原地更新曲线/端点/双 Y 轴/X 轴标签（不重建） |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._on_mouse_moved-->`_on_mouse_moved(evt)`<!--/AUTO--> | 鼠标移动时显示竖线 + 每系列一个彩色数值标签（按所属 ViewBox 顶部堆叠定位，不贴数据点） |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._format_value-->`_format_value(v)`<!--/AUTO--> | 格式化图表数值为紧凑 K/M/B（与 Y 轴共用 format_compact，带 ¥ 前缀） |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget.apply_theme-->`apply_theme()`<!--/AUTO--> | 主题切换时增量更新双曲线/双轴/hover/图例颜色，不重建 |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._show_sparse_hint-->`_show_sparse_hint()`<!--/AUTO--> | n=2~3 时叠加半透明「数据较少」提示（不触碰曲线与交互） |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget.resizeEvent-->`resizeEvent(event)`<!--/AUTO--> | overlay 提示不参与 layout，手动跟随 widget 尺寸 |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._show_placeholder-->`_show_placeholder(n)`<!--/AUTO--> | n=0 显示「暂无数据」，n=1 显示「至少需要两天数据」 |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._clear_placeholder-->`_clear_placeholder()`<!--/AUTO--> | 移除占位/稀疏提示 label |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._setup_context_menu-->`_setup_context_menu()`<!--/AUTO--> | 为 PlotWidget 绑定右键菜单（导出 PNG） |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._show_context_menu-->`_show_context_menu(pos)`<!--/AUTO--> | 在指定位置弹出右键菜单 |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget.export_png-->`export_png()`<!--/AUTO--> | 导出当前图表为 PNG 文件 |
| <!--AUTO:sig:app/chart_widget.py:ChartWidget._clear_all-->`_clear_all()`<!--/AUTO--> | 销毁图表及占位组件 |

**图表结构**：

```
┌────────────────────────────────────────────┐
│  仓库价值（总收益）— 左轴 主色实线+方块    │
│  现金（子项）— 右轴 副色虚线+圆点          │
│  共享 X 轴：日期标签（MM-DD）              │
│  右轴刻度随现金曲线同色（防归属误读）      │
└────────────────────────────────────────────┘
```

**性能优化**：单 PlotWidget + 持久化 `PlotCurveItem`，更新时仅 `setData()` 原地
刷新，不重建。原生无填充区域（对齐原型评审修正版 0559537）。副 ViewBox 与主
ViewBox 的 `linkToView` 同步在 `_create` 的 `_sync` 闭包内维护，resize 时漏同步
会两线 x 错位（ADR-0002 记录的实现坑位）。

**hover 交互**（对齐原型 `_attach_crosshair`）：共享一根竖线 + 每系列一个彩色
数值标签（文案「系列短名 + 值」）。标签按所属 ViewBox 的顶部做堆叠定位
（`ymax - span*(0.06+0.10j)`），不贴数据点——因双轴跨轴高度不可比，标签只叠放
数值不比较线段长度（ADR-0002 代价项落地）。

---

### 4.6 `app/theme.py` — 主题系统（<!--AUTO:lines:app/theme.py-->~671 行<!--/AUTO-->）

主题数据的单一真实来源：内联定义 `THEMES` 色板字典与 `get_color`/`get_theme`/`set_theme`（T-02 迁入，不再从 config.py 导入），并生成 QSS 样式表，专供 `app/` 内的 PySide6 组件使用；D-01 起还负责「收益率信号 → 主题色」映射（`signal_color`）。

| 函数 | 说明 |
|------|------|
| <!--AUTO:sig:app/theme.py:generate_qss-->`generate_qss(theme_name)`<!--/AUTO--> | 根据主题名生成完整 QSS 样式表（全局/标签/输入框/按钮/表格/卡片/滚动条/提示框） |
| <!--AUTO:sig:app/theme.py:get_theme-->`get_theme()`<!--/AUTO--> / <!--AUTO:sig:app/theme.py:set_theme-->`set_theme(name)`<!--/AUTO--> | 读取 / 切换当前主题（"light" \| "dark"） |
| <!--AUTO:sig:app/theme.py:get_color-->`get_color(key)`<!--/AUTO--> | 取当前主题下指定颜色值（渲染期实时解析，C1；**禁止 import 期调用**）；未知键 `logger.warning`（含键名）后返回 `""`，不 raise（C1-06，`generate_qss` 的 `t[...]` 直接索引语义不变） |
| <!--AUTO:sig:app/theme.py:signal_color-->`signal_color(signal)`<!--/AUTO--> | 收益率信号 `RateSignal` → 当前主题颜色：经 `_SIGNAL_TO_KEY` 映射后由 `get_color` 实时解析（D-01；`RateSignal` 定义于 `signals.py`） |

**QSS 覆盖范围**：QMainWindow, QLabel, QLineEdit, QPushButton, QTableWidget, QHeaderView, QFrame, QStatusBar, QScrollBar, QToolTip。

**主题刷新契约（C1-07/C1-08）**：具 `apply_theme()` 的组件构成统一刷新契约——MainWindow 启动期（`_build_ui` 后）递归遍历子树收集（自顶向下、父拥有子树；节点有 `apply_theme` 即收集且不再下钻）为 `self._theme_refreshers`；`refresh_theme` 重写为「`_apply_qss`（移除 sidebar.apply_theme）+ 按钮文字 + 置顶样式 + refreshers 统一调用」，不再触发数据刷新（`table.draw/_update_summary/_update_today_status` 调用移除，主题与数据刷新彻底解耦）；KPI 磁贴颜色以 `_apply_kpi_styles()` 另法保持（纯内存重算 signal，零 I/O）；启动期同样执行一次 refreshers（保 sidebar 首帧主题完整）。组件侧契约：TableWidget `apply_theme()` 基于 `draw()` 缓存（`_last_records/_last_today`）重渲染行内颜色、**不重新取数**；CraftingPage 为显式空实现（样式全部由 QSS 选择器驱动）；ProfitPage 扇出 crafting + exchange 两子页。

---

### 4.7 `calculator.py` — 业务逻辑（<!--AUTO:lines:calculator.py-->~500 行<!--/AUTO-->）

#### 类：`DayRecord` (frozen dataclass)

| 属性 | 类型 | 说明 |
|------|------|------|
| `cash` | float | 当前现金 |
| `warehouse` | float | 仓库价值（含现金） |
| `date` | str | 日期 YYYY-MM-DD |

#### 类：`ProfitCalculatorLogic`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.__init__-->`__init__`<!--/AUTO--> | `data: dict` | — | 解析并持有 `dict[str, DayRecord]`（兼容裸 dict / 已解析 dict；加载时跳过损坏条目并记 warning，ADR-0001——下次保存不再写回，自愈清除） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.get_record-->`get_record`<!--/AUTO--> | `date_str: str` | `DayRecord \| None` | 一行查询；不存在返回 None（非法条目已由加载时解析过滤） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.save_record-->`save_record`<!--/AUTO--> | `date_str, cash, warehouse` | `DayRecord` | 保存某日记录（内部存 DayRecord 实例）；cash/warehouse 存储前舍入到 2 位小数（round，银行家舍入） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.serialize-->`serialize`<!--/AUTO--> | — | `dict` | 转磁盘持久化形态裸 dict（`{日期: {cash, warehouse}}`）；返回**新 dict**，与内部 data 断共享（ADR-0001） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.last_record_before-->`last_record_before`<!--/AUTO--> | `date_str, max_days=365` | `(str, DayRecord) \| None` | 向前回溯最近有效记录（跳过空/无效日） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.recent_records-->`recent_records`<!--/AUTO--> | `days=7` | `list[(str, DayRecord)]` | 最近 days 条实际录入记录（录入条数语义，无空位占位），按日期升序 |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.calculate_rate-->`calculate_rate`<!--/AUTO--> | `prev_warehouse, current_warehouse` | `float \| None` | 计算收益率百分比，前值 None 或为零返回 None |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.is_cash_under_warehouse-->`is_cash_under_warehouse`<!--/AUTO--> | `cash, warehouse` | `bool` | 现金⊆仓库不变式判定（唯一所有者 D-05，告警/拦截/红框三处共用） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.cash_summary-->`cash_summary`<!--/AUTO--> | `days=7` | `(int, float \| None)` | 最近 days 条记录现金总变化（最新−最旧现金，与 summary 同窗口语义，随视图 7/30 联动） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.delete_record-->`delete_record`<!--/AUTO--> | `date_str: str` | `bool` | 删除单日记录，不存在返回 False |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.rotate_weekly-->`rotate_weekly`<!--/AUTO--> | `days=30` | `list[str]` | 保留最近 days 条实际录入记录（默认 RETENTION_LIMIT=30，J 系列：满上限不删、第 31 条才删最旧），超过上限删除最旧；返回被删除日期列表（升序，O-14） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.summary-->`summary`<!--/AUTO--> | `days=7` | `(int, float \| None)` | 最近 days 条记录总盈亏（最新−最旧，录入条数语义） |
| <!--AUTO:sig:calculator.py:ProfitCalculatorLogic.export_csv-->`export_csv`<!--/AUTO--> | — | `str` | 生成 CSV 导出文本（日期/现金/仓库/较前日/收益率，日期升序，O-04） |


### 4.8 `presentation.py` — 展示文本生成（<!--AUTO:lines:presentation.py-->~110 行<!--/AUTO-->）

领域值 → 展示文本 + 语义信号纯函数（架构评审候选 1/6，与 `calculator.py` 解耦）。

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| <!--AUTO:sig:presentation.py:format_rate-->`format_rate`<!--/AUTO--> | `rate: float | None` | `(str, RateSignal)` | 格式化收益率显示文本和颜色 |
| <!--AUTO:sig:presentation.py:format_signed_money-->`format_signed_money`<!--/AUTO--> | `value: float | None` | `(str, RateSignal)` | 带符号金额（较前日差值/总盈亏）：正数 `+¥...`、负数 `¥-...`、零 `¥0.00` 无前缀、None `---`（D-01） |
| <!--AUTO:sig:presentation.py:format_window_text-->`format_window_text`<!--/AUTO--> | `count, total, label, days=7` | `(str, RateSignal)` | 汇总标签文本纯函数（参数化版 #6：替代 format_summary + format_cash_summary）：数据不足/仅 1 条→NONE，>=2 条走 format_signed_money |
| <!--AUTO:sig:presentation.py:format_saved_indicator-->`format_saved_indicator`<!--/AUTO--> | `save_date, warehouse, today, deleted, keep_days=30` | `str` | 保存成功指示器文本纯函数（今日/已更新 + 轮转清理提示，D-07/J 系列） |
| <!--AUTO:sig:presentation.py:get_pnl_label-->`get_pnl_label`<!--/AUTO--> | `prev_warehouse, current_warehouse` | `(str, PnLSignal)` | 判断盈亏标签和颜色 |

**关键业务规则**：
- `data` 为 `dict[str, DayRecord]`（ADR-0001）；磁盘持久化走 `serialize()` 单向导出（返回新 dict，消灭 logic 与磁盘共享别名）；MainWindow 不直接触碰内部 data 形态
- 领域信号枚举 `RateSignal`/`PnLSignal` 定义于 `signals.py`（零依赖叶子）；业务层只返回语义信号，颜色映射留在 UI 层
- 加载时过滤的损坏/非法条目不再随 `serialize()` 写回——下一次保存会静默清除磁盘中的损坏数据（自愈）；记 warning 使行为可观测（O-01）
- 总收益 = 仓库价值（现金是仓库的组成部分）；不变式判定收敛于 `is_cash_under_warehouse`（D-05，告警/拦截/红框共用）
- 收益率 = `(今日warehouse - 前日warehouse) / 前日warehouse × 100%`，精度 1 位小数
- 盈亏标签：盈（绿底）/ 亏（红底）/ —（灰底，无前日数据或持平）
- 较前日差值 / 总盈亏展示统一走 `format_signed_money`：正数 `+¥…`、负数 `¥-…`、零 `¥0.00`（无 + 前缀）、无前值 `—`（D-01）
- CSV「较前日」= 当日仓库值 − 前一有记录日仓库值；无前日数据为 `—`；总收益 = 仓库已含现金

---

### 4.9 `config.py` — 基础配置（<!--AUTO:lines:config.py-->~41 行<!--/AUTO-->）

| 常量 | 值 | 说明 |
|------|-----|------|
| `APP_DIR` | Path | 应用所在目录（打包版为 exe 目录，源码版为项目根）；O-22 起仅作「旧数据源」供一次性迁移 |
| `DATA_DIR` | `Path.home()/Delta Force Dashboard` | 统一数据目录（开发版与 exe 共用，O-22） |
| `DATA_FILE` | `DATA_DIR/data.json` | 数据文件路径 |
| `BACKUP_FILE` | `DATA_DIR/data.json.bak` | 备份文件基础路径 |
| `SETTINGS_FILE` | `DATA_DIR/settings.json` | 设置文件路径 |
| `LOG_FILE` | `DATA_DIR/delta_force_dashboard.log` | 日志文件路径 |
| `DATE_FORMAT` | `"%Y-%m-%d"` | 日期格式 |
| `WEEK_DAYS` | `7` | 视图默认窗口（启动默认 7，录入条数语义；J 系列与保留上限解耦） |
| `RETENTION_LIMIT` | `30` | 存储保留上限（`rotate_weekly` 默认值；满 30 不删、第 31 条才删最旧，J 系列） |

> 主题色板（`THEMES` / `get_theme` / `set_theme` / `get_color`）已于 T-02 迁至 `app/theme.py`（见 §4.6），config.py 不再包含主题数据。

---

### 4.10 `data_store.py` — 数据持久化（<!--AUTO:lines:data_store.py-->~154 行<!--/AUTO-->）

#### 类：`DataStore`

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:data_store.py:DataStore.__init__-->`__init__(data_file=DATA_FILE, backup_file=BACKUP_FILE, max_backups=3)`<!--/AUTO--> | 初始化存储路径和备份数量 |
| <!--AUTO:sig:data_store.py:DataStore.load-->`load()`<!--/AUTO--> | 加载数据：主文件 → 损坏则依次尝试 bak.1 → bak.2 → bak.3 → bak → 空字典 |
| <!--AUTO:sig:data_store.py:DataStore.save-->`save(data)`<!--/AUTO--> | 保存数据：滚动备份 → 原子写入 |
| <!--AUTO:sig:data_store.py:DataStore._try_load-->`_try_load(path)`<!--/AUTO--> | 安全读取 JSON 文件，损坏返回 None |
| <!--AUTO:sig:data_store.py:DataStore._atomic_write-->`_atomic_write(data, target)`<!--/AUTO--> | 原子写入：先写 `.tmp`，再 `os.replace` 覆盖 |
| <!--AUTO:sig:data_store.py:DataStore._rotate_backups-->`_rotate_backups()`<!--/AUTO--> | 滚动备份：bak.2→bak.3, bak.1→bak.2, 当前→bak.1 + bak；复制失败记日志不中断（O-01） |

**关键机制**：
- **原子写入**：`.tmp` → `os.replace`，保证写入过程中进程崩溃不会损坏原文件
- **滚动备份**：最多保留 3 份历史备份（`data.json.bak.1` 为最新）
- **兼容性**：同时保留旧版单文件 `.bak`（与 `.bak.1` 内容相同）
- **损坏恢复**：主文件 JSON 解析失败时自动从最近可用备份恢复，全部损坏则返回空字典
- **日志**：备份复制失败仅记 `logger.warning`，不影响主流程保存（O-01）

#### 模块级迁移函数（O-22 / F-02）

| 名字 | 说明 |
|------|------|
| <!--AUTO:sig:data_store.py:migrate_legacy_data-->`migrate_legacy_data(legacy_dir, target_dir)`<!--/AUTO--> | 旧数据目录一次性迁移到统一目录；复制非移动、目标已有 `data.json` 跳过、失败仅 warning；成功后写 `.migrated` 完成标记（目标已权威也补写，幂等） |
| `MIGRATED_MARKER_NAME` | `.migrated` 完成标记文件名（写入目标数据目录） |
| <!--AUTO:sig:data_store.py:log_legacy_cleanup_hint-->`log_legacy_cleanup_hint(legacy_dir, target_dir)`<!--/AUTO--> | `.migrated` 标记存在且旧源 `data.json` 仍在时打 info 日志「旧数据源可手动清理」；绝不删源 |

**源清理策略（F-02）**：源清理时间点 = 目标数据确认健康之后，由用户确认后手动执行。脚本绝不自动删源；删除必须是用户确认的手动动作。

---

### 4.11 `formatting.py` — 金额格式化工具（<!--AUTO:lines:formatting.py-->~116 行<!--/AUTO-->）

| 函数 | 说明 |
|------|------|
| <!--AUTO:sig:formatting.py:format_compact-->`format_compact(value, *, prefix='')`<!--/AUTO--> | 紧凑 K/M/B 财务单位（SI 阈值 K≥1e3/M≥1e6/B≥1e9，低于 1e3 整数）；图表 Y 轴刻度与 hover/端点标注共用（D-01 收敛点） |
| <!--AUTO:sig:formatting.py:format_short_date-->`format_short_date(date_str)`<!--/AUTO--> | 完整日期 `YYYY-MM-DD` 截取为短格式 `MM-DD`（表格/图表标题展示用） |
| <!--AUTO:sig:formatting.py:format_money-->`format_money(value)`<!--/AUTO--> | 格式化显示：None→"—"，<1M→`¥x,xxx.xx`，≥1M→`¥x,xxx.xK`，≥100M→`¥x,xxx.xM` |
| <!--AUTO:sig:formatting.py:parse_money_input-->`parse_money_input(text)`<!--/AUTO--> | 解析输入：支持 `¥/￥/$`、千分位逗号、`K/M/B` 后缀、负号、空格；空值返回 None；非法格式抛 ValueError |
| <!--AUTO:sig:formatting.py:is_valid_money_input-->`is_valid_money_input(text)`<!--/AUTO--> | 校验输入合法性（空字符串为合法占位） |
| <!--AUTO:sig:formatting.py:format_input_value-->`format_input_value(value)`<!--/AUTO--> | 输入框失焦时格式化（调用 `format_money`） |
| <!--AUTO:sig:formatting.py:unformat_input_value-->`unformat_input_value(text)`<!--/AUTO--> | 输入框聚焦时反格式化：`¥1,234.56` → `1234.56`，尾零去除 |
| <!--AUTO:sig:formatting.py:_normalize_numeric_string-->`_normalize_numeric_string(text)`<!--/AUTO--> | 去除货币符号、逗号、空格，保留 `0-9`、`.`、`-` |
| <!--AUTO:sig:formatting.py:_strip_invisible-->`_strip_invisible(text)`<!--/AUTO--> | 移除 Unicode 不可见字符（零宽空格、BOM 等） |

**单位后缀映射**（大小写不敏感）：
- `K` → ×1,000
- `M` → ×1,000,000
- `B` → ×1,000,000,000

---

### 4.12 `json_file.py` — JSON 原子写 seam（D-02，<!--AUTO:lines:json_file.py-->~71 行<!--/AUTO-->）

| 函数 | 说明 |
|------|------|
| <!--AUTO:sig:json_file.py:atomic_write_json-->`atomic_write_json(path, data)`<!--/AUTO--> | 原子写入：先写 `.tmp` 再 `os.replace`；失败清理临时文件并抛出 OSError，由调用方决定告警/降级 |
| <!--AUTO:sig:json_file.py:try_load_json-->`try_load_json(path, on_error=None)`<!--/AUTO--> | 容错读取：返回解析值（形状校验交由调用方）；文件缺失/解析失败返回 None；解析/IO 失败时若提供 `on_error`，以实际异常为参数调用（供调用方恢复带异常详情的告警） |

**范围**：通用 JSON 持久化 seam（当前消费方为 `SettingsStore`）。`DataStore` 保留其更丰富的写路径（滚动备份 + 损坏恢复），未改用本 seam；**CSV 不走本 seam**（CSV 是导出格式而非持久化状态，D-02 拍板）。

---

### 4.13 `settings_store.py` — 设置持久化（D-02，<!--AUTO:lines:settings_store.py-->~108 行<!--/AUTO-->）

#### 类：`SettingsStore`

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:settings_store.py:SettingsStore.__init__-->`__init__(settings_file=SETTINGS_FILE)`<!--/AUTO--> | 设置文件路径 |
| <!--AUTO:sig:settings_store.py:SettingsStore.load-->`load()`<!--/AUTO--> | 容错读：文件缺失 → `{}`（首次运行静默）；解析失败 → warning（含异常详情，D-02 前逐字文案）+ `{}`；顶层非 dict → warning + `{}` |
| <!--AUTO:sig:settings_store.py:SettingsStore.save-->`save(settings)`<!--/AUTO--> | 经 `atomic_write_json` 原子落盘；失败仅记 warning，不抛异常（不阻断关窗/切换主题）；保留为原语，`update` 内部复用 |
| <!--AUTO:sig:settings_store.py:SettingsStore.update-->`update(patch)`<!--/AUTO--> | **C3-10** schema 合并写入：读当前文件原始 dict → 合并 patch（未知键保留）→ 原子写 → 返回新 dict；写失败 warning 不抛（容错语义与 save 一致） |

**职责边界（C3-10/C3-11）**：SettingsStore 是设置 schema 的唯一所有者——公开 `DEFAULTS`（`geometry`/`pinned`/`theme`/`animations`）与 `KNOWN_KEYS = frozenset(DEFAULTS) | {"current_account"}`；`update(patch)` 取代全量覆盖写（未知键端到端保留）。C3-11：`animations` 键纳入持久化闭环（启动值即运行值写回，关窗后动画开关不丢）；窗口层设置键收敛为 `_KEY_*` 模块常量（消灭裸字符串键，AST 守卫）；`encode_settings` 降级为模块私有 `_encode_window_state`。MainWindow 只保留「编码/解码」（窗口状态 ↔ dict），文件 I/O 全部收敛到此处。

---

### 4.14 `signals.py` — 领域信号枚举（<!--AUTO:lines:signals.py-->~23 行<!--/AUTO-->）

| 枚举 | 说明 |
|------|------|
| `RateSignal` | 收益率信号：`POSITIVE`/`NEGATIVE`/`NEUTRAL`/`NONE`；由 `format_rate`/`format_signed_money`/`format_summary` 返回，`theme.signal_color` 据此映射主题色（D-01） |
| `PnLSignal` | 盈亏信号：`盈`/`亏`/`平`/`无`；由 `get_pnl_label` 返回，`table_widget._PNL_TO_KEY` 据此映射盈亏标签颜色 |

**定位**：零依赖底部叶子（仅标准库），任何层可安全导入——解决 D-01 后 `theme.py` 反向依赖 `calculator` 的层反转（D 系列评审修正）；颜色值不在此定义，永远留在 UI 层。

---

### 4.15 `account_store.py` — 多账号存储层（Y 系列，<!--AUTO:lines:account_store.py-->~196 行<!--/AUTO-->）

**布局约定（ADR-0005）**：`accounts/<账号名>/data.json`，目录名即账号名，无 `accounts.json` 元数据文件；每账号复用 `DataStore(data_file, backup_file)` 路径注入，原子写 / 损坏恢复 / 滚动备份全部继承。UI 层不得直接拼装账号路径——所有账号文件系统操作收敛到本模块。

| 常量 | 值 | 说明 |
|------|-----|------|
| `DEFAULT_ACCOUNT_NAME` | `"主账号"` | 默认账号：首次升级 / 兜底回退落点（H1 共识） |
| `ACCOUNTS_DIR_NAME` | `"accounts"` | 账号根目录名（位于统一数据目录 DATA_DIR 下） |
| `MIGRATED_V2_MARKER_NAME` | `".migrated_v2"` | v2 迁移完成标记（存在即跳过，幂等） |
| `MAX_ACCOUNT_NAME_LEN` | `64` | 账号名长度上限（F1 评审修复，远小于 Windows 255 单目录名上限） |

#### 函数：`validate_account_name(name)`

| 函数 | 说明 |
|------|------|
| <!--AUTO:sig:account_store.py:validate_account_name-->`validate_account_name(name)`<!--/AUTO--> | 校验账号名：合法返回 None，否则返回可读拒绝原因——非文本 / 空名 / 控制字符（ord<32，F1）/ 超 64 字符 / 含 `\ / : * ? " < > \|` / 首尾空格或点；中文 / 数字 / 中间空格合法 |

#### 类：`AccountStore`

| 方法 | 说明 |
|------|------|
| <!--AUTO:sig:account_store.py:AccountStore.__init__-->`__init__(accounts_dir)`<!--/AUTO--> | 账号目录路径（测试显式注入 tmp_path，生产默认 `DATA_DIR/accounts`） |
| <!--AUTO:sig:account_store.py:AccountStore.list_accounts-->`list_accounts()`<!--/AUTO--> | 扫描 accounts 目录返回账号名列表（目录名=账号名，稳定排序）；目录缺失/空 → `[]`（不创建目录） |
| <!--AUTO:sig:account_store.py:AccountStore.create_account-->`create_account(name)`<!--/AUTO--> | 新建账号：成功返回 None / 拒绝返回可读原因（不产生任何目录）；新账号空数据起步（H5，只建目录不写 data.json）；mkdir OSError → warning + 可读原因（F1） |
| <!--AUTO:sig:account_store.py:AccountStore.resolve_account-->`resolve_account(current)`<!--/AUTO--> | 解析当前账号：current 缺失/非字符串/目录不存在/目录名非法（F3）→ 回退主账号并自建空目录（H3）；accounts 空 → 自动建主账号 |
| <!--AUTO:sig:account_store.py:AccountStore.account_dir-->`account_dir(name)`<!--/AUTO--> | 账号目录路径（业务层唯一拼装点，UI 禁止直接拼装） |
| <!--AUTO:sig:account_store.py:AccountStore.new_store-->`new_store(name)`<!--/AUTO--> | 以账号路径注入构造 DataStore（原子写 / 损坏恢复 / 滚动备份全继承） |
| <!--AUTO:sig:account_store.py:AccountStore.migrate_legacy_to_default-->`migrate_legacy_to_default(data_dir=None)`<!--/AUTO--> | v2 旧数据迁移（Y-02）：accounts/ 不存在 **且** 旧 data.json 存在 → 复制 data.json + 全部 `data.json.bak*` 到 accounts/主账号/ 并写 `.migrated_v2`；accounts/ 已存在（含空）/marker 存在 → 跳过；复制非移动、永不删源（O-22 铁律）；OSError → warning 不中断不写 marker；data_dir 缺省 = accounts_dir 父目录（生产 DATA_DIR），测试显式注入 |

**main.py 接线（Y-02）**：v2 迁移在 O-22 `migrate_legacy_data` 之后、MainWindow 构造之前（AST 顺序断言防复发）。

---

### 4.16 `kkrb_client.py` — kkrb.net API 客户端（L-02/V-01，<!--AUTO:lines:kkrb_client.py-->~149 行<!--/AUTO-->）

kkrb.net API 客户端：会话（CSRF 握手：首页 → getMenu → cookie 提取）/ HTTP 传输 / TTL 缓存三合一，纯 stdlib 零外部依赖；数据入口 `fetch_ov_data()` / `fetch_ammo_package_data()`；解析收敛于 `kkrb_models` / `kkrb_parsing`（V-01），本模块只留会话 / 传输 / 缓存。

**C2-01 并发契约**：`__init__` 持有 `threading.Lock`；`_post_json` 对「缓存检查 → 握手 → 请求 → 缓存写入」**整体持锁**（`_ensure_csrf` 仅在本方法内被调用，无锁内重入），保证共享 client 被多后台线程并发调用时握手恰一次、缓存无脏读（C2-02 共享 client 的必要前提）。`reset()` 清会话与缓存（无锁，当前无生产调用点——AA-03 注记）。

---

### 4.17 `app/fetch_page_base.py` — 数据页公共基类（T-03/V-02/C2，<!--AUTO:lines:app/fetch_page_base.py-->~171 行<!--/AUTO-->）

CraftingPage / ExchangePage 共享基类（模块 docstring 见文件头）：showEvent 懒加载、LoadState 四态状态机（V-02）、FetchWorker 后台取数（T-01）、refresh / preload / shutdown 生命周期。

**C2 契约**：
- **C2-02 注入 seam**：`__init__(parent=None, client=None)`——`client` 为 None → 自建 `KkrbClient()`（生产唯一创建点在 MainWindow），测试经构造注入 stub client 即「断网」；
- **C2-03 删哨兵**：`preload()` 不再读取 `QT_QPA_PLATFORM` 环境变量——测试模式靠构造注入压制网络（`tests/conftest.make_stub_client`），offscreen 哨兵已删除；
- **C2-05 错误/空态分离**：`_render_error()` 钩子（默认实现 = 空态渲染，与既有 `_on_fetch_error` 行为逐字节等价）；`_on_fetch_error` = status label 逻辑（KkrbError/非 KkrbError 文案 + 点击重试）+ `self._render_error()`；CraftingPage 覆盖为「加载失败，点击重试」卡片，与空态「暂无数据」可区分；
- **单出口**：`ProfitPage` 在父层扇出 `preload()` / `apply_theme()`（C2-02 / C1-07），页面外部不再直插子页方法。

---

## 五、依赖关系

### 5.1 外部依赖

| 包 | 版本要求 | 用途 |
|-----|----------|------|
| PySide6 | ==6.11.1 | Qt 官方 Python 绑定，UI 框架 |
| pyqtgraph | ==0.14.0 | 高性能 Qt 原生图表渲染 |
| numpy | (pyqtgraph 的传递依赖) | 数值计算（图表数据） |
| pytest | ==9.1.1（requirements-dev.txt） | 单元测试框架（<!--AUTO:tests_total:total-->527<!--/AUTO--> 项，含制造产物推荐 + 兑换利润） |

### 5.2 模块间依赖关系图

```
main.py
  └── app/main_window.py
        ├── app/input_panel.py ──┐
        ├── app/table_widget.py  ├── formatting.py
        ├── app/chart_widget.py  │
        ├── app/theme.py ────────┼── signals.py
        ├── data_store.py ───────┼── config.py
        ├── settings_store.py ───┼── json_file.py, config.py
        ├── json_file.py          （无外部依赖）
        ├── calculator.py ───────┼── config.py, formatting.py, signals.py
        ├── signals.py            （无外部依赖，共享叶子）
        └── config.py
```

### 5.3 导入清单

| 模块 | 导入来源 |
|------|----------|
| `main.py` | `app.main_window`, `config`, `PySide6`（QtCore/QtGui/QtNetwork/QtWidgets） |
| `app/main_window.py` | `app.input_panel`, `app.table_widget`, `app.chart_widget`, `app.theme`, `config`, `data_store`, `settings_store`, `formatting`, `calculator`, `signals`, `PySide6` |
| `app/input_panel.py` | `app.theme`, `formatting`, `calculator`, `PySide6` |
| `app/table_widget.py` | `app.theme`, `formatting`, `calculator`, `signals`, `PySide6` |
| `app/chart_widget.py` | `app.theme`, `formatting`, `pyqtgraph`, `PySide6` |
| `app/theme.py` | `signals`（`RateSignal`，零依赖叶子） |
| `calculator.py` | `config`, `formatting` |
| `account_store.py` | `config`, `data_store` |
| `presentation.py` | `config`, `formatting`, `signals` |
| `data_store.py` | `config` |
| `settings_store.py` | `json_file`, `config` |
| `json_file.py` | 无外部依赖（仅标准库） |
| `signals.py` | 无外部依赖（仅标准库） |
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
- 最多保留最近 30 条记录（超出删除最旧，按记录数而非日历天数）

### 6.2 `settings.json` 格式

```json
{
  "geometry": "hex-encoded QByteArray",
  "pinned": false,
  "theme": "light",
  "current_account": "主账号"
}
```

- `current_account`（Y-03）：最近使用的账号名，启动时经 `AccountStore.resolve_account` 解析（缺失/非法/目录不存在 → 回退主账号）；注入模式（测试）不写此 key
- 账号数据存储于 `DATA_DIR/accounts/<账号名>/data.json`（ADR-0005，目录名即账号名）

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
| `tests/test_calculator.py` | <!--AUTO:tests:tests/test_calculator.py-->81<!--/AUTO--> | DayRecord 字段/冻结、CRUD、日期回溯、记录滚动（recent_records/rotate_weekly）、收益率计算、格式化、盈亏标签、删除、滚动旋转（含删除日志 O-14）、汇总、CSV 导出（含金额统一格式化 O-11）、现金>仓库保存告警（O-08）、带符号金额 format_signed_money（D-01）、现金⊆仓库谓词 is_cash_under_warehouse（D-05）、汇总/保存指示器纯函数 format_summary/format_saved_indicator（D-07）、加载跳过记录 warning |
| `tests/test_presentation.py` | <!--AUTO:tests:tests/test_presentation.py-->23<!--/AUTO--> | 展示文本生成纯函数（format_rate / format_signed_money / format_window_text / format_saved_indicator / get_pnl_label，D-01/D-07 架构评审候选 1） |
| `tests/test_data_store.py` | <!--AUTO:tests:tests/test_data_store.py-->18<!--/AUTO--> | 空加载、保存/加载回环、备份创建、备份编号、滚动旋转、主文件损坏恢复、滚动备份恢复、全部损坏恢复、原子写入无残留、Unicode 支持、备份失败日志、顶层 list 视为损坏（O-09） |
| `tests/test_account_store.py` | <!--AUTO:tests:tests/test_account_store.py-->52<!--/AUTO--> | 多账号存储层（Y-01）：list_accounts 目录扫描、create_account 校验拒绝（空/重名/禁用字符/首尾空格或点/非文本）、resolve_account 兜底回退主账号 + 空库自建、DataStore 路径注入继承（账号隔离/损坏恢复/滚动备份）、全新环境首次运行 |
| `tests/test_formatting.py` | <!--AUTO:tests:tests/test_formatting.py-->58<!--/AUTO--> | 格式化（各种量级/零/负/None）、输入解析（纯数字/逗号/¥/￥/$/后缀/空格/非法格式）、校验边界、焦点格式化/反格式化 |
| `tests/test_settings_store.py` | <!--AUTO:tests:tests/test_settings_store.py-->34<!--/AUTO--> | json_file seam（原子写/容错读/失败清理）+ SettingsStore（缺失静默/损坏告警/非 dict 兜底/原子落盘/失败不抛，D-02）+ on_error 回调/读取失败异常详情回归 |
| `tests/test_json_file.py` | <!--AUTO:tests:tests/test_json_file.py-->3<!--/AUTO--> | json_file seam（D-02）：原子写（失败清理临时文件）/ 容错读（缺失/解析失败返回 None）/ on_error 回调异常详情 |
| `tests/test_migration.py` | <!--AUTO:tests:tests/test_migration.py-->14<!--/AUTO--> | 旧数据一次性迁移（O-22：幂等跳过/复制非移动/失败 warning）+ `.migrated` 完成标记与清理提示（F-02）+ main() mkdir 顺序回归 |
| `tests/test_doc_sync.py` | <!--AUTO:tests:tests/test_doc_sync.py-->1<!--/AUTO--> | F-01 冒烟：运行 `python scripts/doc_sync.py --check` 断言通过（CODE_WIKI 基线同步锁死） |
| `tests/test_chart_geometry.py` | <!--AUTO:tests:tests/test_chart_geometry.py-->6<!--/AUTO--> | 图表几何纯函数 adaptive_range：正常范围/单值/空列表/负值/全同值（rng==0 分支） |

**运行方式**：在项目根目录执行 `pytest`

### 7.2 UI 烟测（pytest offscreen）

UI 烟测并入 pytest（C5 迁移，2026-08-01 删除影子脚本 `verify_all.py`），
offscreen 模式下覆盖原 14 个模块中的 UI 部分：

| 测试文件 | 用例数 | 覆盖范围 |
|----------|--------|----------|
| `tests/test_ui_smoke.py` | <!--AUTO:tests:tests/test_ui_smoke.py-->95<!--/AUTO--> | UI 启动/渲染、保存、编辑、删除（确认/取消）、主题切换、窗口置顶、设置持久化、几何恢复（兼容旧 Tkinter 格式）、输入校验联动（D-04 真实事件链路）、快捷键（Enter/Esc）、CSV 导出按钮、今日未录入提醒、图表稀疏提示（O-06）、编辑态关窗确认（O-13）、自动清理提示（O-14）；Y 系列账号（Y-03 解析链路/兜底/落盘回读、Y-04 账号区初始态/新建/非法名拒绝/注入隐藏、Y-05 切换刷新/重启回读/编辑复用态取消/保存删除 CSV 落新账号/同账号 no-op） |
| `tests/test_kkrb_client.py` | <!--AUTO:tests:tests/test_kkrb_client.py-->28<!--/AUTO--> | 数据模型 + OV 响应解析 |
| `tests/test_fetch_pages.py` | <!--AUTO:tests:tests/test_fetch_pages.py-->30<!--/AUTO--> | T-01 FetchWorker shutdown/超时逃生舱托管/关窗不崩溃 + T-02 preload 幂等/构造注入 stub client（C2 删 offscreen 哨兵）/失败日志 + T-03 基类提炼后懒加载/渲染/主题色收敛/_error 死状态移除；C2 起：共享 client 并发、_render_error 错误态 |
| `tests/test_input_panel.py` | <!--AUTO:tests:tests/test_input_panel.py-->22<!--/AUTO--> | InputPanel getter 语义 / raw getter / 校验真实事件链路与焦点链路（D-04：聚焦反格式化护栏、失焦立即校验、失焦格式化）/ refresh_validity 同步 seam 契约 / 编辑状态归属 / C9 静态守卫 / save_today 走公开 API / cash≤warehouse 不变式警告与保存拦截（O-08） |
| `tests/test_table_theme.py` | <!--AUTO:tests:tests/test_table_theme.py-->8<!--/AUTO--> | 表格主题色实时解析（非 import 期冻结）+ AST 防复发 + D-01 零差值 |

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
python -m PyInstaller delta_force_dashboard.spec --noconfirm
```

**产物**（O-20 起为 onedir）：`dist/Delta Force Dashboard/Delta Force Dashboard.exe` + `dist/Delta Force Dashboard/_internal/`。整目录分发或 zip 压缩，双击 exe 即运行；运行态数据（`data.json`/`settings.json`/日志）统一生成在用户目录 `~/Delta Force Dashboard`（O-22），与 exe 位置/重建解耦——`dist/` 每次构建整体覆盖也不影响用户数据。旧版 exe 目录/项目根内的数据在首次启动时由 `migrate_legacy_data` 自动复制（复制非移动，源保留）。迁移完成后写 `.migrated` 完成标记（F-02）；启动时若标记存在且旧源 `data.json` 仍在，打 info 日志提示「旧数据源可手动清理」。**源清理时间点 = 目标数据确认健康之后，用户确认后手动执行**：应用绝不自动删源，删除是用户确认的手动动作。

**为什么是 onedir 而非单文件**（O-20）：单文件模式每次启动需把整包解压到 `%TEMP%\_MEI*`（实测 181MB），是启动慢（~2-4s）的根因；onedir 免解压，冷启动实测 ~1.5s。`config.APP_DIR`（`sys.executable`）与 `main._icon_path`（`sys._MEIPASS`）在 onedir 下行为一致；O-22 后运行态数据不再依赖 `APP_DIR`，改走 `DATA_DIR`（`Path.home()/Delta Force Dashboard`）。

**体积瘦身**（O-20，80MB 单文件 → 117MB 目录）：spec 内 `excludes` 剔除 matplotlib/PIL 及其纯 Python 依赖（pyqtgraph 的 Matplotlib 导出器运行时从不加载，importtime 实测）；Qt 二进制白名单过滤（bindepend 校验依赖闭包后，仅保留 Core/Gui/Widgets/Network/OpenGL/OpenGLWidgets/Svg/Test——后二者为 pyqtgraph import 时实际加载）；剔除全部 Qt translations（应用不装 QTranslator，文案硬编码中文）；剔除 opengl32sw.dll 软件渲染器（从不创建 GL 上下文）与 tls/networkinformation 插件。`upx=False`（本机未装 UPX，此前为空转）。

**图标**：`delta_force_dashboard.spec` 中 `EXE(icon='app_icon.ico')` 设置 exe 文件图标；`datas=[('app_icon.ico', '.')]` 将图标随包内嵌，供 `main.py` 的 `setWindowIcon` 运行时加载（窗口/任务栏图标）。源码版从项目根目录读取同一文件（`_icon_path()`）。

### 8.5 文档同步（F-01）

`CODE_WIKI.md` 中的四类机械标记（§4 各模块 `（~N 行）`、§7 各测试文件用例数、§4 方法表签名、头部横幅/属性表/依赖表的测试总数 `tests_total`）由 `scripts/doc_sync.py` 从代码生成，**修改代码后需运行它保持同步**：

```bash
python scripts/doc_sync.py               # 就地刷新所有现有标记（不新增标记）
python scripts/doc_sync.py --check       # 校验；有漂移则 exit 1（pre-commit 钩子调用）
python scripts/install-hooks.bat         # 安装 pre-commit 钩子到 .git/hooks（换机器需重装）
```

钩子在每次 commit 前自动跑 `--check`，漂移即拦截提交。**边界**：工具只维护「数字/签名」类机械标记，不生成叙述性文字（F-01 规模悖论）；新增测试文件 / 新增 §4 模块标题时需在 CODE_WIKI 手动补对应标记，`--check` 会提示缺失。

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
| 10 | 记录保留/视图 | 存储保留 30 条 + 视图 7/30 可切换（解耦） | 切回 7 不丢数据；单一按钮组驱动表格/图表/汇总同变（ADR-0003） |

---

## 十、常见注意事项

1. **主题切换**：运行时必须用 `get_color(key)` 而非模块级常量，因为常量在 `import` 时固定为 light 主题
2. **现金⊆仓库不变式**：判定收敛于 `ProfitCalculatorLogic.is_cash_under_warehouse()`（告警/拦截/红框三处共用，D-05）；总收益 = 仓库价值（已含现金），非 `warehouse + cash`
3. **保留条数限制**：`ProfitCalculatorLogic.rotate_weekly()` 在每次 `save_today()` 后执行，按「录入条数」超过保留上限 `RETENTION_LIMIT=30` 时从最旧开始删除（满 30 不删、第 31 条才删）；表格/图表/汇总（`recent_records`/`summary`）同以当前视图 7/30 条实际录入记录为基准（随按钮组切换，Q5 存储与视图解耦），而非日历天
4. **编辑模式**：编辑回填时使用 `unformat_input_value()` 转为纯数字，保存时用原日期覆盖写入
5. **图表更新**：`_update_chart()` 使用持久化的 `PlotCurveItem` + `FillBetweenItem`，仅 `setData()` 更新，避免重建
6. **输入框去抖**：`MoneyLineEdit` 使用 150ms 去抖的 QTimer，快速输入时避免每次按键都触发校验
7. **DPI 感知**：Windows 下通过 `SetProcessDpiAwareness(1)` 配合 `Qt.HighDpiScaleFactorRoundingPolicy.PassThrough`
8. **几何格式兼容**：`_setup_window()` 同时兼容新格式（hex QByteArray）和旧格式（Tkinter `WxH+X+Y` 字符串）

---

*本文档由 AI 基于项目源码自动生成，覆盖所有模块、类、函数及关键实现细节。*
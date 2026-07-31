# DEV_LOG — 收益计算器开发日志

> **格式**：`YYYY-MM-DD` | `<操作>` | `<范围>` | `<描述>`
>
> 按时间倒序排列，最新条目在最前。

---

### 2026-07-31 | C6 | 全项目 | 浅层残留清扫

**变更**：
- 删除 `app/config.py` 空壳文件（grep 全仓确认零引用）
- `config.py`: 删除 7 个无消费者的 `FONT_*` 元组常量，docstring 同步（`WEEK_DAYS` 等保留）
- `calculator.py`: `PnL信号` → `PnLSignal`（Serena rename_symbol，全仓 3 文件同步）
- `formatting.py`: `unformat_input_value` 死分支清理（`f"{v:.2f}"` 恒含小数点，三元 `else` 不可达）
- 死 import 清理 6 文件：`main_window.py`（QTimer/QFont/QSizePolicy/QSpacerItem/APP_DIR/get_theme）、`chart_widget.py`（os/numpy/QFont/QHBoxLayout/QSizePolicy/get_theme）、`input_panel.py`（QSizePolicy/get_theme/format_money + 4 个死 `FONT_*` 本地常量）、`table_widget.py`（QSizePolicy）、`calculator.py`（format_money）、`verify_all.py`（traceback/patch/QTimer/get_color/get_theme/set_theme/DayRecord）
- `CODE_WIKI.md`: 删除 config.py 常量表 FONT_* 行（含已迁走的 THEMES 行）

**验证**：pytest 134/134 ✅ | verify_all 通过（同 4 项既有基线失败）| AST 扫描无残留死 import

---

### 2026-07-31 | C7~C9 | app/input_panel.py + verify_all.py + tests | C4 评审后续三项

**变更**：
- **C7**（docstring 契约修正）：`get_cash_value()`/`get_warehouse_value()` docstring 改为「结构性非法数字抛 ValueError；清洗后为空的文本（如 `'abc'`）返回 None」——与 `parse_money_input` 实际语义对齐，消除「空输入」与「垃圾输入」的 docstring 误导
- **C8**（检查标签改名）：`verify_all.py` `test_edit_mode` 两条 check 标签 `_editing_date` → `get_editing_date()`，不再指向已删除的 `MainWindow._editing_date` 实现细节
- **C9**（seam 静态守卫）：新增 `test_main_window_has_no_direct_entry_access`——AST 扫描 `main_window.py` 源码，断言无 `cash_entry`/`warehouse_entry` 直取、无 `parse_money_input` 调用，即使行为等价测试回归也会被拦截

**验证**：pytest 134/134 ✅（新增 1 项）| verify_all 通过（同 4 项既有基线失败）

---

### 2026-07-31 | C4 | app/input_panel.py + app/main_window.py + verify_all.py + tests | InputPanel seam 成真

**变更**：
- `app/input_panel.py`:
  - `get_cash_value()` / `get_warehouse_value()` 语义明确为「空输入 → None，非法 → 抛 ValueError」（原先吞掉 ValueError 返回 None，区分不了空与非法；二者原无调用者，语义变更无外部影响）
  - 新增 `get_cash_raw()` / `get_warehouse_raw()` 原始文本 getter（供解析失败提示复用）
  - 新增 `refresh_validity()`（供 `MainWindow._clear_focused_input` 清空后立即重校验，替代直取两个 `cash_entry._update_validity()`）
- `app/main_window.py`: 收敛到公开 API，删除私有直取
  - `save_today` 改走 `get_cash_raw()` / `get_cash_value()` 等公开 getter（不再 `cash_entry.text()` + `parse_money_input`）
  - 删除 `self._editing_date` 字段——编辑状态单方归属 InputPanel，MainWindow 只查询 `is_editing()` / `get_editing_date()`
  - `_delete_record` 判断编辑目标改用 `input_panel.get_editing_date()`
- `verify_all.py`: `win._editing_date` ×2 → `win.input_panel.get_editing_date()`（适配新 API）
- `tests/test_input_panel.py`: 新增 9 项回归测试（getter 语义 / raw getter / refresh_validity / 编辑状态归属 / `hasattr` 防 `_editing_date` 复发 / save_today 走公开 API 行为等价）

**验证**：pytest 133/133（124 既有 + 9 新增）✅ | verify_all 通过（同 4 项既有基线失败，与本次无关）

---

### 2026-07-31 | 打包 | dist/收益计算器.exe | 重新打包（含 C3 收尾 `_UNITS` 重构）

**产物**：`dist/收益计算器.exe`（80 MB，单文件）

**验证**：
- pytest 124/124 通过 ✅
- exe 启动烟测通过（双进程常驻 → 单实例锁生效，强制结束后正常退出）✅

---

### 2026-07-31 | C3 收尾 | formatting.py + DEV_LOG | 单位↔因子对收敛为 `_UNITS` 共享表

**变更**：
- `formatting.py`: 新增私有升序表 `_UNITS = (("K", _K), ("M", _M), ("B", _B))`；
  `format_compact` 改 `reversed(_UNITS)` 反向迭代（大单位优先）、`parse_money_input`
  改正向迭代——消除两处内联 (后缀, 因子) 对，新增单位只需改一处（行为不变）
- `DEV_LOG`: C3 记录补记 hover 精度变化为已批准偏离（见 C3 条目说明）

**验证**：pytest 124/124 ✅ | 纯重构，无行为变化

---

### 2026-07-31 | C3 | formatting.py + app/*.py + tests | 收敛三套 K/M/B 格式化 + 日期短格式去重

**变更**：
- `formatting.py`: 新增共享单位常量 `_K/_M/_B` 与公开 `format_compact(value, *, prefix="")`
  （SI 阈值 K≥1e3 / M≥1e6 / B≥1e9，`.1f`，<1e3 整数）；`format_money` 与 `parse_money_input`
  改用同一常量（输出不变）
- `app/chart_widget.py`: `KMBAxisItem.tickStrings`（Y 轴，无前缀）与 `_ChartPanel._format_value`
  （hover/端点，`prefix="¥"`）委托给 `format_compact`——消除两处阈值/精度各自漂移
  （hover 原 `.2f`/`.1f` 混用 → 统一 `.1f`，符合「与 Y 轴一致」的原始意图）
- 日期截取 `date_str[-5:]` 在 4 文件 6 处重复 → 新增 `format_short_date()` 统一替换
  （`table_widget.py` ×3 / `main_window.py` ×2 / `chart_widget.py` ×1 / `input_panel.py` ×1）
- `tests/test_formatting.py`: 新增 format_compact ×7 + format_short_date ×1

**说明（含已批准偏离）**：相对工单提议有两处偏离，均已批准——
1. API 形状：提议 `format_compact(value, *, currency=False)` → 实现为更通用的 `prefix`
   字符串参数（轴无前缀、hover 带 ¥）
2. hover 精度：`_ChartPanel._format_value` 原 `.2f`/`.1f` 混用 → 统一 `.1f`
   （K/M 由 2 位降为 1 位，B 不变）——消除精度漂移并与 Y 轴一致

**验证**：pytest 124/124 ✅ | verify_all 无新增失败（仍为 4 项既有基线失败）| 提交 `e3eff63`

---

### 2026-07-31 | fix | verify_all.py | settings.json 污染修复：测试期间隔离真实设置文件

**症状**：跑完 `verify_all.py` 后 `settings.json` 被改写（theme/pinned/geometry 残留测试态），需手动 `git restore settings.json`

**根因**：每个 UI 测试 `win.close()` → `closeEvent()` → `_save_settings()` 写真实 `SETTINGS_FILE`；`test_theme_toggle` / `test_pin_toggle` 等未做临时替换，测试态主题被持久化（`test_settings_persistence` 虽已替换，但只在单测内局部生效）

**修复**：
- `main()` 启动时把 `app.main_window.SETTINGS_FILE` 重定向到 `tmp_dir/settings.json`，`finally` 中恢复引用——真实文件全程零读写，即使脚本被强杀也无污染窗口
- 附带收益：测试从「读用户真实设置」变为「确定性默认态」，`test_pin_toggle` 不再受用户已置顶状态影响
- 顺带删除 `verify_all.py` 死 import `from config import SETTINGS_FILE`（无引用）

**验证**：pytest 116/116 ✅ | verify_all 跑完 `git status` 无 `settings.json` / `data.json` 改动（同 4 项既有失败，与本次无关）

---

### 2026-07-31 | C2 | calculator.py + app/main_window.py + verify_all.py + tests | DayRecord 生命周期收敛到 logic 层

**变更**：
- `calculator.py`: `ProfitCalculatorLogic` 新增三个公共方法，成为工作 dict 的唯一所有者
  - `delete_record(date_str)` — 删除记录，返回是否存在
  - `rotate_weekly(days=WEEK_DAYS)` — 7 日保留策略（原 `MainWindow._rotate_weekly`）
  - `summary(end_date, days)` — 7 日窗口总盈亏算术（原 `_update_summary` 业务部分），返回 `(记录数, 总盈亏)`
- `app/main_window.py`: 视图减负，只做协调
  - 删除 `self.data` 持有与 `_rotate_weekly`；构造时经 `ProfitCalculatorLogic(self.store.load())` 一次注入数据对象
  - `save_today` / `_delete_record` 走 `logic.save_record` / `logic.rotate_weekly` / `logic.delete_record`，持久化改用 `store.save(logic.data)`
  - `_update_summary` 不再接收 records、不做算术，改为读取 `logic.summary()` 仅格式化展示
- `verify_all.py`: `win.data` → `win.logic.data`，`win._rotate_weekly()` → `win.logic.rotate_weekly()`（适配新 API）
- `tests/test_calculator.py`: 新增 10 项测试（delete_record ×2 / rotate_weekly ×2 / summary ×6）

**验证**：pytest 116/116 ✅ | verify_all 通过（同 4 项既有失败，与本次改动无关，已 A/B 确认基线一致）

**code-review（C2，双轴并行）**：
- ✅ Spec：8/8 需求全部落地，行为与重构前逐点等价（0→数据不足 / 1→仅1条 / ≥2→末日−首日）；"工作 dict 唯一所有者"成立（`main_window.py` 无残留 `self.data` 突变）；无循环 import
- ✅ Standards：无文档规范违规；`ProfitCalculatorLogic` 三新方法 type hints + docstring 齐全，UI/业务分离改善
- ⚠️ 待处理小项（judgement call）：
  1. `_update_summary` 引入 4 行重复块（`数据不足` 与 `仅1条` 两分支 setStyleSheet 相同）→ 可合并
  2. `PROJECT_REFERENCE.md:212` 仍引用已删除的 `MainWindow._rotate_weekly()`（同文件已改，漏网）
  3. `TO-TICKETS.md` 清空 T-01~T-05 工单体非 C2 规格要求（拟意清扫，待确认保留）
- 📌 工作区改动未提交（C2 + 文档 + TO-TICKETS 清理），待确认后 commit

---

### 2026-07-31 | 打包 | dist/收益计算器.exe | 重新打包（含 C1 主题色修复）

**产物**：`dist/收益计算器.exe`（83.3 MB，单文件）

**验证**：
- pytest 106/106 通过 ✅
- exe 启动烟测通过（进程正常常驻后强制结束）✅
- warn-收益计算器.txt 仅剩 Windows 无关的 POSIX 模块与可选 scipy 缺失，无实质风险

---

### 2026-07-31 | C1 | app/table_widget.py + tests/test_table_theme.py | 修复表格主题色 import 期冻结

**变更**：
- `app/table_widget.py`: 信号→颜色映射改为「信号→主题键」静态映射 + 渲染时 `get_color()` 解析
  - 删除模块顶层 `_SIGNAL_TO_COLOR` / `_PNL_TO_COLOR`（import 期调用 `get_color()`，颜色冻结为 light 色板——T-01 复发的同一 bug）
  - 新增 `_signal_color()` / `_pnl_color()` helper，draw() 内实时解析当前主题色
  - 左右栏标题 `_left_title` / `_right_title` 内联样式移入 draw()（原在 `__init__` 冻结主题色）
  - 删除死代码链：`_DaySubTable.apply_theme`（pass）与 `TableWidget.apply_theme`（无人调用；主题路径实为 `refresh_display → draw`）
- `tests/test_table_theme.py`: 新增 3 项回归测试（首个 Qt offscreen fixture）
  - 动态：dark 主题下收益率列前景色 == dark FG_POS（修前失败，修后通过）
  - 动态：light/dark 渲染颜色不同（证明无冻结）
  - 静态：AST 检查 table_widget 顶层（非函数体）无 `get_color()` 调用——防复发

**验证**：pytest 106/106（103 既有 + 3 新增）✅ | verify_all 通过（同 4 项既有失败，与本次改动无关）

---

### 2026-07-30 | ✅ T-05 | app/chart_widget.py | ChartWidget 拆分 `_ChartPanel`

**变更**：
- 新增 `_ChartPanel(QWidget)` 内部类，封装单个图表面板（PlotWidget + 曲线 + 填充 + hover + 端点标注）
- `ChartWidget.__init__` 实例变量从 22 个（top/bottom 对称）降至 4 个（2 个 Panel 引用 + 占位 + 菜单）
- `_create_chart()` / `_update_chart()` / `_update_theme_colors()` 的 top/bottom 重复逻辑消除
- `_on_mouse_moved` 迁入 `_ChartPanel`，无需 `which` 参数分派
- 文件行数从 600 → 327（缩减 45%）

**验证**：pytest 103/103 ✅ | verify_all 通过（同 4 项既有失败）

---

## Phase 4 — 架构深入优化 ✅（已完成）

> **目标**：在第三阶段 P0-P5 基础清理之上，进一步推进架构深度——消除业务层与展示层的耦合、收敛路由表面、引入注入点、消除图表面板重复。

### 2026-07-30 | ✅ T-04 | app/*.py | UI 模块定义 `__all__`

**变更**：
- `app/main_window.py`: 新增 `__all__ = ["MainWindow"]`
- `app/input_panel.py`: 新增 `__all__ = ["MoneyLineEdit", "InputPanel"]`
- `app/table_widget.py`: 新增 `__all__ = ["PnLBadge", "TableWidget"]`
- `app/chart_widget.py`: 新增 `__all__ = ["ChartWidget"]`

**验收**：pytest 103/103 ✅ | verify_all 通过（同 4 项既有失败）

---

### 2026-07-30 | ✅ T-03 | app/main_window.py | MainWindow 依赖注入接口

**变更**：
- `app/main_window.py`: `__init__()` 新增可选参数 `store` 和 `logic`；使用 `store or DataStore()` / `logic or ProfitCalculatorLogic(self.data)` 模式，默认行为不变
- 原有 `MainWindow()` 无参调用无需任何修改

**验收**：pytest 103/103 ✅ | verify_all 通过（同 4 项既有失败）

---

### 2026-07-30 | ✅ T-01 | calculator.py | 从业务逻辑中剥离展示层颜色

**变更**：
- `calculator.py`: 新增 `RateSignal`、`PnL信号` 枚举；`format_rate()` 返回 `(str, RateSignal)`；`get_pnl_label()` 返回 `(str, PnL信号)`；移除 `from config import get_color`
- `app/table_widget.py`: 新增 `_SIGNAL_TO_COLOR`、`_PNL_TO_COLOR` 字典；运行时映射信号→颜色
- `tests/test_calculator.py`: 断言改为检查枚举值
- `verify_all.py`: 修复直接访问 QTableWidget API 的问题

**验收**：pytest 103/103 ✅ | verify_all 通过（4 项既有失败无关）

### 2026-07-30 | ✅ T-02 | app/theme.py | 主题系统收敛至 app/theme.py

**变更**：
- 将 `THEMES`、`get_color()`、`set_theme()`、`get_theme()` 从 `config.py` 移至 `app/theme.py`（内联定义，非重新导出）
- `app/__init__.py` 移除主题函数的重新导出
- `config.py` 仅保留路径、日期格式、字体常量
- 所有消费者统一从 `app.theme` 导入

**验收**：pytest 103/103 ✅ | verify_all 通过（同 4 项既有失败）

### 2026-07-30 | 架构评审 | Python Architecture Review

**范围**：全项目 16 个 Python 模块  
**方法**：`/improve-python-architecture` — 逐项检查摩擦信号  
**输出**：[`python-arch-review-20260730T120000.html`](./python-arch-review-20260730T120000.html)

**发现 5 个候选优化项**（详见 [`TO-TICKETS.md`](./TO-TICKETS.md)）：

| # | 候选 | 信号类型 | 优先级 |
|---|------|----------|--------|
| T-01 | `ProfitCalculatorLogic` 返回颜色字符串 — 边界泄漏 | 边界泄漏 | **P0** |
| T-02 | 主题系统碎片化 — 三个导入路径到同一函数 | 透传 __init__ | **P1** |
| T-03 | MainWindow 缺乏 DI seam — 硬创建依赖 | 胖委托者 | **P2** |
| T-04 | 4 个 UI 模块缺乏 `__all__` | 未定义表面 | **P3** |
| T-05 | ChartWidget 内部状态扩散 — 20+ 实例变量 | 胖委托者 | **P4** |

**顶层建议**：优先处理 T-01——剥离颜色耦合后，`calculator.py` 不再导入 UI 模块，为 T-02（将主题数据移至 `app/theme.py`）解锁路径。

---

## Phase 3 — 架构深度优化 P0-P5 ✅（已完成）

> **时间**：2026-07-28 ~ 2026-07-29  
> **详情**：见 [`CONSENSUS.md`](./CONSENSUS.md) 第四节

### 2026-07-29 | 完成 | 全部五项

- [x] **P0** — 删除 Tkinter 迁移残留（5 文件 / 52 KB）
- [x] **P1** — config 穿透合并（`app/config.py` 停止重新导出）
- [x] **P2** — 删除孤立模块级颜色常量（24 个导出名称）
- [x] **P3** — 为 `calculator.py`, `formatting.py`, `data_store.py`, `app/__init__.py` 定义 `__all__`
- [x] **P4** — 图表性能优化（FillBetweenItem 去重建、输入去抖、主题增量更新）
- [x] **P5** — 单实例保证（QLocalServer 防多开）

**验证**：`pytest` 103 项通过 ✅ | `verify_all.py` 全量通过 ✅

---

## Phase 2 — PySide6 迁移 ✅（已完成）

> **时间**：2026-07-?? ~ 2026-07-28

从 Tkinter + matplotlib 迁移至 PySide6 + pyqtgraph。

- 新框架：PySide6（LGPL，Qt 官方绑定）
- 新图表库：pyqtgraph（原生 Qt 渲染）
- 保留了所有功能：双字段输入、金额校验、K/M/B 后缀、JSON 原子写入与滚动备份、7 日滚动、亮暗主题、窗口置顶、PNG 导出
- 新增：收益率列、盈亏标签列、双栏表格布局（左 4 右 3）

---

## Phase 1 — Tkinter 内增强 ✅（已完成）

> **时间**：2026-07-?? ~ 2026-07-??

在 Tkinter 版本上新增功能：
- 表格新增"收益率"列（1 位小数，红涨绿跌）
- 表格新增"盈亏标签"列（单字盈/亏 + 彩色圆角 Badge）
- 计算逻辑单元测试通过（70 → 106 项全部 PASS）

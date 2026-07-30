# DEV_LOG — 收益计算器开发日志

> **格式**：`YYYY-MM-DD` | `<操作>` | `<范围>` | `<描述>`
>
> 按时间倒序排列，最新条目在最前。

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

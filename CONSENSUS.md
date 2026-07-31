# 收益计算器 — 开发共识文档

> 生成日期：2026-07-28  
> 状态：第一阶段 ✅ 已完成 | 第二阶段 ✅ 已完成 | 第三阶段 ✅ 已完成

---

## 共识摘要

经 Grilling 访谈确认，项目分两阶段推进：

1. **第一阶段（Tkinter 内增强）** — 表格新增收益率列 + 盈亏标签，不改框架
2. **第二阶段（PySide6 迁移）** — 整体迁移至 PySide6 + pyqtgraph 图表，保留所有功能

---

## 一、项目当前状态

- **框架**：Python Tkinter + matplotlib
- **技术栈**：纯 Python，无外部依赖（除 matplotlib）
- **代码量**：~8 个模块 + 3 个测试文件
- **现有功能**：双字段录入、金额校验/格式化（支持 K/M/B 后缀）、JSON 原子持久化（滚动备份）、7 日数据表格带差值对比、亮暗双主题、窗口置顶、matplotlib 双曲线图（仓库总量 + 现金子项）、PNG 导出
- **打包方式**：PyInstaller (.exe)

---

## 二、第一阶段任务（Tkinter 内增强）

### 2.1 表格新增"收益率"列

- **位置**：表格 "较前日" 列之后
- **计算方式**：`(当日总收益 - 前日总收益) / 前日总收益 × 100%`
- **精度**：1 位小数，如 `+2.4%` / `-1.3%`
- **配色**：涨（绿/FG_POS）、跌（红/FG_NEG）、持平（灰/FG_MUTED）

### 2.2 表格新增"盈亏标签"列

- **位置**：收益率列之后，或与收益率合并为一列
- **样式**：单字 "盈"（绿底圆角）/ "亏"（红底圆角）/ "—"（灰底）
- **规则**：当日 warehouse > 前日 warehouse → 盈；< → 亏；= 或无前日数据 → —

### 2.3 涉及文件

| 文件 | 修改内容 |
|------|---------|
| `ui/table.py` | TableManager.draw() — 新增两列，列头 + 单元格渲染 |
| `calculator.py` | 新增 calculate_rate() / format_rate() / get_pnl_label() 三个静态方法 |
| `tests/test_calculator.py` | 新增 16 个测试用例覆盖新方法 |

### 2.4 第一阶段完成确认 ✅

所有改动已完成并通过测试：

- [x] 表格新增"收益率"列（1位小数，红涨绿跌）
- [x] 表格新增"盈亏标签"列（单字盈/亏 + 彩色圆角 Badge）
- [x] 计算逻辑单元测试通过（原70项 → 现106项，全部 PASS）
- [x] 语法校验通过
- [x] 现有功能不受影响

---

## 三、第二阶段任务（PySide6 迁移）

### 3.1 UI 框架迁移

| 方向 | 选择 |
|------|------|
| 框架 | **PySide6**（Qt 官方绑定，LGPL 协议） |
| 图表 | **pyqtgraph**（原生 Qt 渲染，高性能，交互流畅） |
| 许可 | LGPL，商用友好 |

### 3.2 PySide6 组件规划

- **主窗口**：QMainWindow
- **输入面板**：QLineEdit + QPushButton + QLabel，QSS 样式
- **数据表格**：QTableWidget / QTableView + QStyledItemDelegate
- **图表**：pyqtgraph PlotWidget（双 Y 轴，支持鼠标悬停/缩放/平移）
- **主题**：QSS 变量 + `setStyleSheet` 一键切换亮暗
- **右鍵菜单**：图表导出 PNG
- **窗口状态**：geometry / 置顶 / 主题持久化（仍用 JSON）

### 3.3 功能保留清单

所有现有功能在迁移后必须保留：

- [x] 双字段输入（现金 + 仓库价值）
- [x] 金额输入校验与自动格式化（K/M/B 后缀、千分位、¥/$ 符号）
- [x] Enter 保存 / Ctrl+A 全选 / Esc 清空
- [x] JSON 原子写入 + 滚动备份（max_backups=3）+ 损坏自动恢复
- [x] 7 日数据滚动（超出删除最旧）
- [x] 表格编辑模式（点击 ✎ 回填到输入框，修改后更新）
- [x] 删除数据（确认对话框 + 持久化）
- [x] "较前日"差值列（▲/▼/— + 金额 + 红绿配色）
- [x] **新增：收益率列**
- [x] **新增：盈亏标签列**
- [x] 双曲线图（仓库总量线 + 现金子项线，填充区域）
- [x] 亮/暗主题切换
- [x] 窗口置顶
- [x] 右键导出 PNG
- [x] 窗口几何状态持久化
- [x] 单元测试

### 3.4 文件结构新规划

```
Profit Calculator/
├── main.py                 ← 入口
├── app/
│   ├── __init__.py
│   ├── main_window.py      ← QMainWindow
│   ├── input_panel.py      ← QWidget 输入面板
│   ├── table_widget.py      ← QTableWidget
│   ├── chart_widget.py      ← pyqtgraph PlotWidget
│   ├── logic.py             ← 业务逻辑（复用现有 calculator.py 思路）
│   ├── data_store.py        ← 数据持久化（复用现有）
│   ├── formatting.py        ← 金额格式化（复用现有）
│   └── config.py            ← 配置 + 主题
├── tests/                   ← 保留 + 扩充
└── requirements.txt         ← PySide6 + pyqtgraph
```

---

## 四、第三阶段任务（架构深度优化 Architecture Deepen — ✅ 已完成）

> **启动日期**：2026-07-28  
> **目标**：在 PySide6 迁移完成的基础上，清理历史遗留问题，优化代码结构，提升运行性能与 UI 质感  
> **前置条件**：第二阶段（PySide6 迁移）已完成并验证通过  
> **后续**：2026-07-30~31 新增 Phase 4（T-01~T-05）与架构评审 C1/C2 优化，均已完成；进度见 [`DEV_LOG.md`](DEV_LOG.md) 与 [`TO-TICKETS.md`](TO-TICKETS.md)。

### 4.1 优化优先级

按架构审查报告推荐的顺序依次执行：

| 优先级 | 候选 | 类型 | 影响 | 状态 |
|--------|------|------|------|------|
| P0 | **#5 迁移残留清理** — 删除 Tkinter 死代码 | 删除 | 立即减少 5 文件 / 52 KB | ✅ 已完成 |
| P1 | **#2 config 穿透合并** — 消除 app/config.py 的重复导出 | 重构 | 协议面缩小，消除导入歧义 | ✅ 已完成 |
| P2 | **#3 孤立常量清理** — 删除 config.py 中的冻结模块级常量 | 删除 | 协议面缩小 24 个导出名 | ✅ 已完成 |
| P3 | **#4 定义模块表面** — 为所有模块添加 `__all__` | 规范 | 明确消费者契约 | ✅ 已完成 |
| P4 | **性能优化** — 图表渲染、启动速度、内存占用 | 优化 | 更快的运行体验 | ✅ 已完成 |
| P5 | **单实例保证** — QLocalServer 防止多开 | 功能 | 避免内存占用翻倍 | ✅ 已完成 |

### 4.2 具体方案

#### P0 — 删除 Tkinter 迁移残留

| 操作 | 文件 | 理由 |
|------|------|------|
| 删除 | `profit_calculator.py` | Tkinter 主入口，已被 `main.py` 替代 |
| 删除 | `ui/` 整个目录（4 文件） | Tkinter UI 组件，已被 `app/` 替代 |
| 删除 | `profit_calculator.spec` | Tkinter PyInstaller 配置 |
| 保留 | `config.py`（根目录） | 仍有 `THEMES` 色板字典被 `app/config.py` 引用 |
| 保留 | `tests/` | 纯业务逻辑测试，与 UI 框架无关 |

#### P1 — config 穿透合并

- 将 `generate_qss()` 从 `app/config.py` 移至新的 `app/theme.py`
- `app/config.py` 停止从根 `config.py` 重导出常量
- `app/theme.py` 直接从根 `config.py` 导入 `THEMES` 字典 + 主题函数

#### P2 — 孤立常量清理

- 删除 `config.py:130-155` 的 24 个模块级颜色常量
- 这些常量在导入时冻结为 light 主题，且全局无任何消费者

#### P3 — 定义模块表面

| 模块 | `__all__` 内容 |
|------|---------------|
| `calculator.py` | `DayRecord`, `ProfitCalculatorLogic` |
| `formatting.py` | `format_money`, `parse_money_input`, `is_valid_money_input`, `format_input_value`, `unformat_input_value` |
| `data_store.py` | `DataStore` |
| `app/__init__.py` | \*（空或按需导出） |

#### P4 — 性能优化

- 图表 `_update_chart()` 中的 FillBetweenItem 重建优化（当前每次更新都 remove + 重新 add）
- 输入框 `textChanged` 信号去抖（debounce）
- 主题切换时避免全量重建图表（增量更新颜色）
- 验证启动时间、内存占用基线

### 4.3 验收标准

- [x] `verify_all.py` 全部测试通过（exit code 0）
- [x] `pytest tests/` 全部通过（103 项）
- [x] 启动速度不差于优化前
- [x] 程序运行无闪退、无 UI 卡顿
- [x] Tkinter 代码完全移除后已有功能不受影响

---

## 五、关键决策记录

| # | 决策 | 选项 | 选择 | 理由 |
|---|------|------|------|------|
| 1 | UI 框架 | Tkinter / PySide6 / Electron | **PySide6** | LGPL + Qt 官方绑定 + Python 原生集成 |
| 2 | 图表库 | matplotlib / pyqtgraph / Plotly | **pyqtgraph** | 原生 Qt 渲染，无 WebView 开销，交互流畅 |
| 3 | 开发顺序 | 一步到位 / 分阶段 | **分阶段** | 先 Tkinter 加功能再用上，PySide6 迁移不阻塞 |
| 4 | 收益率精度 | 1 位 / 2 位 | **1 位** | 紧凑，足够判断趋势 |
| 5 | 盈亏标签 | 文字 / 单字 Badge | **单字 + 圆角** | 简洁，红绿底色一眼可辨 |
| 6 | 单实例保证 | 文件锁 / QLocalServer | **QLocalServer** | Qt 原生方案，PyInstaller 兼容，崩溃后自动清理 |

---

## 六、后续执行建议

1. 第一阶段直接用当前 Agent 完成，改动的文件少，风险低
2. 第二阶段建议先 `pip install PySide6 pyqtgraph` 验证环境，再逐步迁移
3. 迁移时先搭骨架（QMainWindow → 布局 → 输入 → 表格 → 图表），再填充逻辑
4. 测试文件保持 pytest 框架，PySide6 部分的 UI 测试可后期补充

---

*本文档与 PROJECT_REFERENCE.md 配合使用。*

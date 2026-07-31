# To-Tickets — 收益计算器架构优化工单

> **来源**：2026-07-30 Python Architecture Review（T 系列）+ 2026-07-31 `/improve-codebase-architecture`（C 系列）  
> **规则**：本文件是**仓库内唯一的待办事实来源**。活跃表只保留「未完成」工单；每完成一项 → 移入「已完成归档」并记日期 → 同步 `DEV_LOG.md` → 与本提交一起 commit。
>
> **维护节奏**（绑定到已有流程节点，不新增习惯）：
> 1. 开始实现某工单前，把状态从 📝 已录入 → 🔄 进行中（认领）
> 2. 每会话结束、commit 之前：完成 → ✅/❌ → 移入归档；新评审候选（含未拍板的 `Worth exploring` / `Speculative`）一律先录入活跃表
> 3. 待办**不得只写在 memory / 个人笔记里**——不落 TO-TICKETS 就不算数

---

## 活跃工单

| Ticket | 标题 | 类型 | 优先级 | 状态 | 依赖 | 关联 |
|--------|------|------|--------|------|------|------|
| C3 | 收敛三套 K/M/B 格式化 | 重构 | P2（Worth exploring） | 📝 已录入 | 无 | — |
| C4 | InputPanel seam 成真 | 重构 | P2（Worth exploring） | 📝 已录入 | 无 | C5 |
| C5 | verify_all 覆盖并入 pytest | 重构 | P2（Worth exploring） | 📝 已录入 | C2 ✅、C4 | — |
| C6 | 浅层残留清扫 | 清理 | P3（Speculative） | 📝 已录入 | 无 | — |

---

## 工单详情

### C3: 收敛三套 K/M/B 格式化

- **类型**：重构（重复实现）
- **优先级**：P2 — Worth exploring
- **文件范围**：`formatting.py`、`app/chart_widget.py`

**问题描述**：金额的 K/M/B 缩写存在三套独立实现，阈值与精度互不相同，改动一处容易漏改另两处：

| 实现 | B | M | K | 精度 | 前缀 |
|------|---|---|---|---|------|
| `formatting.format_money()` | 无 | ≥1e8 | ≥1e6 | `,.1f` / `,.2f` | ¥ |
| `KMBAxisItem.tickStrings()` | ≥1e9 | ≥1e6 | ≥1e3 | `.1f` | 无 |
| `_ChartPanel._format_value()` | ≥1e9 | ≥1e6 | ≥1e3 | `.2f` / `.1f` | ¥ |

**连带问题**：`date_str[-5:]`（MM-DD 截取）在 `app/chart_widget.py:395`、`app/main_window.py:408/:458`、`app/input_panel.py:243`、`app/table_widget.py:198` 重复出现。

**解决思路**：抽出单一 `format_compact(value, *, currency=False)` 共享实现，三处按需调用；日期截取提为 helper。

### C4: InputPanel seam 成真

- **类型**：重构（Seam 未落地）
- **优先级**：P2 — Worth exploring
- **文件范围**：`app/main_window.py`、`app/input_panel.py`

**问题描述**：
- `InputPanel.get_cash_value()`（`app/input_panel.py:356`）**无任何调用者**——`MainWindow` 直接访问 `cash_entry.text()` 绕过公开 getter，公开 API 形同虚设
- 编辑状态双份：`MainWindow._editing_date`（`app/main_window.py:70`）与 `InputPanel._editing_date`（`app/input_panel.py:131`）各持一份，可能漂移

**解决思路**：`MainWindow` 改走公开 getter；编辑状态收敛到单一方（`InputPanel` 为所有者，`MainWindow` 只查询），为 C5 创造真 seam。

### C5: verify_all 覆盖并入 pytest

- **类型**：重构（影子测试收敛）
- **优先级**：P2 — Worth exploring
- **依赖**：C2 ✅（已完成）、C4
- **文件范围**：`verify_all.py`、`tests/`

**问题描述**：`verify_all.py`（825 行）是影子测试，深度私有访问（如 `win._editing_date`）；1~3 节重复 pytest 叶子测试。`settings.json` 污染已隔离（2026-07-31 修复），但全量收敛需 C4 先造真 seam（公开 API 可测）。

**解决思路**：将 UI 烟测转成 pytest 用例（offscreen，参照 `tests/test_table_theme.py` 首个 Qt fixture），按节迁移后删除 `verify_all.py`。

### C6: 浅层残留清扫

- **类型**：清理（Speculative）
- **优先级**：P3
- **文件范围**：全项目

**问题描述**：
- `app/config.py` — 空壳文件（5 行 docstring，无导出，模块面为零）
- `config.py` — 7 个 `FONT_*` 元组常量无任何消费者（`input_panel.py` 自带本地字体尺寸）
- `PnL信号` — 中英混排命名，应为 `PnLSignal`
- `unformat_input_value` 死分支、约 8 处死 import

**解决思路**：逐项确认后删除/改名；风险低但需跑全量测试兜底。

---

## 已完成归档

### C 系列（2026-07-31）

| Ticket | 标题 | 完成日期 | 提交 |
|--------|------|----------|------|
| C1 | 表格主题色 import 期冻结修复 | 2026-07-31 | `8a7b98a` |
| C2 | DayRecord 生命周期收敛到 logic 层 | 2026-07-31 | `240d72b` |

### T 系列（2026-07-30，Phase 4）

| Ticket | 标题 | 完成日期 | 提交 |
|--------|------|----------|------|
| T-01 | 从业务逻辑中剥离展示层颜色 | 2026-07-30 | `ea68a61` |
| T-02 | 主题系统收敛至 `app/theme.py` | 2026-07-30 | `ea68a61` |
| T-03 | MainWindow 依赖注入接口 | 2026-07-30 | `ea68a61` |
| T-04 | UI 模块定义 `__all__` | 2026-07-30 | `ea68a61` |
| T-05 | ChartWidget 拆分 `_ChartPanel` | 2026-07-30 | `ea68a61` |

---

## 工单状态说明

- **📝 已录入**：已记录但尚未进入开发计划（含未拍板的候选）
- **🔜 待排期**：已确认需求，等待排入迭代
- **🔄 进行中**：正在开发中
- **✅ 已完成**：已合并验证通过
- **❌ 已关闭**：经评估决定不实施

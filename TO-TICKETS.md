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
| C5 | verify_all 覆盖并入 pytest | 重构 | P2（Worth exploring） | 📝 已录入 | C2 ✅、C4 ✅ | — |
| C6 | 浅层残留清扫 | 清理 | P3（Speculative） | 📝 已录入 | 无 | — |
| C7 | C4 后续：getter docstring 契约修正 | fix | P3 | 📝 已录入 | C4 ✅ | — |
| C8 | C4 后续：verify_all 检查标签改名 | 清理 | P3 | 📝 已录入 | C4 ✅ | — |
| C9 | C4 后续：save_today getter 绕过静态守卫 | 测试 | P3 | 📝 已录入 | C4 ✅ | — |

---

## 工单详情

### C3: 收敛三套 K/M/B 格式化 ✅

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

### C5: verify_all 覆盖并入 pytest

- **类型**：重构（影子测试收敛）
- **优先级**：P2 — Worth exploring
- **依赖**：C2 ✅、C4 ✅（已完成）
- **文件范围**：`verify_all.py`、`tests/`

**问题描述**：`verify_all.py`（825 行）是影子测试，深度私有访问（如 `win.input_panel.cash_entry.setText()`、`win._start_edit()`）；1~3 节重复 pytest 叶子测试。`settings.json` 污染已隔离（2026-07-31 修复），但全量收敛需 C4 先造真 seam（公开 API 可测）。

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

### C7: C4 后续 —— getter docstring 契约修正

- **类型**：fix（文档契约与实际行为不符）
- **优先级**：P3
- **来源**：C4 code-review（Spec 轴）
- **文件范围**：`app/input_panel.py`（+ `tests/test_input_panel.py` 锁行为）

**问题描述**：`get_cash_value()` / `get_warehouse_value()` docstring 写「非法输入抛出 ValueError」，但垃圾文本（如 `"abc"`）经 `parse_money_input` 的 `_normalize_numeric_string` 清洗为空后返回 `None` 而非 `ValueError`——「空输入」与「垃圾输入」仍不可区分，且 docstring 与同改动新增测试断言（垃圾 → `None`）冲突。

**解决思路**：docstring 修正为「结构性非法数字抛 ValueError；清洗后为空的文本返回 None」（与 `parse_money_input` 语义对齐）。如需真正区分空与垃圾输入，属解析层变更，另评。

### C8: C4 后续 —— verify_all 检查标签改名

- **类型**：清理
- **优先级**：P3
- **来源**：C4 code-review（Standards 轴）
- **文件范围**：`verify_all.py`

**问题描述**：`test_edit_mode` 两条 check 标签仍写「edit 后 _editing_date 设置」/「取消后 _editing_date 清空」，断言对象已是 `win.input_panel.get_editing_date()`——标签指向已删除的 `MainWindow._editing_date` 实现细节，误导排查。

**解决思路**：标签改名为「edit 后 get_editing_date() 设置」/「取消后 get_editing_date() 清空」（或等价表述）。

### C9: C4 后续 —— save_today getter 绕过静态守卫

- **类型**：测试（防回归守卫）
- **优先级**：P3
- **来源**：C4 code-review（Spec 轴）
- **文件范围**：`tests/test_input_panel.py`（或 `app/main_window.py` 注释）

**问题描述**：`test_save_today_uses_public_getters` 名字夸大——纯行为等价测试（记录保存、字段清空），即使 `save_today` 回归到 `cash_entry.text()` + `parse_money_input` 也会通过。C4 的 seam 主张目前只对 `_editing_date` 有 `hasattr` 静态守卫，对 getter 绕过无守卫。

**解决思路**：仿照 `test_main_window_has_no_editing_date_attr`，加源码级守卫（AST / 字符串断言 `main_window.py` 无 `cash_entry.text()` 直取、无 `parse_money_input` 调用）；或将测试改名降级为纯行为等价并加注释说明。

---

## 已完成归档

### C 系列（2026-07-31）

| Ticket | 标题 | 完成日期 | 提交 |
|--------|------|----------|------|
| C1 | 表格主题色 import 期冻结修复 | 2026-07-31 | `8a7b98a` |
| C2 | DayRecord 生命周期收敛到 logic 层 | 2026-07-31 | `240d72b` |
| C3 | 收敛三套 K/M/B 格式化 + 日期短格式去重 | 2026-07-31 | `e3eff63` |
| C4 | InputPanel seam 成真 | 2026-07-31 | `bbe59bf` |

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

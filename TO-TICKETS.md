# To-Tickets — 收益计算器架构优化工单

> **来源**：2026-07-30 Python Architecture Review（T 系列）+ 2026-07-31 `/improve-codebase-architecture`（C 系列）+ 2026-08-01 `收益计算器-优化建议清单.md` 评审（O 系列）  
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

> 活跃表为空：O 系列已全部处理完毕（O-06 ✅ / O-07 ❌ 见归档）。

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

### C5: verify_all 覆盖并入 pytest ✅

- **类型**：重构（影子测试收敛）
- **优先级**：P2 — Worth exploring
- **依赖**：C2 ✅、C4 ✅（已完成）
- **文件范围**：`verify_all.py`、`tests/`
- **完成日期**：2026-08-01

**问题描述**：`verify_all.py`（831 行）是影子测试，深度私有访问（如 `win.input_panel.cash_entry.setText()`、`win._start_edit()`）；1~3 节重复 pytest 叶子测试。`settings.json` 污染已隔离（2026-07-31 修复），但全量收敛需 C4 先造真 seam（公开 API 可测）。

**解决思路**：将 UI 烟测转成 pytest 用例（offscreen，参照 `tests/test_table_theme.py` 首个 Qt fixture），按节迁移后删除 `verify_all.py`。

---

### O-01: logging 替换静默 except

- **类型**：重构（可观测性）
- **优先级**：P0 — 立即做，零风险
- **文件范围**：`app/main_window.py`、`data_store.py`、`main.py`（日志配置）

**问题描述**：全项目无 logging 配置，3 处 `except: pass` 静默吞异常，文件损坏/写入失败时用户与开发者均无察觉：

| 位置 | 场景 |
|------|------|
| `app/main_window.py:138` `_load_settings` | 设置文件 JSON 损坏或读取失败 |
| `app/main_window.py:152` `_save_settings` | 设置文件写入失败 |
| `data_store.py:112` `_rotate_backups` | 备份文件复制失败（不影响主流程） |

（注：`calculator.py:72` / `data_store.py:77` 的 except 均 `return None`，属正常语义，非静默吞）

**解决思路**：模块级 `logger = logging.getLogger(__name__)` + `logger.warning("...", e)`；`main.py` 配置 `basicConfig` 写入 `APP_DIR/profit_calculator.log`——打包版为窗口化 exe 无 stderr，文件日志是唯一可见通道。纯新增行为，不改任何逻辑流程。

### O-02: MoneyLineEdit.refresh_validity 公开 seam

- **类型**：重构（seam）
- **优先级**：P0 — 立即做，零风险
- **文件范围**：`app/input_panel.py`
- **关联**：C4（InputPanel seam 成真）、C9（静态守卫）

**问题描述**：`InputPanel.refresh_validity()`（`app/input_panel.py:375-376`）跨类直取 `cash_entry._update_validity()` / `warehouse_entry._update_validity()` 私有方法——C4 公开 seam 体系中漏网的一处跨对象私有访问，与 C9 静态守卫精神相悖。

**解决思路**：`MoneyLineEdit` 新增公开 `refresh_validity()` 委托 `_update_validity()`；`InputPanel.refresh_validity()` 改为调用公开方法。纯重命名，内部实现不动，行为不变。可补一条 AST 静态守卫（防 InputPanel 直调 `_update_validity` 复发）。

### O-03: format_money docstring 阈值交叉说明

- **类型**：文档
- **优先级**：P0 — 随手项，随 O-01 提交
- **文件范围**：`formatting.py`

**问题描述**：`format_compact` 的 docstring 已注明与 `format_money` 的 K 阈值差异（C3 已做），但 `format_money` 侧未交叉引用。两者 K 阈值不同（`format_money` ≥1e6，`format_compact` ≥1e3），改一处易漏另一处。

**解决思路**：`format_money` docstring 末尾补一句「与 `format_compact` 不同，此处 K 阈值为 1,000,000 而非 1,000」，形成双向说明。只改注释。

### O-04: CSV 数据导出

- **类型**：功能（新增）
- **优先级**：P1 — 低风险，纯新增
- **文件范围**：新增导出纯函数 + `app/main_window.py`（按钮 + QFileDialog）

**问题描述**：数据仅存于本地 JSON，无外部查看/备份导出通道。

**解决思路**：业务层新增纯函数生成 CSV 文本（列：日期/现金/仓库/较前日/收益率），UI 标题栏加「导出 CSV」按钮，QFileDialog 选路径保存。纯函数可单测，不修改任何现有方法。

### O-05: 今日未录入提醒

- **类型**：功能（新增）
- **优先级**：P1 — 低风险，纯新增
- **文件范围**：`app/main_window.py`

**问题描述**：每日录入易遗漏，无任何提示。

**解决思路**：标题栏或状态栏只读检查 `logic.get_record(self.today)`，未录入时显示「今日未录入」；`save_today()` 成功后刷新消失。纯读操作，零数据写风险。

### O-06: 图表稀疏数据提示 ✅

- **类型**：功能（新增）
- **优先级**：P2 — 可选增强
- **文件范围**：`app/chart_widget.py`
- **完成日期**：2026-08-01

**问题描述**：n=2~3 时图表只有两三个点，趋势不可读也无说明。

**解决思路**：`ChartWidget.draw()` 中当 `2 <= n <= 3` 时叠加半透明提示文字「数据较少，需更多数据以显示趋势」，复用现有 `_show_placeholder` / `_clear_placeholder` 机制；不触碰数据、曲线、交互。

**实现说明**：`_show_sparse_hint()` 新建 overlay QLabel（不入 layout，作为顶层子控件覆盖图表），`WA_TransparentForMouseEvents` 保证鼠标事件透传，`resizeEvent` 跟随 widget 尺寸；与 `_placeholder_label` 共用生命周期。测试 `test_chart_sparse_data_hint` 覆盖 n>=4 无提示 / n=3、2 有提示 / n<2 回归占位。

### O-07: 收益率目标参考线 ❌

- **类型**：功能（新增）
- **优先级**：P2 — 可选增强
- **文件范围**：`app/chart_widget.py`、`app/main_window.py`、`settings.json`
- **关闭日期**：2026-08-01

**问题描述**：图中无目标参照，难以判断是否达到预期收益。

**解决思路**：上图叠加 pyqtgraph `InfiniteLine` 目标线，目标值经输入框配置并持久化到 settings.json；不碰数据层。

**关闭原因**：目标语义未定义——本 app 的「收益率」是逐日环比（较前日），图表只画「现金」与「仓库」两条金额曲线，无收益率曲线；「目标参考线画在什么序列上、代表累计收益还是逐日收益率」无法解释。实现需输入框 + settings 持久化 + InfiniteLine + 测试，成本远高于收益，YAGNI 关闭（参照 O-C 系列先例）。

---

## 已完成归档

### C 系列（2026-07-31）

| Ticket | 标题 | 完成日期 | 提交 |
|--------|------|----------|------|
| C1 | 表格主题色 import 期冻结修复 | 2026-07-31 | `8a7b98a` |
| C2 | DayRecord 生命周期收敛到 logic 层 | 2026-07-31 | `240d72b` |
| C3 | 收敛三套 K/M/B 格式化 + 日期短格式去重 | 2026-07-31 | `e3eff63` |
| C4 | InputPanel seam 成真 | 2026-07-31 | `bbe59bf` |
| C6 | 浅层残留清扫 | 2026-07-31 | `923f544` |
| C7 | C4 后续：getter docstring 契约修正 | 2026-07-31 | `923f544` |
| C8 | C4 后续：verify_all 检查标签改名 | 2026-07-31 | `923f544` |
| C9 | C4 后续：save_today getter 绕过静态守卫 | 2026-07-31 | `923f544` |
| C5 | verify_all 覆盖并入 pytest | 2026-08-01 | （待提交） |

### T 系列（2026-07-30，Phase 4）

| Ticket | 标题 | 完成日期 | 提交 |
|--------|------|----------|------|
| T-01 | 从业务逻辑中剥离展示层颜色 | 2026-07-30 | `ea68a61` |
| T-02 | 主题系统收敛至 `app/theme.py` | 2026-07-30 | `ea68a61` |
| T-03 | MainWindow 依赖注入接口 | 2026-07-30 | `ea68a61` |
| T-04 | UI 模块定义 `__all__` | 2026-07-30 | `ea68a61` |
| T-05 | ChartWidget 拆分 `_ChartPanel` | 2026-07-30 | `ea68a61` |

---

### O 系列实现（2026-08-01，已合并）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-01 | logging 替换静默 except | 重构（可观测性） | 2026-08-01 | `e6d5b64` |
| O-02 | MoneyLineEdit.refresh_validity 公开 seam | 重构（seam） | 2026-08-01 | `486d41f` |
| O-03 | format_money docstring 阈值交叉说明 | 文档 | 2026-08-01 | `ac75c71` |
| O-04 | CSV 数据导出 | 功能（新增） | 2026-08-01 | `8f50592` |
| O-05 | 今日未录入提醒 | 功能（新增） | 2026-08-01 | `749cd59` |
| O-06 | 图表稀疏数据提示 | 功能（新增） | 2026-08-01 | （随本提交） |

> 两个并行分支（A：O-01~O-03；B：O-04~O-05）经 merge 合入 main，合并提交 `c01c2c2` / `fdeca85`。合并时 `main_window.py` 模块级 logger 命名冲突（`logger` vs `_logger`）已收敛为 `logger`。

### O 系列（2026-08-01，评审关闭）

| Ticket | 标题 | 类型 | 关闭日期 | 关闭原因 |
|--------|------|------|----------|----------|
| O-C1 | `event.position()` 兼容 fallback | 防御性兼容 | 2026-08-01 | requirements 下限 PySide6>=6.6.0，`QMouseEvent.position()` 自 6.2 起保证存在；无真实触发路径（YAGNI） |
| O-C2 | 多选日期范围（7 日→30/90 日） | 核心数据模型变更 | 2026-08-01 | 7 日限制是产品决策；双栏表格（左 4 右 3）、图表、summary、rotate_weekly 均围绕 7 日架构，改动需重做表格布局与数据流，风险高、收益未明。若确需长周期视图应另立「多视图」工单而非扩展 |
| O-C3 | AppController 拆分 | 架构重构 | 2026-08-01 | 采纳清单撤回判断：MainWindow 514 行职责内聚（窗口/主题/置顶/信号/数据流/刷新），对当前规模是合理的协调者，拆分引入不必要间接层 |
| O-C4 | QSS 模板文件化 | 架构重构 | 2026-08-01 | 采纳清单撤回判断：两套主题用 f-string 生成 QSS 是社区常见做法；模板化需处理 PyInstaller 资源路径，收益低 |
| O-07 | 收益率目标参考线 | 功能（新增） | 2026-08-01 | 目标语义未定义（累计收益 vs 逐日收益率），画在哪条序列上不明确；实现成本高于收益，YAGNI 关闭 |

---

## 工单状态说明

- **📝 已录入**：已记录但尚未进入开发计划（含未拍板的候选）
- **🔜 待排期**：已确认需求，等待排入迭代
- **🔄 进行中**：正在开发中
- **✅ 已完成**：已合并验证通过
- **❌ 已关闭**：经评估决定不实施

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

> 活跃表已空（2026-08-01）。O-11~O-15（P2 第三批）已完成并归档，见「已完成归档」。

| Ticket | 标题 | 类型 | 优先级 | 状态 | 依赖 | 关联 |
|--------|------|------|--------|------|------|------|

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

### O-08: 保存前校验 cash ≤ warehouse 不变式 ✅

- **类型**：功能（新增校验）
- **优先级**：P1 — 低风险，纯新增
- **文件范围**：`app/input_panel.py`、`app/main_window.py`、`calculator.py`（可选）
- **关联**：O-C2（数据模型约束同源：7 日限制产品决策）
- **完成日期**：2026-08-01

**问题描述**：代码与文档均声明「现金 ⊆ 仓库」（`calculator.py` DayRecord docstring、README 业务规则），但 `save_today()` / `save_record()` 无任何 cash ≤ warehouse 校验——用户可保存现金 > 仓库的违反核心业务规则数据，无提示、无红边、无拦截。

**解决思路**：`save_today()` 保存前校验 `cash > warehouse` 时弹警告并中断；输入框联动加越界警示边框提示（复用 `validity` 属性或新增状态，琥珀色以区分「结构性非法」的红色）。是否在业务层 `save_record` 强制不变式需拍板——强制会破坏「允许记录异常但保留展示」的语义，建议 UI 层拦截 + 业务层仅告警。补回归测试（越界保存被拦截 / 边界相等允许）。

**实现说明**：UI 层拦截 + 业务层仅告警。`save_today()` 校验 `cash > warehouse` 时 `QMessageBox.warning` 并 return；`InputPanel._update_invariant_state()` 跨字段检查挂在 `_update_save_btn_state`，`MoneyLineEdit.set_invariant_warning()` 公开 seam 置 `validity="warning"` 态（`theme.py` 新增 `BORDER_WARNING` 琥珀色 QSS）；`save_record` 业务层仅 `logger.warning` 不拦截。测试 +6（越界警告边框 / 恢复 / 边界相等 / 空字段 / 保存拦截 / 边界保存）。

### O-09: 加载时顶层 dict schema 校验 ✅

- **类型**：重构（健壮性）
- **优先级**：P1 — 低风险，纯新增
- **文件范围**：`data_store.py`（`_try_load`）、`app/main_window.py`（`_load_settings`）
- **关联**：O-01（同类静默容错加固）
- **完成日期**：2026-08-01

**问题描述**：`_try_load` 只检查 JSON 可解析，不检查顶层结构。若 `data.json` 被外部改写为合法 JSON 但顶层非 dict（如 `[]`），`ProfitCalculatorLogic` 收下错误类型，启动 `summary → get_record → self.data.get()`（`calculator.py:63`）直接 AttributeError 崩溃，且备份恢复链未触发（文件"没坏"）。`settings.json` 同理（顶层数组 → `_settings.get`（`main_window.py:73`）崩溃）。

**解决思路**：`_try_load` 增加 `isinstance(data, dict)` 校验，非 dict 视为损坏 → 走备份恢复链。`_load_settings` 同样要求顶层 dict（非 dict 返回默认 `{}`）。补测试：顶层 list 触发备份恢复 / settings 顶层 list 返回默认。

**实现说明**：`data_store._try_load` 非 dict 返回 None（走备份恢复链）；`main_window._load_settings` 非 dict 返回默认 `{}` + warning 日志。测试 +3（data 顶层 list 触发备份恢复 / 全 list 返回空 / settings 顶层 list 返回默认）。

**连带修复（测试夹具）**：测试 fixtures 的 `DataStore(tmp_path/data.json)` 未传 `backup_file` → 默认指向真实 `data.json.bak*`，`load()` 备份恢复链会读取并把真实备份写入 tmp_path、`save()` 把测试数据写回真实备份（静默污染用户备份）。已改为显式传 `backup_file=tmp_path/data.json.bak`（test_input_panel + test_ui_smoke 共 6 处）。

### O-10: 打包配置纳入版本控制 ✅

- **类型**：运维
- **优先级**：P1 — 低风险，纯版本控制调整
- **文件范围**：`.gitignore`、`收益计算器.spec`、`app_icon.ico`
- **完成日期**：2026-08-01

**问题描述**：`收益计算器.spec` 被 `.gitignore`（第 49 行）忽略、`app_icon.ico` 未跟踪（`git status` 显示 `??`）。打包配置不入库 → 打包产物不可复现、不可追溯，与 README「`python -m PyInstaller 收益计算器.spec`」的打包流程说明矛盾。

**解决思路**：从 `.gitignore` 移除 `收益计算器.spec` 行；`git add 收益计算器.spec app_icon.ico` 入库（工作区未提交的 `main.py` 图标改动建议一并提交）。此后重打包时 spec 的变更可 diff 追溯。

**完成说明**：`收益计算器.spec` 已出 `.gitignore` 入库（提交 `20b5170`）、`app_icon.ico` + `main.py` 图标改动入库（提交 `fa16d77`）。

### O-11: CSV 导出金额统一格式化 ✅

- **类型**：重构（显示一致性）
- **优先级**：P2 — 低风险
- **文件范围**：`calculator.py`（`export_csv`）
- **关联**：C3（K/M/B 收敛）
- **完成日期**：2026-08-01

**问题描述**：`export_csv` 中较前日差值直接 `str(record.warehouse - prev_warehouse)`（`calculator.py:209`），float 运算会暴露 `0.30000000000000004` 类伪影，且与表格/图表显示格式（`format_money` 千分位）不一致。

**解决思路**：导出差值统一走 `format_money`（或保留数值但补格式说明）。需平衡 Excel 打开场景——数值型单元格利于后续分析，字符串格式化利于可读性；拍板后补测试。

**实现说明**：拍板走 `format_money` 字符串（与界面一致；代价是 Excel 中为文本不可直接求和）。现金/仓库/较前日三列统一 `format_money`；改用 stdlib `csv` 模块生成（`lineterminator="\n"`），含千分位逗号的字段自动引号包裹，Excel 正确分列。测试更新 + 新增 `test_export_csv_format_money_unified`（千分位引号包裹 + float 伪影消除）。

### O-12: dev 依赖清单与版本锁定 ✅

- **类型**：运维
- **优先级**：P2 — 低风险
- **文件范围**：`requirements.txt`、新增 `requirements-dev.txt`
- **完成日期**：2026-08-01

**问题描述**：`requirements.txt` 仅 2 个运行时依赖且未锁版本（`PySide6>=6.6.0` / `pyqtgraph>=0.13.0`）；pytest 未记录 → 新环境无法直接复现 166 项测试。

**解决思路**：新增 `requirements-dev.txt`（含 `-r requirements.txt` + pytest）；运行时依赖是否锁精确版本（`==`）由维护习惯决定，至少 dev 环境记录 pytest 版本。

**实现说明**：拍板锁精确版本。`requirements.txt` → `PySide6==6.11.1` / `pyqtgraph==0.14.0`（实测版本，配合 O-10 可复现 exe 构建）；新增 `requirements-dev.txt`（`-r requirements.txt` + `pytest==9.1.1`），新环境可精确复现测试。

### O-13: 编辑态关闭窗口确认 ✅

- **类型**：功能（新增）
- **优先级**：P2 — 低风险，纯新增
- **文件范围**：`app/main_window.py`（`closeEvent`）
- **完成日期**：2026-08-01

**问题描述**：编辑/复用模式下直接关窗，未保存改动静默丢失（`closeEvent`（`main_window.py:160`）只落 settings 不落数据），用户无感知。

**解决思路**：`closeEvent` 检测 `input_panel.is_editing() or is_reusing()` 时弹确认框（「有未保存的编辑，确定退出？」）。注意 UI 烟测中 `win.close()` 是公开 seam，需确认确认框 mock 策略不破坏现有测试（`test_settings_persistence` 等）。

**实现说明**：`closeEvent` 中 `is_editing() or is_reusing()` 时 `QMessageBox.question` 确认，No → `event.ignore()` 拦截（`close()` 返回 False），Yes 继续落 settings 并关闭。测试 `test_close_while_editing_asks_confirmation` mock 确认框断言 close() 返回值；用例结束 `cancel_edit()` 恢复非编辑态，避免 fixture 收尾 close 在 offscreen 下触发真实模态框挂起（实现中踩坑：isHidden() 对从未 show 的顶层窗口恒为 True，改用 close() 返回值断言）。

### O-14: 7 日自动删除的可见性（候选）✅

- **类型**：功能（新增）/候选
- **优先级**：P2 — Worth exploring
- **文件范围**：`calculator.py`（`rotate_weekly`）、`app/main_window.py`
- **关联**：O-C2（7 日限制产品决策）
- **完成日期**：2026-08-01

**问题描述**：`rotate_weekly()`（`calculator.py:165`）静默删除最旧记录，滚动备份同步覆盖。间断录入（假期/出差）超过 7 个日期键后最早记录被永久删除，用户无感知。

**解决思路**：候选方案——删除前 `logger.info` + 状态栏可见提示；或将 7 日保留策略改为可配置/可关闭（触碰产品决策，需与 O-C2 一并拍板）。`Speculative`：是否引入「归档 / 历史视图」。

**实现说明**：拍板「仅可见性提示」（可配置/归档另立候选，未做）。`rotate_weekly` 改为返回被删除日期列表（升序），每条删除 `logger.info`；`save_today` 把「（自动清理 N 条超 7 天记录）」拼到已保存指示器，对用户可见。测试：`test_rotate_weekly_logs_deletion`（caplog）+ `test_save_triggers_rotation_hint`（8 条数据保存后提示 + 裁剪到 7 条）。

### O-15: 日志文件轮转 ✅

- **类型**：重构
- **优先级**：P2 — 顺手项
- **文件范围**：`main.py`（logging 配置）
- **关联**：O-01（日志通道）
- **完成日期**：2026-08-01

**问题描述**：`logging.basicConfig`（`main.py:67`）固定写 `profit_calculator.log`，长期运行单文件无限增长，无轮转。

**解决思路**：改 `RotatingFileHandler(maxBytes=1MB, backupCount=3)`（或按时间轮转）。纯配置改动，零逻辑影响；注意打包版无 stderr 场景下文件日志是唯一可见通道，勿降级日志级别。

**实现说明**：`main.py` logging.basicConfig → `RotatingFileHandler(maxBytes=1MB, backupCount=3, encoding="utf-8")`；根 logger 已有 handler 时不重复添加（幂等，与 basicConfig 语义一致）；日志级别保持 INFO。

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

### O 系列（2026-08-01，第二批 P1）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-08 | 保存前校验 cash ≤ warehouse 不变式 | 功能（新增校验） | 2026-08-01 | （随本提交） |
| O-09 | 加载时顶层 dict schema 校验 | 重构（健壮性） | 2026-08-01 | （随本提交） |
| O-10 | 打包配置纳入版本控制 | 运维 | 2026-08-01 | `20b5170` / `fa16d77` |

> 两个并行分支（A：O-01~O-03；B：O-04~O-05）经 merge 合入 main，合并提交 `c01c2c2` / `fdeca85`。合并时 `main_window.py` 模块级 logger 命名冲突（`logger` vs `_logger`）已收敛为 `logger`。

### O 系列（2026-08-01，第三批 P2）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-11 | CSV 导出金额统一格式化 | 重构（显示一致性） | 2026-08-01 | （随本提交） |
| O-12 | dev 依赖清单与版本锁定 | 运维 | 2026-08-01 | （随本提交） |
| O-13 | 编辑态关闭窗口确认 | 功能（新增） | 2026-08-01 | （随本提交） |
| O-14 | 7 日自动删除的可见性 | 功能（新增） | 2026-08-01 | （随本提交） |
| O-15 | 日志文件轮转 | 重构 | 2026-08-01 | （随本提交） |

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

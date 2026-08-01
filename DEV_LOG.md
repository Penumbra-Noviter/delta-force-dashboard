# DEV_LOG — 收益计算器开发日志

> **格式**：`YYYY-MM-DD` | `<操作>` | `<范围>` | `<描述>`
>
> 按时间倒序排列，最新条目在最前。

---

### 2026-08-01 | 运维 | .gitignore + settings.json | O-18 settings.json 运行态入库清理（出索引 + gitignore）

**O-18**（P2，运维）：`settings.json` 内容为运行时态（窗口几何 + theme 随切换翻转），仍在 git 跟踪导致每次改主题/拖窗口都污染提交 diff（`082ce62` 已附带提交一次翻转）。拍板选 **A**：
- `.gitignore` Runtime data 节 `data.json` 旁追加 `settings.json`；`git rm --cached settings.json` 出索引（磁盘文件保留，本次提交表现为 `deleted: settings.json`）。
- 运行态零变化：`_load_settings` 读磁盘，缺失/损坏返回默认 `{}`（O-09 保证），无需代码改动。
- 与 data.json 隔离惯例一致（`95b7eef`）；此后主题/几何改动不再进入提交。

**验证**：`git status` 确认 settings.json 已出索引且被 ignore；纯版本控制调整，未触碰代码，pytest 无影响。

---

### 2026-08-01 | 文档同步 | CODE_WIKI.md | O-19 CODE_WIKI 失同步修正（方法表/依赖版本/测试计数）

**O-19**（P3，文档）：`082ce62` 声称「同步 CODE_WIKI」但留下三处失实引用，本次以源码/实测为准一次性修正：
- §4.7 方法表：`rotate_weekly` 返回 `None` → `list[str]`（O-14 起返回被删除日期列表）；`get_weekly_records` → `recent_records`、`summary` 去 `end_date`（承接同批 O-17 重构）。
- §3 / §5.1 依赖：`PySide6>=6.6.0` / `pyqtgraph>=0.13.0` → `==6.11.1` / `==0.14.0`，pytest `==9.1.1`；§3 补 `requirements-dev.txt` 行。
- §7 测试计数：以 `pytest --collect-only` 实测为准（calculator 54→57、data_store 16→18、input_panel 12→18、ui_smoke 22/23→26 归一），合计 165→180；§7 覆盖范围补 O-08/09/11/13/14 用例描述。
- §一 / §6.1 / §7 / §十 中「7 日 / 7 天」表述统一为「最近 7 条 / 保留条数限制」，与 README/PROJECT_REFERENCE 同批同步。

**验证**：`pytest --collect-only` 确认逐文件计数与总数 180 一致；pytest 180/180 ✅。

---

### 2026-08-01 | 修复+重构 | calculator.py + main_window.py + tests | O-17 清理文案与轮转语义不符 + 显示基准统一为录入条数

**O-17**（P3，文案准确性）：`rotate_weekly` 按「记录数」轮转（保留最近 7 条），但保存提示写「（自动清理 N 条超 7 天记录）」——间断录入时暗示按日历年龄删除，误导。改「（已保留最近 7 条记录，自动清理 N 条较早记录）」；`rotate_weekly` logger「删除超期记录」改「删除最旧记录（保留最近 %d 条）」。

**显示基准统一为录入条数**（用户拍板，本次核心改动）：
- 现象：表格/图表/汇总此前走 `get_weekly_records(today, 7)`（最近 7 个日历天窗口），间断录入时保留在 data 的老记录（>6 个日历天前）从界面消失，表现为「按现实时间 7 天清出数据」。
- 改动：`get_weekly_records` → `recent_records(days)`（最近 days 条实际录入记录，按日期升序、无空位占位、跳过无效记录）；`MainWindow._get_records` / `logic.summary` 改用它；`summary` 去掉 `end_date` 参数，汇总标签「7日总盈亏」→「最近7条总盈亏」。轮转 `rotate_weekly` 维持按条数（本就正确），本次不改。
- 效果：间断录入时，保留的最近 7 条记录在清理前始终可见；超过 7 条时才删最旧。
- 测试：`get_weekly_records` 6 项 → `recent_records` 6 项（含 caps_to_days / skips_malformed）；`summary` 去掉 invalid_date、新增 `test_summary_caps_to_recent_days`（间断录入的较老记录不参与汇总）；`test_save_triggers_rotation_hint` 断言新文案。

**验证**：pytest 180/180 ✅。

---

### 2026-08-01 | 决策拍板 | TO-TICKETS + calculator.py | O-16 CSV 大额 K/M 精度（保持现状，文档注明取舍）

**拍板**：O-16（CSV 导出 ≥1e6 金额被 `format_money` 缩写为 K/M、丢失全值精度，Excel 不可求和）选 **A 保持现状**。
- A/B/C 三选项：A 保持现状（仅文档注明取舍）；B CSV 专用千分位全值（如 `1,234,567.89`，引号包裹，Excel 可求和但 pandas 默认读成字符串）；C 纯数值（如 `1234567.89`，Excel/pandas 开箱即算、实现最简、彻底移除 K/M 分支）。
- 理由：CSV 主消费场景为 Excel 人工查看，与界面显示一致优先于机器可读全值；B 的千分位逗号引号包裹是 pandas 默认解析的经典坑；C 为最优机器格式，留作后续「机器可读导出」备选。
- 落地：仅 `export_csv` docstring 补取舍说明，零行为变更；TO-TICKETS O-16 → ✅ 归档（新增「决策拍板」表）。
- 附：收益率列「转纯数值」仅在 B/C 下成立，随 A 一并搁置。

**验证**：`export_csv` 相关测试 7/7 通过（docstring 变更不触碰行为）。⚠️ 全量 pytest 当前红（16 failed + 27 errors）——并行 session 正重构 `calculator.py`（`get_weekly_records`→`recent_records`、`summary` 签名变更、`rotate_weekly` 语义），测试未同步，与本次 O-16 改动无关。

---

**评审结论**：`/code-review` 双轴评审 `082ce62`（O-11~O-15）。五张工单实现与规格全部对齐（Spec 轴 0 缺失、新测试 4 项全过），无阻断性缺陷。**对个人用户影响整体低-中**，无 P0/P1 级问题；仅有少量值得做的清理，已拆分为 O-16~O-19 录入活跃表。

**值得做的 4 项**（已录入 TO-TICKETS 活跃表，状态 📝）：
| Ticket | 问题 | 优先级 |
|--------|------|--------|
| O-16 | CSV 导出大额（≥1M）金额被 `format_money` K/M 缩写、精度丢失，Excel 无法求和 | P2（决策） |
| O-17 | 清理提示「超 7 天」与 `rotate_weekly` 记录数轮转语义不符 | P3 |
| O-18 | `settings.json` 运行态（几何/主题翻转）入库，污染 diff，与 data.json 惯例不一致 | P2 |
| O-19 | CODE_WIKI 失同步（`rotate_weekly` 签名 / 依赖版本 / 测试计数 165 vs 180） | P3 |

**归档清理（删除冗余）**：C5「（待提交）」→ `0c6b8e3`；O-06「（随本提交）」→ `0f16e1c`；O-08/O-09「（随本提交）」→ `d0af4d6`，消除归档表占位符冗余。

**评审中判定不值得做（未录入）**：theme.py 84 行调色板重写 + input_panel 按钮色（`082ce62` 越界改动，但为已合并且生效的个人主题偏好，回退属返工）；`rotate_weekly` 返回列表仅用 `len()`（Speculative Generality，列表被测试使用，无害）；`closeEvent` 缺 `QCloseEvent` 注解（微小，随下次 main_window 改动顺手补）；O-15 无测试（纯配置重构，可接受）。

**验证**：pytest 180/180 不受影响（纯文档/工单变更，未触碰代码）。

---

**O-11 | CSV 导出金额统一格式化**（重构）：
- `export_csv`：现金/仓库/较前日三列统一走 `format_money`（拍板：字符串格式与界面一致；代价是 Excel 中为文本不可直接求和）
- 改用 stdlib `csv` 模块生成（`lineterminator="\n"`），含千分位逗号的字段（如 `"¥1,234.56"`）自动引号包裹，Excel 正确分列
- 测试：原断言更新为 format_money 输出；新增 `test_export_csv_format_money_unified`（千分位引号包裹 + 消除 `0.30000000000000004` float 伪影）

**O-12 | dev 依赖清单与版本锁定**（运维）：
- `requirements.txt` 锁精确版本：`PySide6==6.11.1` / `pyqtgraph==0.14.0`（实测版本，配合 O-10 可复现 exe 构建）
- 新增 `requirements-dev.txt`：`-r requirements.txt` + `pytest==9.1.1`，新环境可精确复现测试

**O-13 | 编辑态关闭窗口确认**（功能）：
- `closeEvent`：`input_panel.is_editing() or is_reusing()` 时弹 `QMessageBox.question`「当前有未保存的编辑，确定退出？」，No → `event.ignore()` 拦截
- 测试 `test_close_while_editing_asks_confirmation`：mock 确认框断言 `close()` 返回值（No→False / Yes→True）；用例结束 `cancel_edit()` 恢复非编辑态，避免 fixture 收尾 close 在 offscreen 下触发真实模态框挂起（踩坑：`isHidden()` 对从未 show 的顶层窗口恒为 True，改用 close() 返回值断言）

**O-14 | 7 日自动删除的可见性**（功能）：
- 拍板「仅可见性提示」。`rotate_weekly` 改为返回被删除日期列表（升序），每条删除 `logger.info`；`save_today` 把「（自动清理 N 条超 7 天记录）」拼到已保存指示器
- 测试：`test_rotate_weekly_logs_deletion`（caplog）+ `test_save_triggers_rotation_hint`（8 条数据保存后提示 + 裁剪到 7 条）
- 「保留天数可配置」未做，如需另立候选工单

**O-15 | 日志文件轮转**（重构）：
- `main.py`：`logging.basicConfig` → `RotatingFileHandler(maxBytes=1MB, backupCount=3, encoding="utf-8")`；根 logger 已有 handler 时不重复添加（幂等）；日志级别保持 INFO（打包版无 stderr，文件日志是唯一通道）

**验证**：pytest 180/180（176 基线 + 4 新增）✅

---

### 2026-08-01 | O-08/O-09 | calculator.py + data_store.py + app/* | 现金≤仓库不变式校验 + 加载顶层 dict 校验

**O-08 | 保存前校验 cash ≤ warehouse 不变式**（功能）：
- `save_today()`：解析出 `cash > warehouse` 时 `QMessageBox.warning`「数据不合逻辑」并中断保存（UI 层硬拦截）
- `InputPanel`：新增 `_update_invariant_state()`，跨字段检查挂在 `_update_save_btn_state`（每次字段校验后）；`MoneyLineEdit` 新增公开 seam `set_invariant_warning()`，越界时两输入框置 `validity="warning"` 态
- `app/theme.py`：新增 `BORDER_WARNING` 色（light amber-600 / dark amber-200）+ `QLineEdit[validity="warning"]` QSS
- `calculator.py`：业务层 `save_record` 仅 `logger.warning` 不拦截（允许保留已录入的异常数据并继续展示——拦截由 UI 层负责）
- 测试 +6：越界警告边框 / 恢复自然态 / 边界相等不触发 / 空字段不触发 / 越界保存被拦截 / 边界相等允许

**O-09 | 加载时顶层 dict schema 校验**（健壮性）：
- `data_store._try_load`：`isinstance(data, dict)` 校验，合法 JSON 但顶层非 dict（如 `[]`）视为损坏 → 走备份恢复链（此前会 AttributeError 崩溃且备份链不触发）
- `main_window._load_settings`：顶层非 dict 返回默认 `{}` + warning 日志
- 测试 +3：data 顶层 list 触发备份恢复 / 全 list 返回空 / settings 顶层 list 返回默认

**连带修复（测试夹具 bug）**：`tests/` 中 `DataStore(tmp_path/data.json)` 未传 `backup_file` → 默认指向真实 `data.json.bak*`；`load()` 的备份恢复链读取真实备份并 `_atomic_write` 到 tmp_path、`save()` 把测试数据写回真实备份（静默污染用户备份）。修复：显式传 `backup_file=tmp_path/data.json.bak`（test_input_panel + test_ui_smoke 共 6 处）。⚠️ 此前测试运行已把测试态数据写入真实 `data.json.bak*`（含虚假今日记录），待用户确认后从 `data.json` 恢复。

**验证**：pytest 176/176（166 基线 + 10 新增）✅ | `data.json.bak*` mtime 不再变化（夹具隔离生效）

---

### 2026-08-01 | 评审录入 | TO-TICKETS | 架构评估 O-08~O-15 候选落库

**变更**：多维度架构评估（架构/数据可靠性/测试/打包/流程）8 项发现整理为活跃工单 O-08~O-15 录入 TO-TICKETS（仅录入，不实施）：

| Ticket | 问题 | 优先级 |
|--------|------|--------|
| O-08 | 保存不校验 cash ≤ warehouse 不变式 | P1 |
| O-09 | 加载不校验顶层 dict，坏结构启动崩溃 | P1 |
| O-10 | 打包配置（spec + ico）未纳入版本控制 | P1 |
| O-11 | CSV 导出差值裸写 float，显示不一致 | P2 |
| O-12 | dev 依赖（pytest）未记录、依赖未锁版本 | P2 |
| O-13 | 编辑态直接关窗数据静默丢失 | P2 |
| O-14 | 7 日自动删除不可见（候选，关联 O-C2） | P2 |
| O-15 | 日志文件无轮转 | P2 |

**建议顺序**：O-08/O-09 优先（P1，数据完整性 + 启动健壮性）；O-10 打包配置入库与图标改动（`main.py` + `app_icon.ico` + 文档，见下条）未提交的变更一并处理。

**验证**：pytest 166/166 ✅（评估后基线）

---

### 2026-08-01 | 打包 | dist/收益计算器.exe + app_icon.ico | 应用图标落地（exe 文件 + 运行窗口）

**变更**：
- `收益计算器.spec`：`EXE(icon='app_icon.ico')` 设置 exe 文件图标；`datas=[('app_icon.ico', '.')]` 内嵌图标（单文件版解压后供运行时读取）
- `main.py`：新增 `_icon_path()`（打包版从 `sys._MEIPASS`、源码版从项目根目录解析）+ `app.setWindowIcon()` 设置窗口/任务栏图标
- `app_icon.ico`：项目根目录新增图标（16~256px 多尺寸，来源 `D:\steam\...\8acb6477....ico`，用户指定）

**验证**：pytest 166/166 ✅ | exe 启动烟测通过（双进程常驻 + 单实例锁）| 从 exe 提取图标与源文件一致 ✅

---

### 2026-08-01 | O-06/07 | app/chart_widget.py | 图表稀疏提示落地 + O-07 关闭

**O-06 | 图表稀疏数据提示**（功能）：
- `ChartWidget.draw()` 中 `2 <= n <= 3` 时叠加半透明提示「数据较少，需更多数据以显示趋势」——避免刚开始用 app 的头两三天图表只有 2~3 个点、被误读为图表损坏
- 新增 `_show_sparse_hint()`：overlay QLabel 不入 layout，作为顶层子控件覆盖图表；`WA_TransparentForMouseEvents` 保证鼠标事件透传给图表（不触碰交互）；与 `_placeholder_label` / `_clear_placeholder` 共用生命周期；`resizeEvent` 同步跟随 widget 尺寸
- 测试 +1：`test_chart_sparse_data_hint`（n>=4 无提示 / n=3、2 有提示且不拦截鼠标 / n<2 回归占位）

**O-07 | 收益率目标参考线**（关闭，YAGNI）：
- 目标语义未定义：「收益率」为逐日环比（较前日），图表只画现金/仓库两条金额曲线、无收益率曲线，目标线画在哪条序列上无法解释
- 实现需输入框 + settings 持久化 + InfiniteLine + 测试，成本高于收益，参照 O-C 系列先例关闭

**验证**：pytest 166/166（165 基线 + 1 新增）✅

---

### 2026-08-01 | 打包 | dist/收益计算器.exe | 重新打包（含 O-01~O-05）

**产物**：`dist/收益计算器.exe`（83.3 MB，单文件，PyInstaller `--clean` 重建）

**验证**：
- pytest 165/165 通过 ✅
- exe 启动烟测通过：双进程常驻（PyInstaller 单文件父子结构）→ 二次启动被单实例锁拦截（进程数保持 2）→ 强制结束干净退出 ✅
- `profit_calculator.log` 日志通道就绪：O-01 的 `logging.basicConfig` 按 warning 惰性写文件，无异常时不生成文件属预期
- `dist/` 残留 `settings.json`（上次烟测遗留）已清理

---

### 2026-08-01 | O 系列（并行分发）| 全项目 | O-01~O-05 优化落地

**模式**：O-04/05 论证不依赖 O-01~O-03，分两个 worktree 并行开发（A：O-01~O-03；B：O-04~O-05），合并冲突仅一处（`main_window.py` 模块级 logger 命名 `logger`/`_logger` → 收敛为 `logger`）。

**O-01 | logging 替换静默 except**（`e6d5b64`，重构/可观测性）：
- `app/main_window.py` `_load_settings` / `_save_settings`、`data_store.py` `_rotate_backups` 三处 `except: pass` → `logger.warning("...: %s", e)`
- `main.py` 新增 `logging.basicConfig` 写 `APP_DIR/profit_calculator.log`（打包版窗口化 exe 无 stderr，文件日志是唯一可见通道）
- 保留不动：`_setup_window` 几何恢复/DPI 的 `except Exception: pass`（工单外）；`calculator.py`/`data_store.py` 中 `return None` 的正常语义 except
- 测试 +3：`test_rotate_backups_logs_warning_on_failure` / `test_load_settings_corrupt_logs_warning` / `test_save_settings_failure_logs_warning`

**O-02 | MoneyLineEdit.refresh_validity 公开 seam**（`486d41f`，重构/seam）：
- `MoneyLineEdit` 新增公开 `refresh_validity()` 委托私有 `_update_validity()`；`InputPanel.refresh_validity()` 改调公开方法——C4 公开 seam 体系漏网的最后一处跨对象私有访问收敛
- 测试 +2：公开 seam 行为（valid/invalid/normal）+ AST 守卫（防 InputPanel 直调 `_update_validity` 复发，C9 风格）

**O-03 | format_money docstring 阈值交叉说明**（`ac75c71`，文档）：docstring 补「与 `format_compact` 不同，此处 K 阈值为 1,000,000 而非 1,000」，与 C3 侧形成双向引用。纯注释。

**O-04 | CSV 数据导出**（`8f50592`，功能）：
- `calculator.py` 新增公开纯函数 `ProfitCalculatorLogic.export_csv()`：列 `日期,现金,仓库,较前日,收益率`，日期升序，较前日/收益率复用 `calculate_rate`/`format_rate` 语义（总收益 = 仓库已含现金），无前日数据为 `—`，异常记录跳过
- `app/main_window.py` 标题栏新增 `export_btn`「导出 CSV」+ `QFileDialog` 选路径，`utf-8-sig` + `newline=""` 写入（Excel 可直接打开），失败弹 `QMessageBox.warning` + 记日志，成功 `set_saved_indicator("✓ CSV 已导出")`
- `app/theme.py` `exportBtn` 并入 themeBtn/pinBtn QSS 按钮组
- 测试 +10：纯函数 6（空/表头/单条/多条/升序/异常跳过）+ UI 4（按钮存在/utf-8-sig BOM/取消不写/失败警告）

**O-05 | 今日未录入提醒**（`749cd59`，功能）：
- `app/main_window.py` 标题栏新增 `_today_status_label`「今日未录入」，`_update_today_status()` 纯读 `logic.get_record(self.today)` 控制显隐，挂在 `refresh_display()`（启动/保存/删除/主题切换均刷新）
- `app/theme.py` 新增 `QLabel#todayStatusLabel` QSS（`fg_today` 强调色）
- 测试 +3：未录入可见 / 保存后隐藏 / 已有记录隐藏

**验证**：pytest 165/165（147 基线 + 18 新增）✅ | 提交 `e6d5b64`/`486d41f`/`ac75c71`/`8f50592`/`749cd59` + merge `c01c2c2`/`fdeca85`

---

### 2026-08-01 | C5 | tests/ + 全项目 | verify_all 影子测试并入 pytest

**变更**：
- 盘点 `verify_all.py` 14 节，确定迁移顺序：
  - 第 1~3 节（calculator/formatting/datastore 叶子测试）→ 已被 `test_calculator.py`/`test_formatting.py`/`test_data_store.py` 覆盖，直接删除
  - 第 4~11、13~14 节（UI 烟测）→ 迁移至新文件 `tests/test_ui_smoke.py`（offscreen，参照 `test_table_theme.py` 首个 Qt fixture）
- 迁移改造点（深度私有访问 → 公开 seam，C4 契约）：
  - 保存：`cash_entry.setText()` → `input_panel.fill_values()`（公开）
  - 编辑：`win._start_edit()` → `input_panel.set_edit_mode()`（公开）
  - 删除：`win._delete_record()` → `table.delete_requested.emit()`（公开信号）
  - 主题/置顶：`win._toggle_theme()`/`_toggle_pin()` → `theme_btn.click()`/`pin_btn.click()`
  - 输入校验：去抖 QTimer 异步 → 用 C4 seam `refresh_validity()` 同步断言
  - 失焦格式化：手动模拟 → 派发真实 `focusOutEvent`
  - 几何恢复：旧格式 `680x900+100+50` 与空 geometry 两种恢复无 crash
- 删除 `verify_all.py`（831 行影子脚本）；settings.json 隔离、data.json 备份/恢复逻辑随之移除（pytest fixture 天然隔离，不再需要手动 backup/restore）
- 文档同步：`CODE_WIKI.md`（7.1 用例数更新 + 7.2 改写为 pytest 烟测表 + 文件树 + 顶部测试状态）、`CONSENSUS.md`（4.3 验收标准）

**验证**：pytest 147/147（134 既有 + 13 新增）✅ | `git status` 无 settings.json/data.json 污染

---

### 2026-08-01 | C5 评审修复 | tests/ + README + PROJECT_REFERENCE | code-review 后续修复

**变更**（对应 C5 评审发现，`/code-review` 双轴报告）：
- 修复时间耦合回归（Spec 关键项）：`make_sample_data()` 由固定日期（2026-07-20~27）
  改为相对今天生成（offsets 7/6/5/3/2/0），样本日始终落在 `[today-6, today]` 窗口内，
  `test_ui_initialization` 的 `present > 0` 断言不再于 2026-08-03 后必失败；
  编辑/删除测试改为从 `logic.data` 动态取日期，不硬编码样本日
- 公开 seam 收敛：`test_settings_persistence` 改用 `win.close()`（closeEvent 落盘）
  替代私有 `_save_settings()`；theme 断言由 `!= "light"` 恢复为 `== "dark"`（fixture 确定态）
- fixtures 去重：`qapp`（3 处）/`settings_guard`（2 处）收敛到 `tests/conftest.py`，
  `test_table_theme`/`test_input_panel`/`test_ui_smoke` 删除本地副本
- 文档勘误：节号 `13~15`→`13~14`（verify_all 实际 14 节，本日志 + `test_ui_smoke.py` docstring/节标题）、
  verify_all 行数 `825`→`831`、README 测试数 103→147、PROJECT_REFERENCE `116 项`→147
  + 第四/八节 UI 测试描述改写（原「当前无 UI 测试」已过时）

**验证**：pytest 147/147 ✅

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

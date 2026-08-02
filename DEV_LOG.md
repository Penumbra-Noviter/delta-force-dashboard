# DEV_LOG — 收益计算器开发日志

> **格式**：`YYYY-MM-DD` | `<操作>` | `<描述>`（倒序，最新在前）
>
> 工单标题/完成日期/提交哈希以 `TO-TICKETS.md` 归档表为准；本日志只记「已做」与决策/避坑。

---

## 滚动摘要（2026-08-03）

- **J 系列**：记录保留上限 7→30（`RETENTION_LIMIT`）+ 视图 7/30 可切换（`TableWidget` 按钮组 + `view_changed` 信号），存储与视图解耦、切回 7 不丢数据；ADR-0003 落档，详见日志正文
- **打包**：主分支重新打包（J-01/J-02 后），`dist/收益计算器/` 64M；**未烟测**（用户指示本次不启动 exe 验证，详见日志正文）
- **测试**：pytest **237/237** ✅（2026-08-03 J 系列视图切换 UI 用例 +3、summary/format_summary 参数化纯函数 +2）
- **图表**：样式对齐原型评审修正版（0559537）——删填充区域、hover 改「系列短名+值、按所属 ViewBox 顶部堆叠定位」；布局把曲线图置底固定高度、表格改弹性区，为后续 7/30 天记录预留高度（用户预告将记录天数设为 7/30 天）
- **布局**：图表卡片 `setMaximumHeight(220)` 封顶（PlotWidget sizeHint 480 吃掉纵向空间），880 窗口下表格 107→367px（详见日志正文）
- **活跃工单**：见 TO-TICKETS 归档表（G-01 图表样式对齐已归档为 H-01）

---

## 日志正文

### 2026-08-03 | 调整 | 图表卡片封顶高度，给表格让出纵向空间
- 问题：图表卡片无上限，PlotWidget 默认 sizeHint **480px** 生效 → 图表卡片 502px，880 窗口下表格只剩 ~107px
- 修复：`main_window.py` 图表控件 `setMaximumHeight(220)`（配合既有 `setMinimumHeight(140)`，区间 [140,220]，卡片含边距约 242px）；`test_ui_initialization` 最小高断言随窗口收紧同步 700→650
- 验证：offscreen 实测 880 窗口表格 107→**367px**（1000 窗口 →487px）；pytest **237/237** ✅；`doc_sync --check` 通过

### 2026-08-03 | 打包 | 主分支重新打包（J-01/J-02 视图切换后，含 J 系列改动）
- 命令：`pyinstaller 收益计算器.spec --noconfirm --log-level=WARN`（UPX 在 PATH）
- 产物：`dist/收益计算器/` **64M**（exe 6.56MB + `_internal/`）；J 系列改动（`calculator.py`/`config.py`/`app/table_widget.py`/`app/main_window.py`）编译入 PYZ，spec 无需变更（无新资源/依赖）
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 分发前确认：dist 内无运行态数据（data.json/settings.json/log 均缺），`app_icon.ico` 内嵌
- **未烟测**：用户指示本次不启动 exe 验证；源码态 pytest 237/237 ✅ + 打包 exit 0（如需冒烟，启动 `dist/收益计算器/收益计算器.exe` 观察进程存活与日志）

### 2026-08-03 | 实现 | J-01 保留上限 7→30 + J-02 视图 7/30 切换（ADR-0003，存储/视图解耦）
- 需求：用户「记录天数上限 7→30 + 多视图切换」（Grilling Q1–Q11 收敛，`CONSENSUS.md` §7）。核心=把**保留 Retention**与**视图 View**解耦
- **J-01（数据模型）**：`config.py` 新增 `RETENTION_LIMIT=30`（保留上限），`rotate_weekly()`/`format_saved_indicator()` 默认改引用它——`rotate_weekly` 保留边界「满 30 不删、第 31 条才删最旧」（Q11）；清理文案「已保留最近 30 条记录」
- **J-02（UI）**：`TableWidget` 加 7/30 按钮组（`QButtonGroup` + `QRadioButton`）+ `view_changed(int)` 信号 + 持有 `_view_days`（Q6/Q8 深模块——表格是视图窗口主人，MainWindow 只订阅）；分栏均分 `mid=ceil(n/2)`（Q7：7→4+3、30→15+15）；`MainWindow` 持 `_view_n`（启动默认 7，会话内存不持久化 §7.5）、`_get_records`/`_update_summary` 去硬编码 `WEEK_DAYS` 改走 `_view_n`；切视图 `_on_view_changed → refresh_display`，表格+曲线图+汇总同源联动（Q9/Q10）
- 测试：`test_ui_smoke.py` +3（默认视图 7+按钮组状态 / 切 30 信号+15+15+汇总「最近30条」 / 切回 7 不丢存储 Q5）、`test_calculator.py` +2（`format_summary(days=30)` 前缀 / `summary(7)` vs `summary(30)` 窗口参数化）；rotate_weekly 既有用例改 30 上限
- 文档：ADR-0003 落档（可选方案 A 纯扩容/B 解耦/C 日历口径 → 选 B）；CODE_WIKI/PROJECT_REFERENCE/README 同步「最近 30 条 + 视图 7/30」文案；doc_sync 刷新机械标记
- 验证：pytest 237/237 ✅；`doc_sync --check` 通过

### 2026-08-03 | 打包 | 主分支重新打包（H-01 图表样式 + G-01 双轴合并后，含图表改动）
- 命令：`pyinstaller 收益计算器.spec --noconfirm --log-level=WARN`（UPX 在 PATH）
- 产物：`dist/收益计算器/` **64M**（exe 6.5MB + `_internal/`）；H-01/G-01 图表改动（`chart_widget.py`/`main_window.py`）编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 分发前确认：dist 内无运行态数据（data.json/settings.json/log 均缺）
- 烟测：exe 启动 8s 进程存活后终止 ✅（无启动崩溃）；pytest 231/231 ✅

### 2026-08-03 | 重构 | 图表样式对齐原型评审修正版（0559537）+ 布局：曲线图置底为表格预留
- 需求：将 G-01 落地图改为「原型最后设计的样式」，并把曲线图移至最下方，为后续 7/30 天表格预留高度（用户预告将记录天数设为 7/30 天）
- 样式对齐 `prototype/chart-merge` 评审修正版（提交 `0559537`）：
  - **删填充区域**：`FillBetweenItem` 两条全删（`_warehouse_fill`/`_cash_fill` 及其 `__init__`/`_create`/`apply_theme`/`_clear_all` 触点），双轴合并图只留曲线+端点
  - **hover 对齐原型 `_attach_crosshair`**：从「日期+数值贴数据点」改为「共享竖线 + 每系列一个彩色数值标签」，文案「系列短名 + 值」；标签按**所属 ViewBox** 的顶部堆叠定位（`ymax - span*(0.06+0.10j)`，span 兜底量纲归零）——因跨轴不可比，标签只叠放数值不贴数据点不比较线段
  - 新增 `_hover_views`/`_hover_series` 记录每个标签所属 ViewBox 与系列配置（短名/颜色键）
- 布局（`main_window.py`）：`table_card` 改 `stretch=1`（弹性区，随窗伸缩，为 7/30 天记录预留高度）；`chart_card` 改 `stretch=0` + `new ChartWidget().setMinimumHeight(220)` 置底固定高度，不随窗口扩张
- 测试：新增 `test_chart_dual_axis_no_fill_and_hover_views`（无填充 + 双 hover 标签/所属 ViewBox/系列），231/231 ✅
- 文档：CODE_WIKI §4.5 去「填充」叙述 + 增「hover 交互」说明；doc_sync 刷新机械标记

### 2026-08-02 | 功能 | G-01 图表双曲线合并到同一坐标系（双 Y 轴，方案 B，ADR-0002）
- 需求：把「仓库价值 + 现金」上下双图合并进同一坐标系（原 `_ChartPanel` 双面板结构）
- 流程：O-C2「评审×原型双驱动」——先 `/prototype`（UI 分支，QComboBox 切 A 单轴/B 双轴/C 归一化 4 视图），offscreen 渲染 + PIL 像素扫描验证：
  - A 共享单轴：现金线仅 16px 高（量级 ~20 倍差被压扁）❌
  - B 双 Y 轴：两线均占满图高 ✅ **拍板**
  - C 归一化：丢绝对值（¥10→12 与 ¥1M→1.2M 同高）❌
- 实现：`chart_widget.py` 重写——单 PlotWidget + 主 ViewBox（仓库/左轴）+ 副 ViewBox（现金/右轴，`setXLink`+`linkToView` 共享 X）；`_sync` 闭包固化 resize 同步坑位；图例显式注册双曲线（副 ViewBox 项目不自动进主 PlotItem 图例）；端点标注/hover 双值/PNG 导出/主题切换全保留；`_ChartPanel` 删除
- 避坑记录（ADR-0002）：跨轴高度不可比、右轴刻度须与曲线同色、resize 漏同步两线 x 错位
- 测试：新增 `test_chart_dual_axis_merged`（双 ViewBox 归属 + 右轴链接 + 图例双项），230/230 ✅
- 文档：CODE_WIKI §4.5 重写（去 `_ChartPanel`）+ 依赖表修正（去 numpy，加 formatting）+ ADR-0002 + TO-TICKETS G-01 归档
- 原型留存：throwaway 分支 `prototype/chart-merge`（`b6800bb`），主分支不含原型文件

### 2026-08-02 | 打包 | 主分支重新打包（F-01/F-02 后，含 .migrated 标记 + 清理提示）
- 命令：`pyinstaller 收益计算器.spec --noconfirm --log-level=WARN`（未显式 `--upx-dir`，UPX 已在 PATH）
- 产物：`dist/收益计算器/` **64M**（exe 6.5MB + `_internal/`）；F-02 `.migrated` 标记 + `log_legacy_cleanup_hint` 编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（`No module named 'OpenGL'`，可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（无启动崩溃）；pytest 229/229 ✅

### 2026-08-02 | 修复 | F-01 安装脚本 install-hooks.bat 括号转义 bug + CRLF 行尾
- 背景：安装钩子被权限分类器拦下（写入 `.git/hooks` 属持久化动作），授权代跑时发现 `cmd /c scripts\install-hooks.bat` 恒静默 exit 1——钩子能装、验证脚本却永远报失败
- 根因（cmd 经典陷阱）：`echo ... (not a git repo root?)` 内未转义 `)` 提前闭合 `if not exist (...)` 块，第 13 行 `exit /b 1` 无条件执行，成功路径也被 1 退出；另行为 LF 且 `.bat` 无 CRLF（`type` 正常但块解析易踩边界）
- 修复：`scripts/install-hooks.bat:12` 括号转义 `^(...^)`；行尾统一 CRLF
- 验证：`cmd //c "scripts\\install-hooks.bat"` → exit 0；`.git/hooks/pre-commit` 与 `scripts/pre-commit.sh` 字节一致；`sh .git/hooks/pre-commit` → exit 0（`doc_sync --check` 通过）
- 纯运维修复，pytest 229/229 不受影响；随 F-01 提交 `fc28fff` 一并入库

### 2026-08-02 | 运维 | F-01 文档同步自动化：scripts/doc_sync.py + pre-commit 防漂移钩子
- **背景**：`CODE_WIKI` §7 测试表各文件用例和 214 ≠ 实际 pytest 221、漏 `test_migration.py`——手工表格已多次漂移（复盘 3.6 教训现场）
- **工具**：`scripts/doc_sync.py`（纯 stdlib，秒级）生成三类机械标记：① `lines:<module>` §4 标题 `（~N 行）`= 非空行计数；② `tests:<test_file>` §7 用例数 = 解析 `pytest --collect-only -q`（实际收集口径，含参数化）；③ `sig:<module>:<symbol>` §4 方法签名 = AST 提取（剥 self/cls、渲染默认值、property 无括号）。`--check` 比对现文 + 结构校验（tests/lines 双向覆盖 + sig 符号存在性），漂移 exit 1；无参模式就地刷新现有标记
- **钩子**：`scripts/pre-commit.sh`（跑 `--check` 拦截漂移）+ `scripts/install-hooks.bat`（复制到 `.git/hooks/pre-commit`，不入库）；已手动验证：同步 → exit 0、故意篡改行数 → exit 1 拦截
- **CODE_WIKI 基线同步**：插入 133 个标记；修复漂移——§7 补 `test_doc_sync` 行（§7.1 单测表）、§4.5 chart_widget 方法表重写（`_create_chart`/`_update_chart`/`_update_theme_colors` 三陈旧方法 → `_ChartPanel` 面板类 + 新 ChartWidget 方法表）、§4.10 补 `format_compact`/`format_short_date`、§3 文件树补 `scripts/`、§4 行数全部对齐实测值；`--update` 收敛 11 处签名（如 `MainWindow.__init__(store=None, logic=None, settings_store=None)`）；新增 §8.5 文档同步说明
- **边界（规模悖论）**：只自动「数字/签名类」机械标记，不生成叙述性文字；工具脚本只加 1 个冒烟测试（`tests/test_doc_sync.py`：`doc_sync.py --check` rc==0 即基线同步锁死），不堆数量
- 测试：+1；pytest 229/229 ✅（228+1）
- TO-TICKETS F-01 → ✅ 归档（2026-08-02，提交 `fc28fff`）

### 2026-08-02 | 运维 | F-02 数据迁移「源清理时间点」策略：.migrated 标记 + 启动提示
- `migrate_legacy_data` 迁移成功后写 `.migrated` 完成标记到目标数据目录（幂等）；目标已有 `data.json` 视为已权威同样补写标记（覆盖 F-02 上线前已迁移用户）
- 新增 `log_legacy_cleanup_hint`：`.migrated` 标记存在且旧源 `data.json` 仍在 → info 日志「旧数据源可手动清理：<路径>」；`main.py` 迁移后调用
- **安全原则**：脚本绝不自动删源，删除是用户确认后的手动动作；CODE_WIKI §4.9/§8.4 记策略「源清理时间点 = 目标数据确认健康之后，用户确认后手动执行」
- 测试 +7（标记写入/目标已权威补写/二次幂等/无旧数据不写 + 清理提示 3 态）；test_migration 7→14；pytest 228/228 ✅
- TO-TICKETS F-02 → ✅ 归档（2026-08-02，提交 `fc28fff`）

### 2026-08-02 | 待办 | 复盘反思评估 → F 系列工单录入（TO-TICKETS）
- 来源：`D:\Desktop\knowledge base\demo\experience\收益计算器项目经验复盘.md` 五、复盘反思（5 条可提升方向）
- 评估：① **文档同步自动化 ✅ 值得做**——实测 `CODE_WIKI` §7 测试表各文件用例和 214 ≠ 实际 pytest 221，且漏 `test_migration.py`，手工同步又漂移（正是 3.6 教训现场）→ 录 **F-01**；④ **数据迁移源清理时间点 ✅ 值得做**——O-22 复制非移动的源清理时间点模糊（E-04 本机残留已清），转为前瞻性策略 → 录 **F-02**
- 不建工单：② 提交前 code-review——交互式 skill 无法进 git 钩子，习惯已由流程覆盖，可行自动化（AST 守卫 + doc-sync）并入 F-01；③ 并行开发命名/接口先约——流程约定，O 系列合并教训已留痕，无需代码；⑤ 规模悖论——原则性边界，作为后续工单验收标准（覆盖真实路径 + 防复发，不堆测试数量）
- 现状核对：根目录 `data.json.bak*` 4 份（E-04 暂缓项）已清空，无残留；`~/收益计算器/` 数据自足健康
- 2026-08-02 拍板：F-01 / F-02 均采纳（待开发）；本次 TO-TICKETS / DEV_LOG 变更**未提交**（用户指示，工作区保留）

### 2026-08-02 | 运维 | 项目评估报告核对 + E 系列工单收口
- 背景：外部 AI 评估报告（`项目评估报告.md`，8.80/10）与 HEAD 逐条核对——3 条 P1 中 2 条已存在（纯函数 docstring / ADR 文档），1 条论据过期（其引用的 `DATA_RETENTION_DAYS` 常量 O-17 已删）；报告文件已不在工作区（用户自行处理，git 零引用）
- 拍板（用户）：E-01 保留天数可配置 **关闭**（不知配置对用户实际作用）；E-02 操作审计日志 **关闭**（单用户无追责场景 + 覆盖写日志留不下旧值，救不了撤销）；E-03 图表脚本化导出 **关闭**（不需要，YAGNI）；E-04 陈旧产物清理 **授权**（已录入 TO-TICKETS 活跃表 🔄）
- E-04 执行：删 5 个 stale pyc（`app/__pycache__/` 下 logic/data_store/formatting/config + 根 `verify_all`——C5/D 系列重构残留，gitignore 已忽略无害）+ 根目录旧 `profit_calculator.log`（O-22 前 APP_DIR 日志，现日志在 `~/收益计算器/`）
- ⚠️ **根目录 `data.json.bak*` 4 份暂缓**：核对发现值差异——bak 含 07-24 唯一记录、07-25/08-01 数值与权威 `~/收益计算器/data.json` 不同（疑 O-08 测试污染或旧快照）；权威数据自足健康（含当日 08-02 记录 + 完整备份链），07-24 系 08-02 保存时正常轮转删除。用户确认后删除（E-04 归档）
- pytest 221/221 不受影响（纯运维 + 文档）

### 2026-08-02 | 打包 | 主分支重新打包（D-08 后，含 signals.py）
- 命令：`pyinstaller 收益计算器.spec --noconfirm --log-level=WARN`（未显式 `--upx-dir`）
- ⚠️ UPX 现已在 PATH：WinGet 安装的 `upx 5.2.0`（`C:/Users/.../WinGet/Packages/UPX.UPX.../upx.exe`），spec `upx=True` 自动命中，无需再显式传 `--upx-dir`（滚动摘要第 12 行旧避坑已过时，保留为无 PATH 环境的兜底）
- 产物：`dist/收益计算器/` **64M**（exe 6.5MB + `_internal/`，与 O-21 UPX 后持平）；`signals.py` 编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（`No module named 'OpenGL'`，可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 6s 进程存活后终止 ✅（无启动崩溃）

### 2026-08-02 | 修复+文档 | D-08 D 系列评审修正：signals 叶子收敛 + 告警可观测性 + 文档漂移
- **① 层反转修复（唯一设计分叉）**：`RateSignal`/`PnLSignal` 自 `calculator.py` 抽至新零依赖叶子 `signals.py`；`theme.py`/`table_widget.py`/`main_window.py`/`calculator.py` 改从叶子导入——`theme.py` 不再反向依赖业务层，保住 D-01 的 `signal_color` 收敛（评审：theme.py 依赖图「无外部依赖」陈）。
- **③ 读取告警异常详情恢复**：`json_file.try_load_json` 加可选 `on_error: Callable[[Exception], None]` 回调（seam 的自然错误通知口）；`SettingsStore.load` 经回调恢复 D-02 前逐字文案「设置文件读取失败（使用默认设置）: %s, e」。
- **⑤ 跳过记录可观测**：`__init__` 对每条丢弃记录 `logger.warning("跳过损坏/非法记录（%s）", date_str)`（O-01 不允许静默）；ADR-0001 后果段 + CODE_WIKI §4.7 明示磁盘侧自愈清除（下次保存不再写回）。
- **④/② 文档漂移修正**：PROJECT_REFERENCE 「D-01~D-03/208 项」→「D-01~D-07/221 项」；CODE_WIKI §5.3 依赖表（theme/input_panel/main_window/calculator 行 + 新增 signals 行）、§5.2 依赖图、§4.6 函数表补 signal_color/get_color/set_theme、§3 文件树、§2.1 分层图、新增 §4.13 signals.py；README 计数 217→221。
- 测试：+4（try_load_json on_error 2 / SettingsStore 异常详情 1 / 加载跳过记录 warning 1）；pytest 221/221 ✅（217+4）；test_calculator 73、test_settings_store 18。

### 2026-08-02 | 重构 | D-05 现金⊆仓库不变式单一所有者：is_cash_under_warehouse 纯函数
- `ProfitCalculatorLogic.is_cash_under_warehouse(cash, warehouse) -> bool`（True=不变式成立）；告警（save_record）/ 拦截（save_today）/ 红框（input_panel）三处字面量 `cash > warehouse` 改调用，语义零变化
- 测试：+3（成立 / 相等边界 / 违反）；pytest 213/213 ✅

### 2026-08-02 | 重构 | D-06 删浅表面：DayRecord.total 删除
- 删 `DayRecord.total` property（生产零引用真死代码）；test_calculator 4 个专属测试删除 + 1 处冗余断言删除 + 3 处断言改 `.warehouse`
- 文档：CODE_WIKI 属性表/关键规则/注意事项、PROJECT_REFERENCE 坑点条目改注「现金⊆仓库不变式」语义
- 测试：-4；pytest 209/209 ✅

### 2026-08-02 | 重构 | D-07 展示渲染移出编排器：format_summary + format_saved_indicator 纯函数
- `ProfitCalculatorLogic.format_summary(count, total, days=7) -> (str, RateSignal)`：数据不足/仅 1 条→NONE（灰字弱化），≥2 条走 format_signed_money；`format_saved_indicator(save_date, warehouse, today, deleted) -> str`：今日/已更新 + 轮转清理提示（O-14/O-17 文案）
- `_update_summary` 只留信号→颜色映射与样式落地（颜色映射留 UI，依赖 D-01 信号 seam）；save_today 指示器改调用纯函数
- 测试：+8（format_summary 5 + format_saved_indicator 3）；pytest 217/217 ✅

### 2026-08-02 | 测试重构 | D-04 被测试的路径=真实路径：QTest 打事件链路（`cfb15e1`）
- 校验/联动断言不再把 `refresh_validity()` 当测试后门：conftest 新增 `type_and_settle` fixture（QTest `keyClicks` 键入 → 150ms 去抖 → `validity_changed` → save_btn 真实链路）；test_input_panel 校验/不变式 5 用例 + test_ui_smoke `test_input_validation_save_btn` 全改走它
- `refresh_validity` 保留为同步 seam（主窗口 Esc 清空等程序化改动用，`_clear_focused_input`），只留 `test_money_line_edit_public_refresh_validity` 单一契约测试
- 焦点事件收敛到真实路径：test_input_panel 新增 `shown_panel` fixture（offscreen 下 setFocus 焦点事件只对可见窗口派发）；新增聚焦反格式化护栏（`¥123,456.00`→`123456`+全选）/ 失焦立即校验（非法文本不等去抖）/ 失焦格式化 3 用例；test_ui_smoke 同名直派 `focusOutEvent` 用例迁入删除（-1）
- 测试：+2（208→210）；test_input_panel 18→21、test_ui_smoke 23→22；3 连跑稳定；CODE_WIKI 方法表/文件树/测试表同步（顺带修正 test_calculator 61→65、test_table_theme 3→4 两处既有漂移）
- 纯测试改动，无生产代码变更；pytest 210/210 ✅

### 2026-08-02 | 重构 | D-03 序列化边界：data→dict[str, DayRecord] + serialize()（ADR-0001，`54a23d0`）
- `ProfitCalculatorLogic.data` 改为 `dict[str, DayRecord]`；解析收敛 `__init__`（私有 `_parse_record`：兼容已解析 DayRecord dict + 加载时跳过损坏/非法条目，语义=旧 get_record 对非法条目返回 None）
- 新增 `serialize()`：DayRecord→磁盘裸 dict，返回**新 dict**（消灭 logic 与磁盘共享别名）；`get_record` 退化一行 `self.data.get(date_str)`；`save_record` 内部存储 DayRecord 实例
- MainWindow `save_today`/`_delete_record` 改走 `store.save(self.logic.serialize())`；测试内部形态断言 `logic.data[k]["cash"]` 迁移为 `logic.serialize()[k]["cash"]`
- 测试：+4（加载时过滤 / serialize round-trip / serialize 新 dict 别名消灭 / 构造函数兼容 DayRecord dict）；pytest 208/208 ✅（204+4）；CODE_WIKI 方法表/data 规则/测试表同步

### 2026-08-02 | 重构 | D-02 原子写 seam：json_file.py + SettingsStore
- `json_file.py`：`atomic_write_json`（.tmp→os.replace，失败清理并抛 OSError）+ `try_load_json`（容错读，缺失/解析失败返回 None，形状校验交调用方）；**CSV 不进 seam**（导出格式非持久化状态）；DataStore 保留其更丰富的写路径（备份+恢复），未改用 seam
- `settings_store.py` `SettingsStore`：容错读（缺失→{} 静默 / 解析失败→warning+{} / 顶层非 dict→warning+{}）+ 原子写（失败仅 warning 不抛）；MainWindow 只留「编码/解码」——`_save_settings` 委托 `settings_store.save`，删静态 `_load_settings`，`__init__` 注入 `settings_store` 参数（默认 `SettingsStore(SETTINGS_FILE)`，settings_guard monkeypatch 兼容）
- 行为等价性：warning 文案（读取失败/顶层非 dict/写入失败）与 D-02 前逐字一致，测试断言子串不变
- 测试：原 test_ui_smoke 3 个设置容错测试移至 `tests/test_settings_store.py`（15 项新文件），test_ui_smoke 26→23；pytest 204/204 ✅（192-3+15）；CODE_WIKI 新增 4.11/4.12 + 依赖图/导入清单/测试表同步

### 2026-08-02 | 重构 | D-01 趋势判定收敛：format_signed_money 纯函数
- `ProfitCalculatorLogic.format_signed_money(value) -> (str, RateSignal)`：None→`—` / 正→`+¥…` / 负→`¥-…` / 零→`¥0.00`（无 + 前缀）；较前日差值 / 总盈亏展示统一走它
- 表格较前日列改用它：零值 `+¥0.00`→`¥0.00`；颜色经 `app.theme.signal_color`（信号→色映射自 table_widget 收敛至 theme，C1「颜色不在 import 期冻结」语义不变）
- 汇总标签 `_update_summary`：≥2 条分支改走 `format_signed_money` + `signal_color`；「仅 1 条」/「数据不足」灰字分支保持原样（仓库值非趋势，不加 + 前缀）；CSV 较前日列保持无前缀（O-16 语义不变）
- 测试：+5（4 单测 + 1 表格零差值渲染回归）；pytest 192/192 ✅（187+5）；CODE_WIKI 同步方法表/较前日列说明

### 2026-08-02 | 决策 | 架构评审 7 候选 grilling 拍板 + 录入 TO-TICKETS（D-01~D-07）
- 来源：`architecture-review-20260802.html` 深层化机会（O/C 系列热点）；用 grilling 逐分支走决策树，7 分支全部确认
- 定案：D-01 趋势收敛（`format_signed_money` 纯函数，复用 RateSignal，零值 `¥0.00` 无前缀）；D-02 `json_file.py` 原子写 seam + `SettingsStore`；D-03 序列化边界（ADR-0001：`data`→`dict[str, DayRecord]` + `serialize()`）；D-04 QTest 打真实事件链路（`refresh_validity` 降级为同步 seam）；D-05 `is_cash_under_warehouse` 谓词三处收敛；D-06 删 `DayRecord.total`（生产零引用真死代码，`format_input_value` 保留）；D-07 `format_summary` 纯函数（依赖 D-01 信号 seam）
- 新建：`docs/adr/0001-logic-data-dayrecord-map.md`（唯一满足 ADR 三条件的决策）；`CONTEXT.md`（领域词汇表，含序列化/有效性/跨字段校验/格式化等新词）；TO-TICKETS 活跃表 D-01~D-07
- 纯文档/决策，未动代码；pytest 187/187 不受影响

### 2026-08-02 | 运维 | 清理 %TEMP% 影子测试残留 + 陈旧产物提醒约定
- 清理：`C:\Users\Administrator\AppData\Local\Temp\profit_calc_verify_*` **31 个目录（168K）** —— C5 迁移前 `verify_all.py` 的 settings 夹具残留，确认当前代码/测试零引用后 `rm -rf` 清除（`architecture-review-20260802.html` 按用户要求保留）
- 教训：C5 删 `verify_all.py`（831 行）时其 tempfile 夹具目录未同步清理，8 天累积 31 个；**删除影子脚本/一次性工具后须同步清理其运行态残留**
- 约定（用户要求）：此后开发中主动提醒清理陈旧临时产物（`%TEMP%` 残留、`_MEI*` 孤儿目录、旧备份等），清理前仍须用户确认
- 纯运维，pytest 187/187 不受影响

### 2026-08-01 | 文档 | DEV_LOG 精简（滚动摘要 + 单行条目）+ 进度审计修复
- 背景：DEV_LOG 615 行/46.6KB，每次会话读取耗 ~14K tokens；核心内容（决策/避坑/哈希/计数）与 TO-TICKETS 归档表大量重复
- 精简：615→158 行（-61%，~14K→~5.5K tokens）；新增「滚动摘要」顶部块（当前状态 + 4 条持久避坑），正文每工单 1 条仅保留决策/避坑/哈希/计数；4 条「重新打包」烟测条目删除（被 O-20/O-21 覆盖，烟测模式已在 O-20/O-21 保留）；评审录入表压缩（完整行在 TO-TICKETS 归档）
- 审计同步修复：TO-TICKETS O-22 行回填 `c2e34f9`（空启动崩溃修复，`9835387` 之后）；PROJECT_REFERENCE 打包形态「单文件」→「onedir」（O-20 后失同步，CODE_WIKI/README 已同步）
- 纯文档改动，pytest 187/187 不受影响

### 2026-08-01 | 修复 | O-22 空启动日志目录未建崩溃（`c2e34f9`）
- 症状：exe 空环境首启即崩 `FileNotFoundError: ~/收益计算器/profit_calculator.log`
- 根因：`main()` 先构造 `RotatingFileHandler`（打开 LOG_FILE）再执行迁移；目录创建仅在迁移分支内，空启动提前返回时目录未建
- 修复：`main()` 第一行 `DATA_DIR.mkdir(parents=True, exist_ok=True)`，先于日志 handler/迁移/写入
- 回归测试：AST 静态断言 mkdir 行号先于 RotatingFileHandler（防顺序回退复发）
- 结果：pytest 187/187 ✅（186+1）；重建 exe 空启动正常出窗口

### 2026-08-01 | 重构+运维 | O-22 运行态数据统一到用户目录（`9835387`）
- 动机：`dist/` 重建整体覆盖丢数据（O-20/O-21 已踩两次）；exe 移动丢数据；开发版与 exe 两套数据割裂
- 改动：`DATA_DIR = Path.home()/"收益计算器"`，`DATA_FILE`/`BACKUP_FILE`/`SETTINGS_FILE`/`LOG_FILE` 全挂其下；`APP_DIR` 保留为旧数据源；`migrate_legacy_data` 幂等（目标已有 data.json 跳过 / legacy 无数据跳过 / **复制非移动** / 失败仅 warning）；CSV 默认导出路径同改；`main.py` 单实例检查后、建 MainWindow 前迁移
- 测试：`tests/test_migration.py` +6；pytest 186/186 ✅（180+6）
- 取舍：复制非移动——源保留（`.gitignore` 已忽略）可逆，用户确认后手动清理

### 2026-08-01 | 运维+打包 | O-21 UPX 压缩瘦身（`6978182`）+ O-20 待办闭环
- O-20 `_MEI*` 孤儿清理闭环：5 个目录 905MB `rm -rf`（确认无进程占用）
- UPX 5.2.0（winget）装至 `D:\Desktop\tools\UPX\`；spec `upx=True`（EXE + COLLECT 两处）
- ⚠️ PyInstaller 不读 `UPX_DIR` 环境变量（仅 `--upx-dir` CLI / PATH 搜索），构建须显式传参
- 结果：dist 117M→64M（-45%）。未达理论值：Qt6*.dll 与 MSVCP*/VCRUNTIME 为 **CFG（Control Flow Guard）构建，PyInstaller 自动跳过 UPX**（`Disabling UPX ... due to CFG`，防损坏）；实际压缩 8 个 Qt *.pyd（`--lzma`）
- 验证：exe 烟测通过（常驻 ~180MB、二次实例被单实例锁拦截、taskkill 干净）；pytest 180/180 ✅；`upx -t` 确认 QtCore.pyd packed / Qt6Core.dll 未 packed（符合预期）

### 2026-08-01 | 打包 | O-20 onedir 化 + 体积瘦身（`5913a22`）
- 背景：单文件 80MB 每次启动解压 181MB 到 `%TEMP%\_MEI*`（启动慢 ~2-4s 根因），残留 5 个孤儿目录 905MB（O-21 已清）
- 改动：① spec 重写 `EXE(exclude_binaries=True) + COLLECT`（onedir 免解压，交付 `dist/收益计算器/`，exe 6.3MB + `_internal/`）；② 瘦身：excludes 剔 matplotlib/PIL（pyqtgraph 导出器运行时从不加载）、Qt 二进制白名单（仅留 Core/Gui/Widgets/Network/OpenGL/OpenGLWidgets/Svg/Test，8 pyd/8 DLL）、剔 translations/opengl32sw/tls 插件；③ 单实例等待 `waitForConnected(500→100)`（main.py:52）
- 结果：80MB 单文件→117MB 目录（onedir 免压缩，可 zip 分发）；冷启动烟测 1560ms（vs 解压 2~4s+）；二次实例 667ms 被拦截
- `config.APP_DIR`/`_icon_path`（`sys._MEIPASS`）在 onedir 下行为不变，源码零改动；pytest 180/180 ✅

### 2026-08-01 | 文档整理 | TO-TICKETS/README/CODE_WIKI/PROJECT_REFERENCE
- TO-TICKETS 删「工单详情」长文（401→109 行，只留规则+活跃表+归档表）；README 修正图表颜色标注、备份份数 5→4、文件树补全；CODE_WIKI §4.6 theme.py 内联 THEMES（T-02 迁入）、§4.8 删已迁走主题色板；PROJECT_REFERENCE 精简为项目介绍，技术细节统一指向 CODE_WIKI（根治双文档漂移，O-19 同因）
- 纯文档改动，pytest 180/180 不受影响

### 2026-08-01 | 运维 | O-18 settings.json 出索引 + gitignore（`dd47efa`）
- 运行态（几何+主题翻转）入库污染 diff（`082ce62` 曾附带提交一次翻转）；拍板 A：`.gitignore` Runtime data 节追加 + `git rm --cached settings.json`（磁盘保留，本次提交表现为 deleted）；运行态零变化（`_load_settings` 缺失/损坏返回默认 `{}`，O-09 保证）；与 data.json 惯例一致（`95b7eef`）

### 2026-08-01 | 文档同步 | O-19 CODE_WIKI 失同步修正（`9df5ee4`）
- `rotate_weekly` 返回 `list[str]`、`get_weekly_records`→`recent_records`、`summary` 去 `end_date`；依赖锁 `PySide6==6.11.1`/`pyqtgraph==0.14.0`/`pytest==9.1.1`；测试计数以 `--collect-only` 实测为准 165→180（含 O-08/09/11/13/14 用例）；「7 日」表述统一为「最近 7 条」

### 2026-08-01 | 修复+重构 | O-17 清理文案 + 显示基准统一为录入条数（`9df5ee4`）
- 文案：`rotate_weekly` 按记录数轮转，保存提示改「已保留最近 7 条记录，自动清理 N 条较早记录」；logger「删除超期记录」→「删除最旧记录（保留最近 %d 条）」
- **核心决策（用户拍板）**：显示基准从「最近 7 个日历天」改为「最近 7 条实际录入」——`get_weekly_records(today,7)`→`recent_records(days)`（日期升序、无空位占位、跳无效记录）；`summary` 去 `end_date`；标签「7日总盈亏」→「最近7条总盈亏」；间断录入的老记录清理前始终可见
- 轮转 `rotate_weekly` 维持按条数（本就正确）；测试 6 项同步 + 新文案断言；pytest 180/180 ✅

### 2026-08-01 | 决策拍板 | O-16 CSV 大额 K/M 精度（保持现状）
- ≥1e6 金额被 `format_money` 缩写成 K/M，丢失全值精度、Excel 不可求和。三选项：**A** 保持现状仅 docstring 注明取舍 / **B** CSV 专用千分位全值（引号包裹，pandas 默认读成字符串的经典坑）/ **C** 纯数值（Excel/pandas 开箱即算，最优机器格式）
- 拍板 **A**：主消费场景为 Excel 人工查看，与界面显示一致优先于机器可读全值；C 留作「机器可读导出」备选；零行为变更，TO-TICKETS 归档
- 注：当时全量 pytest 红（16 failed+27 errors）系并行重构 `recent_records`/summary/rotate_weekly 未同步，与 O-16 无关

### 2026-08-01 | 评审 | /code-review `082ce62`（O-11~O-15）
- Spec 轴 0 缺失、新测试 4 项全过、无阻断缺陷（影响低-中）；拆 O-16~O-19 录入活跃表；判定不值得做：theme 调色板重写（已合并的个人偏好，回退属返工）、rotate_weekly 返回列表仅用 len()（Speculative，无害）、closeEvent 缺 `QCloseEvent` 注解、O-15 无测试（纯配置，可接受）

### 2026-08-01 | 实现 | O-11~O-15（`082ce62`，180/180 = 176+4）
- **O-11** CSV 金额统一格式化：现金/仓库/较前日走 `format_money`（拍板：字符串与界面一致，代价 Excel 为文本不可求和）；stdlib csv + `lineterminator="\n"`，千分位自动引号包裹；消除 float 伪影
- **O-12** dev 依赖锁定：`PySide6==6.11.1`/`pyqtgraph==0.14.0`；新增 `requirements-dev.txt`（+pytest==9.1.1）
- **O-13** 编辑态关窗确认：`QMessageBox.question`，No→`event.ignore()`；踩坑 `isHidden()` 对未 show 顶层窗口恒 True，改用 `close()` 返回值断言，用例尾 `cancel_edit()` 恢复
- **O-14** 7 日删除可见性：`rotate_weekly` 返回被删日期列表（升序）+ 逐条 logger.info；`save_today` 拼清理提示到已保存指示器；「保留天数可配置」未做（如需另立候选）
- **O-15** 日志轮转：`RotatingFileHandler(1MB×3, utf-8)`，根 logger 幂等；级别保持 INFO（打包版无 stderr）

### 2026-08-01 | 实现 | O-08/O-09（`d0af4d6`，176/176 = 166+10）
- **O-08** 保存前 cash ≤ warehouse 校验：UI 层硬拦截（`QMessageBox.warning`）+ `MoneyLineEdit.set_invariant_warning()` seam + `BORDER_WARNING` 色；业务层 `save_record` 仅 logger.warning 不拦截（允许保留已录入异常数据并继续展示）
- **O-09** 加载顶层 dict 校验：`_try_load` 非 dict（如 `[]`）视为损坏走备份恢复链（此前 AttributeError 崩溃且链不触发）；settings 非 dict 返回默认 `{}` + warning
- ⚠️ **连带修复（测试夹具污染 bug）**：tests 中 `DataStore(tmp_path/data.json)` 未传 backup_file → 默认指向真实 `data.json.bak*`，load 读真实备份、save 写回（静默污染用户备份）。修复：显式传 `backup_file=tmp_path/data.json.bak`（test_input_panel + test_ui_smoke 共 6 处）。此前测试态数据已写入真实备份，待用户确认后从 data.json 恢复

### 2026-08-01 | 评审录入 | O-08~O-15 候选落库
- 架构评估 8 项录入活跃表（O-08 cash≤warehouse P1 / O-09 顶层 dict 校验 P1 / O-10 打包配置入库 P1 / O-11~O-15 P2），详情见 TO-TICKETS 归档；pytest 166/166 基线

### 2026-08-01 | 打包 | O-10 应用图标落地（`20b5170`/`fa16d77`）
- spec `icon='app_icon.ico'` + `datas` 内嵌（单文件版解压后运行时读取）；`main.py` 新增 `_icon_path()`（`sys._MEIPASS`/项目根解析）+ `setWindowIcon()`；ico 16~256px 多尺寸；pytest 166/166 ✅

### 2026-08-01 | 实现 | O-06/O-07（`0f16e1c`，166/166 = 165+1）
- **O-06** 图表稀疏提示：2≤n≤3 叠加半透明「数据较少，需更多数据以显示趋势」overlay（`WA_TransparentForMouseEvents` 不拦鼠标，resizeEvent 跟随）；防新用户误读为图表损坏
- **O-07** 收益率目标参考线：**关闭（YAGNI）**——目标语义未定义（逐日环比 vs 累计），画在哪条序列上无法解释；成本（输入框+settings 持久化+InfiniteLine+测试）>收益

### 2026-08-01 | 实现 | O-01~O-05（165/165 = 147+18）
- **O-01** logging 替换静默 except（`e6d5b64`）：`_load_settings`/`_save_settings`/`_rotate_backups` 三处 `except: pass`→logger.warning；main 加 `logging.basicConfig` 写 APP_DIR/profit_calculator.log（打包版无 stderr）；保留 `_setup_window` 几何/DPI 与 return None 正常语义
- **O-02** `refresh_validity` 公开 seam（`486d41f`）：C4 最后一处跨对象私有访问收敛；AST 守卫防复发
- **O-03** format_money docstring 阈值交叉说明（`ac75c71`）：K 阈值 1,000,000 非 1,000，与 C3 双向引用
- **O-04** CSV 数据导出（`8f50592`）：`export_csv()` 纯函数（日期升序、较前日/收益率复用 format_rate 语义、无前日为—、异常跳过）+ 标题栏「导出 CSV」按钮，utf-8-sig + newline="" 写入
- **O-05** 今日未录入提醒（`749cd59`）：`_today_status_label` 纯读 `get_record(today)` 控制显隐，挂在 refresh_display()
- 并行 worktree（A：O-01~03；B：O-04~05）合并冲突一处（模块级 logger/_logger→logger）；merge `c01c2c2`/`fdeca85`

### 2026-08-01 | 实现 | C5 verify_all 影子测试并入 pytest（`0c6b8e3`，147/147 = 134+13）
- 删除 `verify_all.py`（831 行）；第 1~3 节叶子测试已被覆盖直接删，第 4~11/13~14 节 UI 烟测迁至 `tests/test_ui_smoke.py`（offscreen，13 项）；深度私有访问收敛公开 seam（`fill_values`/`set_edit_mode`/`delete_requested.emit`/`theme_btn.click`）；去抖 QTimer 用 `refresh_validity()` 同步断言；settings/data.json 隔离移交 fixture，删手动 backup/restore

### 2026-08-01 | 修复 | C5 评审后续（时间耦合回归，147/147）
- `make_sample_data()` 固定日期 2026-07-20~27 与墙钟窗口 [today-6,today] 耦合，2026-08-03 起 `test_ui_initialization` 必失败 → 改相对今天（offsets 7/6/5/3/2/0）；编辑/删除测试动态取日期
- `test_settings_persistence` 用 `win.close()`（closeEvent 落盘）替代私有 `_save_settings()`；`qapp`/`settings_guard` 收敛 `tests/conftest.py`；文档勘误（verify_all 14 节、行数 831、README/PROJECT_REFERENCE 147）

### 2026-07-31 | 实现 | C6 浅层残留清扫（`923f544`，134/134）
- 删 app/config.py 空壳、config.py 7 个无消费者 `FONT_*`；`PnL信号`→`PnLSignal`（rename 全仓同步）；formatting 死分支；6 文件死 import 清理；CODE_WIKI 同步

### 2026-07-31 | 实现 | C7~C9（`923f544`，134/134）
- C7 getter docstring 契约修正（空→None / 结构性非法→ValueError）；C8 verify_all 检查标签改名；C9 AST 静态守卫（防 main_window 直取 cash_entry/parse_money_input 复发）

### 2026-07-31 | 实现 | C4 InputPanel seam 成真（`bbe59bf`，133/133 = 124+9）
- getter 语义明确（空→None/非法→抛，原先吞 ValueError 区分不了）；新增 `get_cash_raw`/`get_warehouse_raw`/`refresh_validity`；MainWindow 收敛公开 API、删 `_editing_date` 字段（编辑状态单方归属 InputPanel）；verify_all 适配

### 2026-07-31 | 实现 | C3 收尾 _UNITS 共享表（`e3eff63`，124/124）
- 私有升序表 `_UNITS = (("K", _K), ("M", _M), ("B", _B))`：format_compact 反向迭代、parse_money_input 正向迭代，消除两处内联 (后缀, 因子) 对；纯重构无行为变化

### 2026-07-31 | 实现 | C3 收敛三套 K/M/B 格式化（`e3eff63`，124/124）
- `format_compact(value, *, prefix="")`（SI 阈值 K≥1e3/M≥1e6/B≥1e9，.1f，<1e3 整数）；KMBAxisItem（Y 轴）与 `_ChartPanel._format_value`（hover/端点，prefix="¥"）委托；`format_short_date()` 统一 4 文件 6 处 `date_str[-5:]`
- **两处已批准偏离**：① API 提议 `currency=False`→实现为更通用 `prefix` 字符串；② hover 精度 `.2f`/`.1f` 混用→统一 `.1f`（K/M 降 1 位，B 不变，与 Y 轴一致）

### 2026-07-31 | 修复 | settings.json 测试污染（116/116）
- 症状：跑 verify_all 后 settings.json 被测试态改写（theme/pinned/geometry 残留），需手动 `git restore`
- 根因：每 UI 测试 `win.close()`→closeEvent→`_save_settings()` 写真实 SETTINGS_FILE
- 修复：main() 启动把 SETTINGS_FILE 重定向 tmp_dir，finally 恢复——真实文件全程零读写（强杀也无污染窗口）；附带收益：测试从「读用户真实设置」变确定性默认态；删死 import

### 2026-07-31 | 实现 | C2 DayRecord 生命周期收敛到 logic 层（`240d72b`，116/116）
- logic 新增 `delete_record`/`rotate_weekly`/`summary`，成工作 dict 唯一所有者；MainWindow 视图减负（删 self.data/_rotate_weekly，构造时经 `ProfitCalculatorLogic(self.store.load())` 注入）；`_update_summary` 仅格式化展示；verify_all 适配；测试 +10
- code-review：Spec 8/8 等价（0→数据不足/1→仅1条/≥2→末日−首日）、Standards 合规、无循环 import；3 小项待处理（`_update_summary` 4 行重复块可合并 / PROJECT_REFERENCE:212 残留引用 / TO-TICKETS 清空 T-01~05 待确认）

### 2026-07-31 | 实现 | C1 表格主题色 import 期冻结修复（`8a7b98a`，106/106 = 103+3）
- 根因：模块顶层 `_SIGNAL_TO_COLOR`/`_PNL_TO_COLOR` 在 import 期调 `get_color()`，颜色冻结为 light（T-01 复发同一 bug）→ 改「信号→主题键」静态映射 + draw() 内实时 `get_color()` 解析；左右栏标题内联样式移入 draw()；删死代码链（`apply_theme`）
- ⚠️ **持久避坑：绝不在模块顶层调 `get_color()`**；回归 3 项：dark 下收益率色==FG_POS、light/dark 渲染不同、AST 检查顶层无 get_color 调用

---

## Phase 4 — 架构深入优化 ✅（2026-07-30，T-01~T-05，`ea68a61`；基线 103/103）

- **T-01** 剥离展示层颜色：`RateSignal`/`PnLSignal` 枚举，`format_rate`/`get_pnl_label` 返回 (str, signal)；calculator 不再 import config
- **T-02** 主题系统收敛 `app/theme.py`（内联 THEMES，非重新导出）；config.py 仅留路径/日期/字体
- **T-03** MainWindow 依赖注入（`__init__(store=None, logic=None)`，默认行为不变）
- **T-04** 4 个 UI 模块定义 `__all__`
- **T-05** ChartWidget 拆分 `_ChartPanel`（实例变量 22→4，600→327 行，-45%）
- 来源：Python Architecture Review 2026-07-30（`python-arch-review-20260730T120000.html`），5 候选 T-01~T-05（P0~P4），顶层建议 T-01 先行

## Phase 3 — 架构深度优化 P0-P5 ✅（2026-07-28~29）

- P0 删 Tkinter 迁移残留（5 文件/52KB）；P1 config 穿透合并；P2 删孤立模块级颜色常量（24 导出）；P3 `__all__` 补齐；P4 图表性能（FillBetweenItem 去重建/输入去抖/主题增量更新）；P5 单实例（QLocalServer 防多开）
- 验证：pytest 103 ✅ + verify_all ✅；详情见 CONSENSUS.md

## Phase 2 — PySide6 迁移 ✅（~2026-07-28）

- Tkinter+matplotlib → PySide6（LGPL，Qt 官方绑定）+ pyqtgraph（原生 Qt 渲染）；保留全部功能（双字段输入/金额校验/K-M-B 后缀/JSON 原子写入+滚动备份/7 日滚动/亮暗主题/窗口置顶/PNG 导出）；新增收益率列、盈亏标签列、双栏表格（左 4 右 3）

## Phase 1 — Tkinter 内增强 ✅

- 新增收益率列（1 位小数，红涨绿跌）+ 盈亏标签列（单字盈/亏 + 彩色圆角 Badge）；测试 70→106 PASS

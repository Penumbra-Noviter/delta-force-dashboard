# DEV_LOG — Delta Force Dashboard 开发日志

> **格式**：`YYYY-MM-DD` | `<操作>` | `<描述>`（倒序，最新在前）
>
> 工单标题/完成日期/提交哈希以 `TO-TICKETS.md` 归档表为准；本日志只记「已做」与决策/避坑。

---

## 滚动摘要（2026-08-08）

- **评审修复（08-08，多维度评审 → 子代理按优先级实现）**：P0 `FetchWorker.shutdown()` 关闭逃生舱（请求在途关窗不再 "QThread: Destroyed while thread is still running" abort，atexit 兜底 join）；P1 `app/fetch_page_base.py` 共享基类（crafting/exchange 双页重复提炼，210→122 / 256→178 行，`_error` 死状态删除）+ `preload()` 公开 seam（消除 main_window 四处私有穿透与 lambda 吞错）；P1 硬编码颜色收敛 theme.py（新增 BTN_HOVER_FG/BADGE_FG/NAV_HOVER_BG/OVERLAY_BG/PACKAGE_COLOR_0~2 七键，dark NAV_HOVER_BG 灰 overlay→半透明白，其余逐字保持）；P2 死代码清理（calculator 不可达 return + calendar、config SQLITE_FILE）+ 更名收尾（日志文件名 `profit_calculator.log` → `delta_force_dashboard.log`，推翻「仅改身份标识」中日志名保留项——单实例锁/user-agent 仍保留）；doc_sync 新增 `tests_total` 机械标记（测试数入 pre-commit 保护）；测试数 6 处文档 + memory 统一 305
- **性能优化（08-07 `ded4a5d` + 08-08 `762ef27`）**：crafting/exchange 页同步 HTTP 请求改 `FetchWorker`（QThread）后台执行，UI 不再阻塞（最坏 30s 冻结→0）；`_DaySubTable.draw` 改 get-or-create 复用 widget（30 天视图每次刷新从创建 ~300 个 Qt 对象降为 0）；calculator `_sorted_dates` 缓存（recent_records/summary/export_csv O(n log n)→O(1)）；`refresh_theme()` 解耦主题切换与数据刷新；kkrb_client 60s TTL 缓存；ProfitPage 制造产物预加载
- **测试**：pytest **305/305** ✅

- **项目更名（2026-08-07）**：正式更名为 **Delta Force Dashboard**（原「收益计算器 / Profit Calculator」）——窗口标题、应用名、`DATA_DIR`（`~/收益计算器` → `~/Delta Force Dashboard`，`_LEGACY_DATA_DIR` 一次性迁移旧数据）、spec 改名 `delta_force_dashboard.spec`（exe `Delta Force Dashboard.exe`）、README/PROJECT_REFERENCE/CODE_WIKI/CONSENSUS/CONTEXT/TO-TICKETS/ADR 文档、GitHub 仓库 `profit-calculator` → `delta-force-dashboard`；按「仅改身份标识」决策，`ProfitCalculatorLogic` 类名、日志文件名、单实例锁、user-agent 等内部标识保留

- **X 系列完成**：子弹自选包兑换利润模块 — X-01 兑换利润页面（`app/exchange_page.py`，7 种包类型网格展示，kkrb_client 新增 `AmmoPackageItem`/`fetch_ammo_package_data()`）+ X-02 特殊子弹自选包扩展（4 种新增包：通行证基础/高级、进阶物流、特级物流）+ X-03 代码气味消除（NamedTuple `_PackageConfig`、`exchangeGradeAndCount` 重命名）
- **ProfitPage 重构**：QTabWidget 标签页 → QScrollArea 纵向堆叠，制造产物与兑换利润无需切换直接可见
- **死代码清理**：移除 SQLiteDataStore（`sqlite_store.py` + `test_sqlite_store.py`，有测试无 UI 消费者，与 D-06 纪律对齐）
- **测试**：pytest **293/293** ✅
- **文档**：8 已有提交补 DEV_LOG + TO-TICKETS 归档

- **M-01 修复**：暗色主题 `CHART_GRID` 色值 `rgba(255,255,255,.05)` 无法被 pyqtgraph 解析（`pg.mkColor` 只认十六进制/SVG 名，浮点 alpha 的 `rgba()` 抛 ValueError）→ 暗色主题下首次绘制图表即崩；改 `#RRGGBBAA` 八位十六进制（`#FFFFFF0D`，alpha 13≈5%，视觉一致）+ 回归测试
- **L 系列完成**：Delta Force 游戏工具扩展全部 4 张工单已实现 — L-01 侧边栏导航（`app/sidebar.py` + main_window 重构为 sidebar | QStackedWidget 水平布局）、L-02 kkrb.net API 客户端（`app/kkrb_client.py`，纯 stdlib，CSRF 自动管理）、L-03 制造利润页面（`app/crafting_page.py`，4 台位卡片 2×2）、L-04 卡战备推荐页面（`app/gear_page.py`，输入匹配 + 方案表格）
- **测试**：pytest **297/297** ✅（296 + 1 M-01 回归）
- **打包**：M-01 后主分支重新打包，`dist/Delta Force Dashboard/` **68M**（exe 6.67MB + `_internal/`），烟测通过（dark 主题 + 9 条记录 = M-01 修复前崩溃场景，直接验证修复）
- **文档**：TO-TICKETS M-01/L 系列归档、CODE_WIKI 测试表补 test_kkrb_client.py、doc_sync 通过

- **L 系列立项**：Delta Force 游戏工具扩展（侧边栏导航 + 制造利润 + 卡战备推荐），ADR-0004 落档，4 张工单录入 TO-TICKETS 活跃表
- **架构评审第二轮**：8 候选全实施完毕（#1 展示文本簇→presentation.py / #2 MainWindow 变薄 / #3 原子写合一 / #4 VIEW_DAYS 单源化 / #5 信号→颜色收敛 / #6 汇总四合一 / #7 MoneyLineEdit.set_value / #8 图表几何抽纯函数），详见日志正文
- **测试**：pytest **259/259** ✅（候选 1+6: -27 移 + 23 新 = 249；候选 3: 不变；候选 2: +5 reuse_candidate 测试；候选 4: 不变；候选 5: 不变；候选 7: 不变；候选 8: +5 adaptive_range 测试；249+5+5=259）

---

## 日志正文

### 2026-08-09 | 修复 | U-11 切页崩溃（用户实测：点利润→切回→再点利润闪退，317/317）
- **症状**：快速切页（利润→记账→利润）闪退无提示；日志无崩溃现场（无 crash 捕获）
- **根因定位**：U-06 切页淡入动画（`fade_in_widget` → QGraphicsOpacityEffect + QPropertyAnimation 挂 QStackedWidget 页面）——QGraphicsEffect 挂在 QStackedWidget 页面上，动画进行中页面被 hide/show（快速切页），触发 Qt 已知崩溃路径（effect 与 stack 绘制交互）；Falsify 只测过「同 widget 连续 fade」，未覆盖「stack 切页中 hide/show」场景
- **修复**：① 移除切页淡入动画（`_on_page_changed`/`_PAGE_FADE_MS` 删除；曲线绘制/保存指示动画保留——它们不在 hide/show 路径上）；② `fade_in_widget` 补 dynamic property 悬空指针清理（DeleteWhenStopped 自删动画后 `_fade_anim` 里的 QObject* 悬空，下次读取访问已删对象）——finished 时同步 `setProperty("_fade_anim", None)`；③ **崩溃现场捕获**入 main.py：faulthandler（crash.log，all_threads）+ sys.excepthook（未捕获异常写日志，PyInstaller 无 stderr 默认被吞）+ qInstallMessageHandler（Qt qWarning/qCritical/qFatal 落盘——"QThread destroyed" 等致命消息 abort 前先记录）——下次任何崩溃都有现场
- 回归：`test_page_switch_loop_no_crash`（利润→记账×20 循环）+ U-06 测试改断言（切页动画断言移除、property 清空断言加入）
- pytest 317/317 ✅；重新打包 + 烟测

### 2026-08-09 | 实现 | U-10 利润页启动预加载（316/316）
- 用户反馈：利润页点击后才开始拉数据，有卡顿感。根因：`_preload_profit_page` 只预加载制造产物，兑换利润由首次 showEvent 才拉取（10s 超时 HTTP）
- 改：启动 500ms 定时器同时预加载 crafting + exchange（各自 FetchWorker 后台线程，kkrb 60s TTL 缓存复用）；点击利润页时数据已就绪零闪烁；预加载失败仍走既有兜底（状态标签可点重试）
- 测试坑：`QTest.qWait(1600)` 固定时长与两个后台线程调度存在竞态（同一测试首跑通过次跑失败）→ 改轮询等待 `_loaded_once`（50ms 步进 + 5s 超时），3 连跑稳定
- 测试 +1；pytest 316/316 ✅；重新打包 + offscreen 烟测

### 2026-08-09 | 修复 | U-09 方案 A：折线图空间按屏幕自适应（315/315）
- 用户实测反馈：表格全量展示达成后折线图 140-150px 太小。空间账：920 窗口已被顶部 190 + 表格 490 + 图表 160 + 提示/边距占满，图表变大只能向屏幕高度要
- 方案 A（用户拍板）：`MainWindow._window_preset(screen_h)` 纯函数两档——可用高度 ≥1000（1080p 主流）→ 窗口 1020 + 图表 [160,240]（+90px/+60%）；小屏 → 920/[140,150]；两档表格全量参数（行高 26/stretch 1）完全一致
- 实测：大档 1020 窗口图表实际 240px，30 天视图左 15/15 右 15/15 全量无滚动 ✅
- 测试 +1（`_window_preset` 边界：1000 含/999 不含/0 兜底）；test_u02_type_scale 图表断言改与 `win._chart_min_h/_chart_max_h` 实际档位对齐
- 重新打包（PyInstaller onedir）+ offscreen 烟测

### 2026-08-09 | 修复 | U-09 用户实测反馈（打包前修复，314/314）
- 用户反馈三处：①折线图卡片太大挤占表格，表格要全量展示不要滚动；②「今日未录入」提醒没了；③利润页亮色主题卡片纯白背景纯黑违和
- **①图表布局回退**：U-02 的弹性翻转（chart stretch 1 吃窗口增长）推翻——chart 固定 [140,150] stretch 0，表格恢复 stretch 1（H-01 语义）；30 天视图全量展示关键参数：行高固定 26px（`resizeRowsToContents` 的 sizeHint 与 QSS 交互算出 33px，15 行塞不下 → 改 `setDefaultSectionSize(26)`）+ 视图按钮 28→24px + 卡片边距 (12,10)→(10,8) + 默认窗口 880→920；实测 920 窗口 30 天视图左 15/15 右 15/15 全量可见、无滚动条，7 天 4+3 全量
- **②pill 不可见根因**：WARNING_BG `#fcf4e8` 与 sage 页面底 `#eef0ec` 亮度差仅 0.029（近同色）→ 改 `#F1D9A0`/`#6E4A08`（亮度差 0.084 + 琥珀 vs 灰绿 hue 双区分，10px 文字对比 ≈7:1）；dark `#261e14`→`#3A2E1A`
- **③利润页背景纯黑根因**：U-05 全局 `QWidget { font-family }` 规则使**所有未显式设背景的 QWidget 落入 palette.window 背景**（不随主题）——用户系统深色 palette 时亮色主题下背景即纯黑（本机实测 viewport palette window `#efefef`，autoFillBackground 被 QStyleSheetStyle 接管、代码关闭无效）→ QSS 显式 `QWidget#profitPage, QWidget#profitContainer { background-color: bg }` + profit_page.py viewport 内联透明（QSS 选择器匹配不到 viewport）；双主题实测背景 == 主题 BG
- 附带：QSS 注释内 `{ font-family }` 触发 f-string 插值 NameError（已改写注释避坑）；test_u02_type_scale 图表断言更新为回退语义
- 打包：PyInstaller onedir 重建，dist 67M，offscreen 烟测 12s 无崩溃

### 2026-08-09 | 修复 | U 系列 code-review 评审修复（U-08，314/314）
- 双轴评审（Standards + Spec + Falsify 维度，2 子代理并行）结果：无崩溃级问题；3 处真实规格偏差 + 若干标准项
- **修复**：① 动效全局开关——`motion.set_animations_enabled`（settings 键 `animations`，默认 true），关闭时 fade_in 不挂 effect、属性动画直接落终态（U-06 验收「系统关闭动画时全部动效失效」以设置项实现，注册表检测不做）；② `fade_in_widget` 竞态防护——同 widget 连续触发先 stop 旧动画（QPropertyAnimation.stop 不发 finished，旧清理回调不会误删新 effect）；③ `animate_property` 参数收紧 `QObject`（去 type: ignore）；④ `exchangePage` 包名标签内联 14→15px（QSS 已改 15 但内联优先级更高，U-02 归位失真——DEV_LOG 上一版记录失真已更正）；⑤ `EMOJI['ok']` 收敛 main_window CSV 提示（字面量 ✓ 清零，测试 regex 补 ✓ + Path 绝对化）；⑥ 曲线动画 250→200ms（feedback-only 上限）
- **裁决/取舍**：`app/motion.py`/`ui_text.py` 不注册进 `app/__init__.py`——与 `fetch_worker.py` 同例（内部工具模块不进包表面）；U-01 迷你趋势/窄窗口响应式堆叠不做（验收未列项 + 实测 680px 可用，DEV_LOG 记取舍）
- 测试 +1（动效全局开关）；pytest 314/314 ✅

### 2026-08-09 | 实现 | U-01~U-06 UI 视觉打磨（finesse-ui 审计落地，313/313）
- **U-01 KPI 磁贴**（`b5d230e`）：汇总从裸 QLabel 升级为卡片磁贴——`_split_kpi_text` 拆「说明行（11px caption）+ 数值行（22px 信号色）」；`summary_style` 升级（正常 22px/700、数据不足 16px 灰）；输入卡限宽 520 与 KPI 卡并排（顶部两栏），宽窗口不再全宽拉伸
- **U-02 排版刻度**（`251baec`）：QSS 顶部注释固化刻度（display 18-22 / section 15-16 / body 12-13 / meta 10-11）；按钮两级（QPushButton 默认 11px/500 = secondary，saveBtn/queryBtn 13px/600 = primary；themeBtn 等 10→11、refreshBtn 12→11）；页面标题 `pageTitleLabel` 16px 与应用名 18px 分层；craftProduct 18→16、tierLabel/exchangePackageLabel 14→15；**图表弹性翻转**——chart min 200、max 220 封顶移除、chart_card stretch 0→1、table_card 1→0（H-01「表格独占弹性」决策推翻：趋势图优先趋势阅读），30 天视图超高改 `_DaySubTable` vertical AsNeeded 内部滚动兜底（原 AlwaysOff 会裁剪行）
- **U-04 侧边栏**（`222787d`）：宽度 100→130；选中态「整条实心 BTN_BG」→「浅底 pill（新键 NAV_SELECT_BG，light 森林绿 12% / dark 琥珀 14% 透明）+ 3px accent 指示条」——border-left 选中/未选中同宽（transparent vs accent）保证文字零位移；选中文字改 accent 色
- **U-05 emoji 一致性**（`f0741ff`）：新增 `app/ui_text.py` EMOJI 单一来源（9 键：导航/主题/置顶/加载/警告/保存），sidebar/main_window/fetch_page_base/chart_widget 4 文件散落字面量清零（AST 测试断言无残留）；全局 QWidget font-family 补 "Segoe UI Emoji" 消 Windows 基线错位
- **U-06 反馈型动效**（`d430cd7`）：新增 `app/motion.py`——`fade_in_widget`（QGraphicsOpacityEffect + QPropertyAnimation，结束后移除 effect 防常驻）+ `animate_property`（QVariantAnimation 驱动非 QObject property，如 pyqtgraph 曲线 opacity）；接入三处：切页 120ms 淡入（`_on_page_changed`）、曲线绘制揭示 250ms（opacity 0→1）、保存指示 180ms 淡入
- **U-06 取舍**：hover 背景平滑过渡**未做**——Qt Widgets QSS 无 transition，背景色动画需自定义样式委托（QStyle 子类或事件过滤器逐帧重绘），成本显著高于收益，且 QSS 跳变 + 光标已是可接受的反馈；若用户要平滑 hover 需单独立项
- 测试 305→313（+8：可点重试/中性 badge/U-07 聚合/U-01 拆分/U-02 刻度/U-04 侧边栏/U-05 emoji 来源/U-06 动效），doc_sync 标记同步，每工单独立提交

### 2026-08-09 | 实现 | U-07 交互小修批量（交互反馈闭环）
- **可点「重试」**：`fetch_page_base.py` 新增 `_ClickableLabel`（clicked 信号 + mousePressEvent），错误态设手型光标、点击重新 `_load_data`；文案「点击重试」从骗人变真实（T-02 旧文案回归测试保持通过）
- **按钮焦点态**：`generate_qss` 加 `QPushButton:focus { outline: 2px solid FOCUS_RING }`（Qt 6 QSS outline 不占布局，避免像 QLineEdit 那样 padding 补偿）；Tab 键流可见
- **今日未录入 pill**：`todayStatusLabel` 从裸文字改 WARNING 系底色+边框+圆角 pill（亮 #fcf4e8/#B77A16，暗 #261e14/#E8A33D）
- **轴线对齐**：日期标签取消整页居中改左对齐（与标题同侧），消「标题左/日期中」错位
- **QStatusBar 死样式删除**（8px，从未使用）
- **中性 badge 对比度**：`—` badge 由 FG_MUTED 底+白字（≈4.2:1）改 MUTED_BG 底 + TEXT_SECONDARY 字（light ≈7:1 / dark ≈5.5:1，AA 达标）；涨/亏 badge 配色不变
- 测试 +3（可点重试 / 中性 badge 双主题 / UI 小修聚合断言）；doc_sync 刷新 11 标记；pytest 308/308 ✅

### 2026-08-09 | 审计 | finesse-ui UI 审计 → U 系列工单录入（TO-TICKETS 活跃表）
- 用户反馈 UI「差点意思」，按 finesse-ui skill（product register：craft floor + 密度 + 反廉价清单）全量审计 9 个 UI 模块
- 结论：**底色（craft floor）已达标**——tinted 中性色（无纯 #fff/#000）、hairline 半透明边框、红涨绿跌语义色、焦点环、主题切换无 import 期冻结（C1 教训内化）；问题集中在三层：数字没有家（KPI 层级）、字号没有刻度（排版层级）、颜色没有组织（色彩角色）
- 关键发现：① 汇总（总盈亏/现金总变化）是唯一没住进卡片的元素；② 全 app 字号挤在 8-18px 无刻度，按钮 10/11/12/13px 四档乱跳；③ 图表限高 [140,220] 拿不到窗口增长空间；④ 兑换页 7 包 7 色相 + emoji 混排（游戏感 OK 但无组织）；⑤ 「点击重试」label 不可点（骗人文案）；⑥ 动效为零（hover 直跳色、页面切换无过渡）
- 方向拍板（用户）：**游戏感强一点**——保留多色点缀与 emoji，不收敛配色，只修层级/布局/动效
- 录入 U-01~U-07 至 TO-TICKETS 活跃表（U-01 KPI 磁贴+顶部两栏 / U-02 排版刻度 / U-03 色彩角色系统化 / U-04 侧边栏重做 / U-05 emoji 一致性 / U-06 反馈型动效 / U-07 交互小修批量），暂不实现
- 一次性审计脚本（offscreen 两页两主题截图）已清理，未入版本控制

### 2026-08-08 | 评审修复 | 多维度评审 → 4 子代理按优先级实现（P0/P1/P2）
- P0: `FetchWorker.shutdown(timeout_ms=300)` + 逃生舱——`requestInterruption()` + `wait(超时)`，超时后 `setParent(None)` 脱离 + 模块级 `_detached_workers` 强引用 + `atexit` 兜底 join；`run()` 顶部检查中断标志；`MainWindow.closeEvent` 停 `_preload_timer` + 级联 `ProfitPage.shutdown()`；消除 "QThread: Destroyed while thread is still running" abort 路径（4 项新测试）
- P1: `app/fetch_page_base.py`（179 行）——crafting/exchange 共享基类：`_client/_loading/_loaded_once/_worker/_data/_shut_down` 状态机、showEvent 懒加载、标题栏+状态标签构建、`_load_data/_on_fetch_done/_on_fetch_error` 三件套、`refresh/preload/shutdown`；crafting 210→122、exchange 256→178 行；`_error` 死状态（两页均只写不读）删除并有测试固化
- P1: `preload()` 公开 seam——main_window `_preload_profit_page` 收缩为一行，删除对 `_loaded_once/_loading/_client/_on_fetch_done` 四处私有穿透与 `lambda e: None` 吞错（失败走 `_on_fetch_error` 记 warning + 状态标签「点击重试」）
- P1: 硬编码颜色收敛——theme.py 新增 7 键（BTN_HOVER_FG/BADGE_FG/NAV_HOVER_BG/OVERLAY_BG/PACKAGE_COLOR_0~2，双主题定义）；table_widget PnLBadge/_ActionButtons hover、theme danger 按钮 hover、sidebar 导航 hover、chart 稀疏提示 overlay、exchange 剩余 3 包色收敛；dark NAV_HOVER_BG 由灰 overlay 改半透明白（暗底可见性），其余逐字保持
- P2: 死代码清理——calculator `rotate_weekly` 不可达 `return self._window_delta(...)` + `import calendar`；config `SQLITE_FILE`（92f1a94 移除 SQLiteDataStore 后零引用）
- P2: 更名收尾——`_LOG_FILE` `profit_calculator.log` → `delta_force_dashboard.log`（.gitignore 同步；推翻更名时「日志文件名保留」项，单实例锁/user-agent 仍保留）；main.py 经 `LOG_FILE` 常量引用无需改
- 文档: doc_sync 新增 `tests_total` 机械标记（测试数入 pre-commit 保护）；测试数 6 处文档 + memory 统一；DEV_LOG 补记 `ded4a5d`/`762ef27`；CODE_WIKI 模块树补 3 模块/§4 编号重排/§7 表补齐
- 测试：pytest 305/305 ✅（293 + 12 新：test_fetch_pages.py）

### 2026-08-08 | 性能 | sorted_dates 缓存 + 主题刷新解耦 + kkrb TTL 缓存 + ProfitPage 预加载（`762ef27`）
- P0: calculator.py 维护 `_sorted_dates` 缓存——recent_records/summary/export_csv 从 O(n log n) 降为 O(1)，save_record/delete_record/rotate_weekly 增量更新
- P0: main_window.py 新增 `refresh_theme()` 解耦主题切换与数据刷新——主题切换只刷新视觉样式，不再触发 chart.draw 全量渲染
- P1: kkrb_client.py 新增 60 秒 TTL 内存缓存，避免短时间内重复 HTTP 请求；`reset()` 同步清除缓存
- P1: main_window.py QTimer.singleShot(500ms) 后台预加载 ProfitPage 制造产物数据；crafting_page/exchange_page `_on_fetch_done` 补设 `_loaded_once=True`，消除预加载完成后 showEvent 重复触发
- 测试：pytest 293/293 ✅

### 2026-08-07 | 性能 | 网络请求移至后台线程 + 表格 widget 复用（`ded4a5d`）
- P0: crafting_page/exchange_page 的同步 HTTP 请求改用 `FetchWorker`（QThread，`app/fetch_worker.py`）后台执行，UI 线程不再阻塞（最坏情况从冻结 30s 降为 0）
- P1: `_DaySubTable.draw` 重构为 get-or-create 模式——QTableWidgetItem/PnLBadge/_ActionButtons 首次创建后后续刷新只更新属性，不再重建；30 天视图每次刷新从创建 ~300 个 Qt 对象降为 0
- 测试：pytest 293/293 ✅（纯性能改动，测试数不变）

### 2026-08-06 | 清理 | 移除 SQLiteDataStore 死代码（与 D-06 纪律对齐）
- 删 `sqlite_store.py`（99 行）+ `tests/test_sqlite_store.py`（107 行）
- `data_store.py` 脱 `from sqlite_store import SQLiteDataStore` 导入 + `__all__` 移除条目
- `CODE_WIKI.md` 文件树同步删 `test_sqlite_store.py` 行
- 有测试无 UI 消费者，真死代码，与 D-06 一致
- pytest 293/293 ✅

### 2026-08-06 | 重构 | ProfitPage 标签页改为纵向堆叠（QTabWidget→QScrollArea）
- 制造产物推荐 + 兑换利润在同一滚动页面内纵向堆叠，无需标签页切换
- 各自保留标题栏与刷新按钮，独立刷新；`setSizePolicy(Policy.Fixed)` 按内容高度排列
- `addStretch()` 内容不足时推到顶部，超出时滚动条自动出现
- theme.py 删除 QTabWidget/QTabBar 33 行 QSS 样式（不再需要）
- CODE_WIKI/README profit_page 描述同步更新
- pytest 293/293 ✅

### 2026-08-06 | 多个 | 兑换利润模块（X 系列）— 无工单无日志，补充记录
- 源：08-05 起从 L-03 制造利润页面延伸，独立进入兑换利润方向
- 以下 4 个提交合并为 X 系列统一补录

#### X-01（8c6393e）：子弹自选包兑换利润模块，制造板块更名为利润
- 新增 `AmmoPackageItem` 数据模型（frozen dataclass）和 `fetch_ammo_package_data()` API
- 新增 `ExchangePage`：展示 3/4/5 级子弹中利润最高的兑换方案，QTabWidget 标签页容器
- 新增 `ProfitPage`：QTabWidget 标签页容器（制造产物 + 兑换利润）
- 侧边栏「制造」→「利润」；新增 QTabWidget + 兑换卡片 QSS
- 测试 +7；pytest 299/299 ✅

#### X-02（7977de6）：兑换利润页面增加 4 种特殊子弹自选包
- 取消 kkrb_client 等级过滤，返回所有子弹数据
- exchange_page 重构：7 种包类型各一张卡片（4 列网格布局）
- 新增卡片：通行证基础/高级、进阶物流、特级物流
- 新增样式 exchangeGradeLabel2/exchangePackageLabel；测试 +2（全等级解析 + 特殊包解析）

#### （235cf9a）：文档同步（测试计数、页面列表、项目结构）
- CODE_WIKI.md + README.md 同步

#### X-03（c9bdeb7）：消除两个代码气味
- Primitive Obsession：`_PACKAGE_CONFIG` list[tuple] → NamedTuple `_PackageConfig`
- Mysterious Name：`exchangeGradeLabel2` → `exchangeGradeAndCount`

### 2026-08-06 | 推送 | origin 4 提交落后修复 + 8 提交统一推送
- origin/main 落后 HEAD 4 个提交（X 系列 + 文档同步）
- 工作区 3 个改动（profit_page 重构 + 死代码清理 + DEV_LOG/TO-TICKETS 补录）一并提交
- 共 8 提交推送至 origin（已推 + 4 新增）

### 2026-08-05 | 打包 | 主分支重新打包（M-01 后）+ 烟测通过（dark 崩溃场景直接验证）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）；spec 无变更
- 产物：`dist/Delta Force Dashboard/` **68M**（exe 6.67MB + `_internal/`）；M-01 改动（`app/theme.py`）编译入 PYZ
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（pid 14980，常驻 ~226MB）；用户真实 settings 为 **dark 主题 + 9 条记录**（≥2 触发图表创建路径）——正是 M-01 修复前的崩溃场景，存活 8s 无 Traceback 直接验证修复生效
- 分发前确认：dist 内无运行态数据（data.json/settings.json/log 均缺）
- release 资产未更新（用户未指示；如需更新 `default.zip` 另行执行）

### 2026-08-05 | 修复 | M-01 暗色主题图表网格色 pyqtgraph 解析崩溃
- 症状：暗色主题（Midnight & Amber）下应用启动即崩 `ValueError: Unable to convert rgba(255,255,255,.05) to QColor`（`chart_widget.py` 创建轴时 `pg.mkPen(color=grid_color)`）
- 根因：`app/theme.py` 暗色 `CHART_GRID = "rgba(255,255,255,.05)"` 是 QSS 风格色（浮点 alpha），**pyqtgraph 的 `pg.mkColor` 只认十六进制/SVG 颜色名，不解析 `rgba()`**；其余 `rgba()` 色值只进 QSS 不受影响，唯一流入 pyqtgraph 的就是 CHART_GRID
- 修复：改 `#FFFFFF0D`（RRGGBBAA 八位十六进制，alpha 13≈5%，与原视觉一致）；亮色 `#e2e4df` 本就合法未动
- 回归测试（先写复现）：`tests/test_chart_geometry.py` 新增 `test_chart_colors_parseable_by_pyqtgraph`——双主题 × 5 个图表取色键逐一 `pg.mkColor()`，防再混入 QSS-only 色值
- 测试：pytest 297/297 ✅（296+1）；doc_sync 刷新 CODE_WIKI 机械标记
- TO-TICKETS M-01 → ✅ 归档（2026-08-05）

### 2026-08-04 | 设计 | L 系列立项 — Delta Force 游戏工具扩展
- 来源：Grilling 会话，用户需求「制造利润排行 + 卡战备推荐」
- 范围：两功能整合到现有Delta Force Dashboard App，左侧边栏切换（记账/制造/战备）
- 设计：ADR-0004 落档（QStackedWidget + 侧边栏方案 A），CONTEXT.md 新增 Delta Force 领域词汇
- 工单：L-01~L-04 录入 TO-TICKETS 活跃表，含详细验收标准
- 测试：259/259 ✅（纯设计，未动代码）
- 注：kkrb.net 已确认有公开 REST API（`getOVData`/`getCPVData`），无需浏览器渲染

### 2026-08-05 | 实现 | L 系列全部完成 — Delta Force 游戏工具扩展
- **L-01（侧边栏导航）**：`app/sidebar.py` 新文件（QWidget + QListWidget 导航 + 底部主题/置顶/导出按钮）；`main_window.py` 重构为水平布局（sidebar | QStackedWidget），Dashboard 为 Page 0，标题栏/日期标签只在记账页显示；侧边栏主题色 `apply_theme()` 方法（运行时 get_color 避免 C1 复发）；按钮引用改为 `self.sidebar.*`
- **L-02（kkrb.net API 客户端）**：`app/kkrb_client.py` 纯 stdlib（urllib.request），数据模型 `CraftingProduct`/`GearScheme`/`GearItem`（frozen dataclass），CSRF 首页提取 + 缓存复用，`KkrbError` 自定义异常，测试 14 项
- **L-03（制造利润页面）**：`app/crafting_page.py`，4 台位卡片 2×2 网格，加载中/失败重试状态，刷新按钮，按利润排序
- **L-04（卡战备推荐页面）**：`app/gear_page.py`，输入框支持 K/M/B 后缀解析，`_find_closest_tier` 匹配最近档位，方案卡片含 QTableWidget 装备清单
- **测试**：295/295 ✅（+14 kkrb_client 测试）；UI 烟测 28 项全绿（含 sidebar 按钮引用迁移）
- **文档**：TO-TICKETS L 系列归档、CODE_WIKI 测试表补 test_kkrb_client.py、DEV_LOG 同步、doc_sync --check 通过

### 2026-08-04 | 实现 | R-02 DataStore 泛型化 `DataStore[T]`
- `DataStore` 改为 `DataStore(Generic[T])`，`T = TypeVar('T', bound=dict)`
- `load()` 返回 `T`，`save(data: T)` 接受 `T`
- 内部方法 `_try_load`/`_atomic_write` 保留具体类型签名不变
- 向后兼容：所有现有代码使用 `DataStore()` 无类型参数，类型检查器推断为 `DataStore[dict]`，运行时行为一致
- 测试：264/264 ✅（全部通过，无回归）
- 文档：TO-TICKETS R-02 移入已完成归档

### 2026-08-04 | 实现 | 第二轮架构评审 8 候选全实施（Grilling → subagent fan-out → 合并）
- 来源：`D:\Desktop\To-do\architecture-review-20260804-1110.html`（架构评审报告第二轮，8 候选）
- 流程：Grilling 三问（Q1-Q3）→ 用户拍板 → parallel subagent worktree 实施 → 合并 → code-review → 文档同步
- 候选 1+6（`3964d83`）：展示文本簇拆出 `presentation.py`（根层，5 公开函数）+ `format_window_text` 参数化替代 format_summary/format_cash_summary（#6 四合一）。`calculator.py` 协议面 17→11 方法，`summary`/`cash_summary` 改为 `_window_delta` 薄包装。
- 候选 3（`3964d83`）：`DataStore._atomic_write` 委托 `json_file.atomic_write_json`，原子写 seam 唯一实现，测试面收敛。
- 候选 4（`d1e39cf`）：`VIEW_DAYS` 移入 `config.py`，`WEEK_DAYS` 保留语义独立性，注释说明数值巧合。
- 候选 5（`7ea4a26`）：`_PNL_TO_KEY` 合并进 `_SIGNAL_TO_KEY`，`signal_color(RateSignal | PnLSignal)` 单入口，`table_widget.py` 删 18 行自建映射。
- 候选 2（`3368a2c`）：`reuse_candidate` 纯方法下沉 calculator（返回三元组含 is_today_fallback），`summary_style` 封装进 theme，`view_n` 只读 property，`set_reuse_hint` 合并三步委托。`_update_summary` 样式去重，`_reuse_last_record` 缩小。
- 候选 7（`4275479`）：`MoneyLineEdit.set_value(text)` 公开方法，`_formatting` 重入保护内聚，`InputPanel` 调用方改走公开协议。
- 候选 8（`4f76876`）：`_adaptive_range` → `adaptive_range` 公开纯函数，`ChartState`/`ChartSeries` frozen dataclass，`state` property 只读快照，烟测改走 `chart.state` 公开 API，新增 `test_chart_geometry.py`（5 测试）。
- 测试：259/259 ✅（249+5+5，doc_sync 通过）
- 文档：TO-TICKETS 归档 8 候选 + DEV_LOG 同步；code-review 通过（Standards 0 硬违反，Spec 2 项需注意）

### 2026-08-04 | 打包 | K 系列重新打包（3efc77c）+ 烟测通过
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）；spec 无变更
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.56MB + `_internal/`）；K 系列改动（`calculator.py`/`app/main_window.py`）编译入 PYZ
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（pid 17536，常驻 ~200MB；`.migrated` 10:20:04 重写证明启动路径完整、日志无异常）
- release 资产未更新（用户未指示；如需更新 `default.zip` 另行执行）

### 2026-08-04 | 实现 | K-01 保存保留两位小数 + K-02 现金总变化展示
- 需求：用户「修改数据保存逻辑：保留两位小数」+「最近7条/30条总盈亏旁边加一条最近现金7条/30条总变化」（并行 fan-out 3 子代理，前两个分别完成、第三个评审——两实现子代理因基础设施 API 错误（`reasoning_content` 回传校验）在落盘代码后中断，由主会话接手补测试/评审/文档闭环）
- **K-01（数据精度）**：`ProfitCalculatorLogic.save_record` 存储前 `round(cash, 2)`/`round(warehouse, 2)`（Python 银行家舍入，docstring 注明；不变式告警改用舍入后值，保证告警与落盘一致）；磁盘 `serialize()` 输出随之为 2 位小数
- **K-02（UI 双标签）**：`cash_summary(days)`（镜像 `summary` 的现金版：最新−最旧现金，同窗口语义）+ `format_cash_summary(count, delta, days)`（镜像 `format_summary`，前缀「最近N条现金总变化：」）；`MainWindow` 汇总条改 QHBoxLayout 并排双标签（`_summary_label` 总盈亏 + `_cash_summary_label` 现金总变化），`_update_summary` 双写文本+信号→颜色，随视图 7/30 联动
- 测试：`test_calculator.py` +15（rounding 回归 3：两位小数/银行家舍入/浮点表示；cash_summary 6：空/单条/正/负/零/超窗截断；format_cash_summary 6：空/单条/正/负/零/days 参数化）、`test_ui_smoke.py` +1（双标签随 7/30 联动）；全量 253/253 ✅
- 文档：CODE_WIKI 方法表补 `cash_summary`/`format_cash_summary` 行 + `save_record` 说明注舍入；README/CODE_WIKI/PROJECT_REFERENCE 测试数 237→253；TO-TICKETS K 系列归档；doc_sync --check 通过（机械标记 6 处刷新）
- 注：K-02 复用 D-07 纯函数模式（文本+信号由 logic 生成、样式留 UI），与既有 `summary`/`format_summary` 完全镜像，无新增跨层依赖

### 2026-08-03 | 打包 | 洁癖收尾：布局修复版重新打包 + release 更新（烟测通过）
- **打包**：主分支重新打包（J-01/J-02 后），`dist/Delta Force Dashboard/` 64M；**未烟测**（用户指示本次不启动 exe 验证，详见日志正文）
- **打包**：洁癖收尾补布局修复版（`e261685`）重新打包 + GitHub release 资产替换为 `default.zip`（烟测通过，详见日志正文）
- **测试**：pytest **237/237** ✅（2026-08-03 J 系列视图切换 UI 用例 +3、summary/format_summary 参数化纯函数 +2）
- **图表**：样式对齐原型评审修正版（0559537）——删填充区域、hover 改「系列短名+值、按所属 ViewBox 顶部堆叠定位」；布局把曲线图置底固定高度、表格改弹性区，为后续 7/30 天记录预留高度（用户预告将记录天数设为 7/30 天）
- **布局**：图表卡片 `setMaximumHeight(220)` 封顶（PlotWidget sizeHint 480 吃掉纵向空间），880 窗口下表格 107→367px（详见日志正文）
- **活跃工单**：见 TO-TICKETS 归档表（G-01 图表样式对齐已归档为 H-01）

---

## 日志正文

### 2026-08-03 | 打包 | 洁癖收尾：布局修复版重新打包 + release 更新（烟测通过）
- 背景：`e261685`（图表卡片封顶 220px，880 窗口表格 107→367px）在 `92acd44` 打包**之后**提交，`dist/` 与 GitHub release 均落后一个提交；洁癖收尾核对发布面时发现并补齐
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）；spec 无变更
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.56MB + `_internal/`）；唯一 warn 仍为 `pyqtgraph.opengl` 可选子模块未收集（历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（pid 14812；`.migrated` 15:38 重写证明启动路径完整、日志无异常）；pytest 237/237 ✅
- release：更新 GitHub release（tag `default`）资产——旧 `default.rar`（37.9M，H-01/G-01 版，落后布局修复）删除，上传 `default.zip`（布局修复版，64M→zip）。**压缩格式 rar→zip**：本机无 rar/WinRAR，README 已提前改「压缩包」通用措辞，zip 为 Windows 原生可解压
- 清场（用户确认）：删 throwaway 分支 `prototype/chart-merge`（`0559537`）/`prototype/multiview`（`f39c66f`）；清 `build/`（21M）/`__pycache__`/`.pytest_cache`；`.claude/settings.local.json` 删一次性调试授权残留（.shots / download_finesse_cdn.py / /tmp 脚手架等），保留 pytest / doc_sync / pre-commit / install-hooks 可复用条目

### 2026-08-03 | 调整 | 图表卡片封顶高度，给表格让出纵向空间
- 问题：图表卡片无上限，PlotWidget 默认 sizeHint **480px** 生效 → 图表卡片 502px，880 窗口下表格只剩 ~107px
- 修复：`main_window.py` 图表控件 `setMaximumHeight(220)`（配合既有 `setMinimumHeight(140)`，区间 [140,220]，卡片含边距约 242px）；`test_ui_initialization` 最小高断言随窗口收紧同步 700→650
- 验证：offscreen 实测 880 窗口表格 107→**367px**（1000 窗口 →487px）；pytest **237/237** ✅；`doc_sync --check` 通过

### 2026-08-03 | 打包 | 主分支重新打包（J-01/J-02 视图切换后，含 J 系列改动）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.56MB + `_internal/`）；J 系列改动（`calculator.py`/`config.py`/`app/table_widget.py`/`app/main_window.py`）编译入 PYZ，spec 无需变更（无新资源/依赖）
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 分发前确认：dist 内无运行态数据（data.json/settings.json/log 均缺），`app_icon.ico` 内嵌
- **未烟测**：用户指示本次不启动 exe 验证；源码态 pytest 237/237 ✅ + 打包 exit 0（如需冒烟，启动 `dist/Delta Force Dashboard/Delta Force Dashboard.exe` 观察进程存活与日志）

### 2026-08-03 | 实现 | J-01 保留上限 7→30 + J-02 视图 7/30 切换（ADR-0003，存储/视图解耦）
- 需求：用户「记录天数上限 7→30 + 多视图切换」（Grilling Q1–Q11 收敛，`CONSENSUS.md` §7）。核心=把**保留 Retention**与**视图 View**解耦
- **J-01（数据模型）**：`config.py` 新增 `RETENTION_LIMIT=30`（保留上限），`rotate_weekly()`/`format_saved_indicator()` 默认改引用它——`rotate_weekly` 保留边界「满 30 不删、第 31 条才删最旧」（Q11）；清理文案「已保留最近 30 条记录」
- **J-02（UI）**：`TableWidget` 加 7/30 按钮组（`QButtonGroup` + `QRadioButton`）+ `view_changed(int)` 信号 + 持有 `_view_days`（Q6/Q8 深模块——表格是视图窗口主人，MainWindow 只订阅）；分栏均分 `mid=ceil(n/2)`（Q7：7→4+3、30→15+15）；`MainWindow` 持 `_view_n`（启动默认 7，会话内存不持久化 §7.5）、`_get_records`/`_update_summary` 去硬编码 `WEEK_DAYS` 改走 `_view_n`；切视图 `_on_view_changed → refresh_display`，表格+曲线图+汇总同源联动（Q9/Q10）
- 测试：`test_ui_smoke.py` +3（默认视图 7+按钮组状态 / 切 30 信号+15+15+汇总「最近30条」 / 切回 7 不丢存储 Q5）、`test_calculator.py` +2（`format_summary(days=30)` 前缀 / `summary(7)` vs `summary(30)` 窗口参数化）；rotate_weekly 既有用例改 30 上限
- 文档：ADR-0003 落档（可选方案 A 纯扩容/B 解耦/C 日历口径 → 选 B）；CODE_WIKI/PROJECT_REFERENCE/README 同步「最近 30 条 + 视图 7/30」文案；doc_sync 刷新机械标记
- 验证：pytest 237/237 ✅；`doc_sync --check` 通过

### 2026-08-03 | 打包 | 主分支重新打包（H-01 图表样式 + G-01 双轴合并后，含图表改动）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.5MB + `_internal/`）；H-01/G-01 图表改动（`chart_widget.py`/`main_window.py`）编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
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
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（未显式 `--upx-dir`，UPX 已在 PATH）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.5MB + `_internal/`）；F-02 `.migrated` 标记 + `log_legacy_cleanup_hint` 编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
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
- 来源：`D:\Desktop\knowledge base\demo\experience\Delta Force Dashboard项目经验复盘.md` 五、复盘反思（5 条可提升方向）
- 评估：① **文档同步自动化 ✅ 值得做**——实测 `CODE_WIKI` §7 测试表各文件用例和 214 ≠ 实际 pytest 221，且漏 `test_migration.py`，手工同步又漂移（正是 3.6 教训现场）→ 录 **F-01**；④ **数据迁移源清理时间点 ✅ 值得做**——O-22 复制非移动的源清理时间点模糊（E-04 本机残留已清），转为前瞻性策略 → 录 **F-02**
- 不建工单：② 提交前 code-review——交互式 skill 无法进 git 钩子，习惯已由流程覆盖，可行自动化（AST 守卫 + doc-sync）并入 F-01；③ 并行开发命名/接口先约——流程约定，O 系列合并教训已留痕，无需代码；⑤ 规模悖论——原则性边界，作为后续工单验收标准（覆盖真实路径 + 防复发，不堆测试数量）
- 现状核对：根目录 `data.json.bak*` 4 份（E-04 暂缓项）已清空，无残留；`~/Delta Force Dashboard/` 数据自足健康
- 2026-08-02 拍板：F-01 / F-02 均采纳（待开发）；本次 TO-TICKETS / DEV_LOG 变更**未提交**（用户指示，工作区保留）

### 2026-08-02 | 运维 | 项目评估报告核对 + E 系列工单收口
- 背景：外部 AI 评估报告（`项目评估报告.md`，8.80/10）与 HEAD 逐条核对——3 条 P1 中 2 条已存在（纯函数 docstring / ADR 文档），1 条论据过期（其引用的 `DATA_RETENTION_DAYS` 常量 O-17 已删）；报告文件已不在工作区（用户自行处理，git 零引用）
- 拍板（用户）：E-01 保留天数可配置 **关闭**（不知配置对用户实际作用）；E-02 操作审计日志 **关闭**（单用户无追责场景 + 覆盖写日志留不下旧值，救不了撤销）；E-03 图表脚本化导出 **关闭**（不需要，YAGNI）；E-04 陈旧产物清理 **授权**（已录入 TO-TICKETS 活跃表 🔄）
- E-04 执行：删 5 个 stale pyc（`app/__pycache__/` 下 logic/data_store/formatting/config + 根 `verify_all`——C5/D 系列重构残留，gitignore 已忽略无害）+ 根目录旧 `profit_calculator.log`（O-22 前 APP_DIR 日志，现日志在 `~/Delta Force Dashboard/`）
- ⚠️ **根目录 `data.json.bak*` 4 份暂缓**：核对发现值差异——bak 含 07-24 唯一记录、07-25/08-01 数值与权威 `~/Delta Force Dashboard/data.json` 不同（疑 O-08 测试污染或旧快照）；权威数据自足健康（含当日 08-02 记录 + 完整备份链），07-24 系 08-02 保存时正常轮转删除。用户确认后删除（E-04 归档）
- pytest 221/221 不受影响（纯运维 + 文档）

### 2026-08-02 | 打包 | 主分支重新打包（D-08 后，含 signals.py）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（未显式 `--upx-dir`）
- ⚠️ UPX 现已在 PATH：WinGet 安装的 `upx 5.2.0`（`C:/Users/.../WinGet/Packages/UPX.UPX.../upx.exe`），spec `upx=True` 自动命中，无需再显式传 `--upx-dir`（滚动摘要第 12 行旧避坑已过时，保留为无 PATH 环境的兜底）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.5MB + `_internal/`，与 O-21 UPX 后持平）；`signals.py` 编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
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
- 症状：exe 空环境首启即崩 `FileNotFoundError: ~/Delta Force Dashboard/profit_calculator.log`
- 根因：`main()` 先构造 `RotatingFileHandler`（打开 LOG_FILE）再执行迁移；目录创建仅在迁移分支内，空启动提前返回时目录未建
- 修复：`main()` 第一行 `DATA_DIR.mkdir(parents=True, exist_ok=True)`，先于日志 handler/迁移/写入
- 回归测试：AST 静态断言 mkdir 行号先于 RotatingFileHandler（防顺序回退复发）
- 结果：pytest 187/187 ✅（186+1）；重建 exe 空启动正常出窗口

### 2026-08-01 | 重构+运维 | O-22 运行态数据统一到用户目录（`9835387`）
- 动机：`dist/` 重建整体覆盖丢数据（O-20/O-21 已踩两次）；exe 移动丢数据；开发版与 exe 两套数据割裂
- 改动：`DATA_DIR = Path.home()/"Delta Force Dashboard"`，`DATA_FILE`/`BACKUP_FILE`/`SETTINGS_FILE`/`LOG_FILE` 全挂其下；`APP_DIR` 保留为旧数据源；`migrate_legacy_data` 幂等（目标已有 data.json 跳过 / legacy 无数据跳过 / **复制非移动** / 失败仅 warning）；CSV 默认导出路径同改；`main.py` 单实例检查后、建 MainWindow 前迁移
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
- 改动：① spec 重写 `EXE(exclude_binaries=True) + COLLECT`（onedir 免解压，交付 `dist/Delta Force Dashboard/`，exe 6.3MB + `_internal/`）；② 瘦身：excludes 剔 matplotlib/PIL（pyqtgraph 导出器运行时从不加载）、Qt 二进制白名单（仅留 Core/Gui/Widgets/Network/OpenGL/OpenGLWidgets/Svg/Test，8 pyd/8 DLL）、剔 translations/opengl32sw/tls 插件；③ 单实例等待 `waitForConnected(500→100)`（main.py:52）
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

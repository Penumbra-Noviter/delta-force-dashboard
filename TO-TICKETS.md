# To-Tickets — Delta Force Dashboard

> **来源**：2026-08-04 架构迁移（domain/skeleton/adapter 三包分离）+ 后续增强候选
> **规则**：本文件是**仓库内唯一的待办事实来源**。活跃表只保留「未完成」工单；每完成一项 → 移入「已完成归档」并记日期 → 同步 `DEV_LOG.md` → 与本提交一起 commit。
>
> **维护节奏**（绑定到已有流程节点，不新增习惯）：
> 1. 开始实现某工单前，把状态从 📝 已录入 → 🔄 进行中（认领）
> 2. 每会话结束、commit 之前：完成 → ✅/❌ → 移入归档；新评审候选（含未拍板的 `Worth exploring` / `Speculative`）一律先录入 [TECH_DEBT.md](TECH_DEBT.md) 候选池（不自动进入 preflight 认领，带 编号/来源/强度/状态）
> 3. 待办**不得写在 memory / 个人笔记里**——不落 TO-TICKETS 就不算数
>
> **归档清出机制（2026-08-27 推行，规则与论证见 [docs/ticket-archive-cleanup-research.md](docs/ticket-archive-cleanup-research.md) / conver system 先例）**：
> 1. 已完成归档完整保留**最近 6 个批次**；更早批次折叠为「历史归档索引」单行（工单号/提交哈希/摘要保留，细节由 git 历史承担：`git log -p -- TO-TICKETS.md`）
> 2. 索引行超 **60 行**时，最旧的行整行删除
> 3. **叙述职责归位**：新批次归档只承载工单事实表（编号/标题/类型/日期/提交）；背景/spec 详情/验收链等叙述**只写 DEV_LOG.md**，归档批次末尾一句引用「详见 DEV_LOG〈节标题〉」；已完成工单的 spec 档案不再回填「工单详情」区（2026-08-27 起整区退役为存档索引）
> 4. 活跃表禁止 ✅ 滞留：会话结束 commit 前检查活跃表无完成态为显式一步

---

## 活跃工单

> 活跃表（2026-08-13）：无进行中工单（IC-债1/2 已归档，见下方）。

| Ticket | 标题 | 依赖 | 状态 |
|--------|------|------|------|

---

## 技术债区

> 已迁移至独立文件 [TECH_DEBT.md](TECH_DEBT.md)（AGENTS.md §3 规范，2026-08-24 迁移；
> 迁移时净清零）。历史技术债消费批次（IC-债 / BD-债 / C4-债 系列）见下方「已完成归档」。

---

## 工单详情存档索引

> 2026-08-27 压缩：原「工单详情」区（已完成工单的 spec 档案）整区退役，原文由 git 历史承担
> （`git log -p -- TO-TICKETS.md`）；对应归档节见「已完成归档」。

| 系列 | 日期 | 内容 | 对应归档节 |
|------|------|------|-----------|
| IC-债1/2 | 2026-08-13 | 技术债消费：Magic Number + Data Clumps（sidebar 导航），基线 06f31df | IC-债1/2 技术债消费批次 |
| IC 系列（ADR-0006） | 2026-08-13 | SVG 图标替换 emoji：icons.py + sidebar/main_window/fetch_page_base/chart_widget 落点 + ui_text 退役 | IC 系列 |
| BD-债1~3 | 2026-08-13 | 技术债消费：kkrb 错误码/未知键 warning/None 字段防御 | BD-债1~3 技术债消费批次 |
| BD 系列 | 2026-08-13 | 桌面端密码门模块（DESIGN_MOBILE.md v5 §5.2）：数据层/页面/装配/文档 4 工单 | BD 系列 |
| Z 系列 | 2026-08-10 | 兑换页 SEPARATOR 分隔线主题联动（U-03 遗留） | Z 系列 |
| U 系列 | 2026-08-09 | UI 视觉打磨（finesse-ui 审计）：KPI 磁贴/排版刻度/色彩角色 3 方向 | U 系列 |

---

## 已完成归档

> 完整批次（最近 6 批）见下方；更早批次已折叠为「历史归档索引」表（2026-08-27 首次压缩执行，原文由 git 历史承担）。

### 架构评审批次（2026-09-08，improve-codebase-architecture，基线 a53c102）

> 来源：全库架构审查（`improve-codebase-architecture` skill，7 项候选）+ 用户拍板「按强度顺序逐个推进」。候选池见 [TECH_DEBT.md](TECH_DEBT.md)；叙述见 DEV_LOG〈滚动摘要 2026-09-08〉；本表只承载工单事实。

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C1 | 动画句柄生命周期回归 `app/motion.py`：在途注册表（target 弱键）+ `is_running`/`stop`/`finish` + 四工厂 bool 化 + `shake` 关键帧内化；四落点迁移（`_shake`/KPI 槽/chart 句柄/fade）；六条 u06 契约换观测点 + `tests/test_motion.py` 11 例 | ✅ 2026-09-08 | `1508728` |
| C2 | 删 `main_window._kpi_signal` 1 行中继与 kpi_presenter 调用期延迟导入：判定归位 presenter 私有 `_window_signal`（AA-01 单一来源不漂移），跨模块 import 与循环依赖消失；守卫测试改扫描目标；顺带修正 CODE_WIKI §4.19 的 C1 后残留叙述 | ✅ 2026-09-08 | `266faaf` |
| C3 | FetchPageBase 删只写不读的 `_data` 僵尸成员；空/错态占位文案单源为类常量 `_EMPTY_TEXT`/`_ERROR_TEXT`（三页引用）；ExchangePage 补 `_render_error` 覆盖（错误态此前与空态同形）；+2 测试（基类默认钩子最小子类验证、`_data` 缺席守卫） | ✅ 2026-09-08 | `327c07b` |
| C4 | KPI count-up 判据改纯语义（删 `value != "数据不足"` 展示文案判据——`new is None` 已覆盖）；加载中文案单源为 `_LOADING_TEXT`（状态标签 ⟳ 前缀 + exchange 卡片初始占位）；+2 测试（源码守卫「本模块无展示文案字面量」、加载中文案单源） | ✅ 2026-09-08 | `c8514b0` |
| C5 | 仪表盘页族同构：`DashboardPage(QWidget)` 取代 `build_dashboard(mw)`（构造参数即接口、标签公开、删工厂转发）；7 组信号接线归 `MainWindow._connect_signals`；`_build_card` 内迁 `_card_frame()`；MainWindow 私读与副作用写回全消 | ✅ 2026-09-08 | 本提交 |

期末验证：**642/642 全绿**（55.4s）、doc_sync 双绿（先 update 7 标记再 check）；diff 逐批次 8/6/8/5/7 文件；测试净减 3（C5 删 4 条面向旧接口的 Falsify、加 1 条 MainWindow 接线断言）。行为变化仅 C3 一处（兑换页错误态文案）；另记测试基建发现 DFD-7（`test_fetch_pages.py` 单独运行 heap corruption，与生产代码无关）。

### 简化批次（2026-08-29，simplify-codebase skill，Survey→Change，基线 cb3ceae）

> 来源：simplify-codebase 审计（生产/测试两域只读 Explore）+ 用户拍板 A+C。叙述见 DEV_LOG〈滚动摘要 2026-08-29〉；本表只承载工单事实。

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| S-01 | 删 16 个死主题 token ×light/dark（BORDER_LIGHT/CHART_TEXT/ERROR_*/INFO_*/PANEL_2/PIN_OFF_BG/PIN_ON_BG/SUCCESS_*/SURFACE_0/1/2/TEXT_DISABLED/TEXT_LINK）——逐键 grep 全仓（含 QSS 消费）零引用，删字典定义 + 空注释组 | ✅ 2026-08-29 | 本提交 |
| S-02 | 删 `theme.get_theme()`（全仓含测试零调用）+ `__all__` + `app/__init__.py` 导出 + CODE_WIKI 3 处引用 | ✅ 2026-08-29 | 本提交 |
| S-03 | 删 `MainWindow.view_n` property（测试全用 `_view_n`） | ✅ 2026-08-29 | 本提交 |
| S-04 | 删 3 个死 import：main_window 的 signal_color/format_short_date、table_widget 的 QRadioButton（视图切换实际是 QPushButton） | ✅ 2026-08-29 | 本提交 |
| S-05 | 删死 fixture `store`（test_account_store，文件内 25+ 测试零消费） | ✅ 2026-08-29 | 本提交 |
| S-06 | `cleanup_encryption` autouse fixture 两文件逐行副本 → conftest 单源 | ✅ 2026-08-29 | 本提交 |
| S-07 | `theme_guard` fixture 两文件 4 行副本 → conftest 单源 | ✅ 2026-08-29 | 本提交 |
| S-08 | `tmp_dir` 自造 fixture（tempfile 重复 pytest 内建 tmp_path）→ 60 处机械替换 + 删 tempfile import | ✅ 2026-08-29 | 本提交 |
| S-09 | `wait_loaded` 8 行轮询双内联 → 模块级 helper（qapp 显式参数化） | ✅ 2026-08-29 | 本提交 |
| S-10 | doc_sync sig 标记「完整签名 vs 裸名」双谓词分裂 → `_is_full_sig` 单一谓词（`_sig_content_ok`/`_sig_update_text` 共用） | ✅ 2026-08-29 | 本提交 |
| S-11 | `make_store` 工厂收敛 19 处 `DataStore(tmp_path...)` 双参构造（含 test_data_store 本地同款 + 文件名双形态 data.json/d.json 统一） | ✅ 2026-08-29 | 本提交 |

期末验证：**631/631 全绿**、doc_sync 双绿（先 update 3 标记再 check）；diff 15 文件 ±163/−244 净 −81 行；行为零变化（死键零 QSS 消费、删除符号全仓零残留、测试数不变）。B 类（summary_by_period/import_csv 删可达能力）用户未拍板，保留；C7 完整 make_window 工厂因构造参数异构降级为 make_store；chart.state 观测面/`_kpi_signal` 中继/两套迁移双实现保留（净收益为负或红线）。

### IC-债1/2 技术债消费批次（2026-08-13，kickoff 全自动档，基线 06f31df，分支 kickoff/ic-debt）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| IC-债2 | Magic Number：提取 `_NAV_ICON_SIZE = 16` 模块级私有常量（仿 `_RENDER_DPR` 先例），apply_theme 三处显式（render ×2 + pixmap ×1）与 icons.py 默认 size 解耦；行为零变化；Falsify：常量改 8 → Selected pixmap 尺寸 16→8 接线成立 | ✅ 2026-08-13 | `d6b5cd4` |
| IC-债1 | Data Clumps：`NAV_ITEMS` 就地捆元组（`ClassVar[list[tuple[str, str]]]`，新增导航项缺图标键 → 解包 ValueError 快速失败；键非法 → render_icon KeyError）、删除 `_NAV_ICONS`、构造与 apply_theme 元组解包 + `zip(strict=True)`（期末评审建议）；测试 367/2434/2435 断言同步（367 全量元组相等自带配对守卫），TDD 红→绿 | ✅ 2026-08-13 | `c37f5f5` + 审核小修（本提交） |

期末四轴：**0 阻断**（Standards 3 非阻断：注释 KeyError/ValueError 口径已修；Spec 4 非阻断：两处工单验收文字口径已裁决修正；Falsify 6 非阻断：zip strict 建议已采纳；Architecture 4 非阻断）；全量 630/630、doc_sync 双绿、冒烟 SMOKE OK；技术债区净清零

### IC 系列（2026-08-13，SVG 图标替换 emoji，来源：用户拍板方案 C，ADR-0006，主会话直改）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| IC-01 | `app/icons.py` 图标模块——`ICONS` 表 9 键（ledger/wrench/key/plus/pin/moon/sun/refresh/save）内嵌 24×24 SVG 模板 + `render_icon(name, color, size=16)`（QSvgRenderer → 2x pixmap + DPR HiDPI；未知键 KeyError；模块内零 get_color C1 铁律）；`tests/test_icons.py` 6 用例（键集守卫/渲染有效/颜色注入/尺寸/未知键/占位符无残留） | ✅ 2026-08-13 | 本提交 |
| IC-02 | sidebar + main_window 落点——`NAV_ITEMS` 纯文本 + QIcon 双模式（Normal=FG_LABEL/Selected=accent，apply_theme 重建）；new_account_btn/pin_btn setIcon（pin 按 active 态 BTN_FG/FG_LABEL，置顶切换即时换色）；theme_btn moon/sun 图标；account_title 去 emoji 纯文本；`theme.py` font-family 移除 Segoe UI Emoji | ✅ 2026-08-13 | 本提交 |
| IC-03 | fetch_page_base + chart_widget 落点——refresh_btn setIcon + FetchPageBase 新增 apply_theme（C1-08 自动纳入；**三子类 Crafting/Exchange/BonusDoor 的 apply_theme 补 super() 契约**）；状态文本去 FE0F 变体（⚠️→⚠、🔄→⟳，BMP 文本符号）；chart 导出 action setIcon + apply_theme 重建 | ✅ 2026-08-13 | 本提交 |
| IC-04 | ui_text.py 退役（4 处 import 清）+ U-05 守卫迁移——`test_u05_emoji_single_source` → `test_ic_emoji_free_and_icon_single_source`（彩色 emoji/FE0F 范围正则扫 app/ + 图标装配断言 + 文案纯文本断言；✓⚠⟳ BMP 文本符号不在范围）；新增 `test_icons_follow_theme_toggle`（主题切换图标像素跟随 FG_LABEL，Falsify）；全部文本断言同步（状态 4 处/theme 按钮/NAV_ITEMS/pin_btn/BD-03） | ✅ 2026-08-13 | 本提交 |
| IC-05 | 文档收尾——CODE_WIKI §3 文件树（ui_text→icons）+ test_icons 行 + §4.23 icons.py 节 + 4.22 apply_theme 描述更新；README 同步（icons.py/测试数 630）；doc_sync 双绿；DEV_LOG 批次记录；本表归档 | ✅ 2026-08-13 | 本提交 |

### BD-债1~3 技术债消费批次（2026-08-13，kickoff 轻量档，基线 84ea3a8，分支 kickoff/bd-debt）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| BD-债1 | kkrb 业务错误码检查——`parse_bonus_door_response` code 存在且 != 1 → `KkrbError`（消息带响应 msg，无 msg 不悬挂空冒号）；code 缺失/为 1 正常解析（容错，既有无 code 畸形矩阵用例保持通过）；docstring 分层一致（顶层非 dict 在前） | ✅ 2026-08-13 | 本提交 |
| BD-债2 | 未知地图键 warning——解析前对比 data 键集与 `BONUS_DOOR_NAMES`，映射外键 `logger.warning`（列出键名，str 映射后排序稳定）；遍历逻辑不变（未知键仍跳过）；模块新增 `logger = logging.getLogger(__name__)`；Falsify：非 str 键（仅手造可达）不崩 | ✅ 2026-08-13 | 本提交 |
| BD-债3 | None 字段防御——`_build_card` `item.name/password or ""`（QLabel 构造入参契约 str，纯防御；实测 PySide6 6.11.1 `QLabel(None)` 不崩退化为空文本——契约守卫，C4-债6 先例）；测试 614→621（+7），kkrb_parsing 100% / bonus_door_page 100% | ✅ 2026-08-13 | 本提交 |

### BD 系列（2026-08-13，桌面端密码门模块，来源：DESIGN_MOBILE.md v5 §5.2，基线 4a235ca，分支 kickoff/bd-bonus-door）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| BD-01 | kkrb 数据层：`BonusDoorItem`（frozen，全 str）+ `BONUS_DOOR_NAMES` 映射单源（7 键，定义序=输出序）+ `parse_bonus_door_response` 纯函数（畸形矩阵 V-01 惯例）+ `fetch_bonus_door_data()`（`_EXCLUDED_BONUS_DOOR_KEYS = {az3r6}` 单点剔除，复用会话/锁/60s 缓存）；FakeOpener 传输/缓存/错误降级 V-05 惯例；kkrb 三文件覆盖 100%，72/72 | ✅ 2026-08-13 | `ec35780` |
| BD-02 | 密码门页面 `app/bonus_door_page.py`：`BonusDoorPage(FetchPageBase)` 动态卡片网格（`_render_data` 清空重建）、地图名 + 密码大字 34px bold 内联（颜色全 QSS 选择器 `#bonusDoorCard/#bonusDoorMap/#bonusDoorPassword`，双主题）、空态「暂无数据」/ 错误态「加载失败，点击重试」`_show_placeholder` 共用（C2-05）、`apply_theme` 空钩子、**不展示更新时间**（v5）；`make_stub_client` 增 `bonus_impl` 参数（既有调用零改动）；页面 100% / theme 98%，13/13 | ✅ 2026-08-13 | `6e3059c` |
| BD-03 | 装配：侧边栏第三导航「🔑 密码门」（`EMOJI['nav_bonus_door']` 单一来源）+ `QStackedWidget` 第三页（共享同一 client，C2-02 惯例）+ `_preload_profit_page` 改名 `_preload_data_pages` 扇出密码门 preload + closeEvent shutdown；`app/__init__` 导出；main_window 90% / sidebar 99% / ui_text 100% | ✅ 2026-08-13 | `c9b30cc` |
| BD-04 | 文档收尾：CODE_WIKI §4 补 kkrb_models/kkrb_parsing/bonus_door_page 三节（lines+sig 标记）+ kkrb_client 方法表（fetch_bonus_door_data 等）+ §3 文件树 + doc_sync 双绿（614 项 tests_total 一致）；DEV_LOG 批次记录；本表归档 | ✅ 2026-08-13 | 本提交 |

### 技术债批次 C4-债9/11/12（2026-08-13，kickoff 轻量档全自动，基线 f70347d）+ C4-债10 复核关闭

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C4-债9 | fade_in_widget duration 护栏——`max(1, duration_ms)`（duration=0 时 start 即 Stopped、finished 不触发 → property 残留悬空 wrapper，Falsify 实测比预测更硬：调返回值方法 access violation 致 pytest 进程 abort）；反证测试真红真绿（state() 触碰悬空 wrapper）+ 契约断言（非 None + property 收敛 + effect None）；评审微修 docstring 补钳制语义 | ✅ 2026-08-13 | `23817ff`（merge `6d0b1a7`）+ `92a06ce` |
| C4-债10 | identity 守卫惯用法提取候选——复核关闭（grep：显式 identity 比较恰 3 处 chart_widget:299/input_panel:116/kpi_presenter:263 + fade property 清理集中 motion，「第 5 实例」触发条件未成立） | ❌ 复核关闭 2026-08-13 | — |
| C4-债11 | 删 `_saved_indicator_anim` 只写句柄——改直接调用 fade_in_widget 不接返回值（属性零读取、无 __init__ 初始化；防 GC 由 C++ parent + C4-债6 `_fade_anim` property 承担）；补契约测试 test_saved_indicator_fade_contract（填补既有 fade 覆盖全在 motion 层、无 InputPanel 公开 API 链路的真实缺口） | ✅ 2026-08-13 | `23817ff`（merge `6d0b1a7`） |
| C4-债12 | test_w02_shake_identity_guard 时序加固——identity 断言前补 `anim2.state() == Running` 辅助断言（时序漂移先红在辅助断言而非误判 identity；确定性论证：动画时钟只随事件处理推进，130ms 处理 < 150ms 总时长） | ✅ 2026-08-13 | `23817ff`（merge `6d0b1a7`） |

### 技术债批次 C4-债6/7/8（2026-08-13，kickoff 轻量档全自动，基线 5103092）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C4-债6 | fade_in_widget 生命周期收敛——stop 后同步清 `_fade_anim` property（DWS 不发 finished 的残留窗口结构性消除）+ finished 闭包 weakref 破环（强闭包环 → 在途销毁与 DWS 延迟删除互踩，C4-债3/5 同款定案）；诚实声明无行为级反证（防御性/一致性加固），契约测试保持；motion 覆盖 100% | ✅ 2026-08-13 | `510330a`（merge `b9d01ce`） |
| C4-债7 | `_shake` finished 加 identity 检查（默认参数 `a=anim` + `edit._shake_anim is a`，对齐 chart_widget on_finished 定案）；**实证**：PySide6 6.11.1 同 target 同 property 启动新动画自动停旧动画（anim2.start() 瞬间 anim1→Stopped + DWS 自删 + finished 零触发）——并发路径从根上不可构造，identity 属防御/一致性（Qt 层结构保证比防抖更强）；测试转契约守卫，docstring 如实注明 | ✅ 2026-08-13 | `858bc15`（merge `b9d01ce`） |
| C4-债8 | `test_u06_clear_all_stops_running_draw_anim` 环境态自持——`prev = animations_enabled()` + try/finally 恢复（比既有 hardcode-True 恢复惯例更强）；反证真红真绿（关闭态原测试 AttributeError → 修复后关闭/正常双绿） | ✅ 2026-08-13 | `858bc15`（merge `b9d01ce`） |

### 历史归档索引（2026-08-27 首次压缩：2026-07-30 ~ 2026-08-13 批次）

> 折叠规则见头部「归档清出机制」。原文细节由 git 历史承担（`git log -p -- TO-TICKETS.md`）；叙述详情见 DEV_LOG 同名节。

| 日期 | 批次 | 提交范围 | 摘要 |
|------|------|---------|------|
| 2026-08-13 | 技术债批次 C4-债5（轻量档） | `b04e07e` + `6bcac30` | 图表动画生命周期加固（stop+deleteLater+weakref 破环）+ 第 4 实例复核关闭 |
| 2026-08-12 | 技术债批次 C4-债1~4（轻量档） | `e26f1a6`→`044d926` | KPI/图表动画竞态与生命周期四连修（per-label 分槽→per-tile 槽→weakref 收敛→chart 闭环） |
| 2026-08-12 | C7（全自动档） | `c5eecfe` | 存储 seam 容错收敛（_try_load 委托 + InvalidToken 容错） |
| 2026-08-12 | C6（全自动档） | `c9b7f3e` | 删除 Registry 插件系统 + AST 守卫 |
| 2026-08-12 | C5（全自动档） | `d718a3e` | calculator 展示边界（format_rate 单源 + 删孤儿报告，579→412 行） |
| 2026-08-12 | C4 系列（全自动档） | `f53a1ea`/`0ed4f76` | widget 装配抽离（DashboardBundle）+ KPI 渲染收敛（KpiPresenter 三出口） |
| 2026-08-11 | 架构加深 C1/C2/C3 | merge `633f549` + `c78acc4` | 11 工单：KkrbClient 并发锁/注入 seam/offscreen 退役/主题契约树遍历/get_color 守卫 |
| 2026-08-11 | AA 系列（评审非阻断） | merge `25082df` | 4 项：KPI signal 纯函数/卡重置抽取/锁边界/公开命名 |
| 2026-08-10 | Z 系列（主题联动收尾） | 本提交 | 兑换页 SEPARATOR 分隔线主题联动（构建期冻结 → 运行期刷新） |
| 2026-08-10 | Y 系列（多账号记账） | merge `900f50a` + `39d9595` | 5+1 工单：AccountStore/旧数据迁移/启动解析/侧栏账号区/切换 + 评审修复，ADR-0005 |
| 2026-08-09 | W 系列（微交互打磨） | `03989ea` | 4 项：KPI count-up/非法输入 shake/按钮 pressed 反馈/图表 hover 高亮 |
| 2026-08-09 | V 系列（架构深化） | `4c0f590`→`59275d9` | 5 工单：kkrb 解析拆出/load_state 状态机/SettingsCodec 纯函数/主题双轨收敛/传输层补测 |
| 2026-08-09 | U 系列（UI 视觉打磨） | `b5d230e`→`99efd87` | 11 工单：KPI 磁贴/排版刻度/色彩角色系统化/emoji 一致性/动效/崩溃修复/屏幕自适应 |
| 2026-08-05 | M 系列（修复） | — | 暗色图表网格 rgba 无法解析崩溃修复（#RRGGBBAA 八位十六进制） |
| 2026-08-05 | L 系列（游戏工具扩展，ADR-0004） | — | 侧栏导航系统 + kkrb.net 客户端 + 制造利润页 + 卡战备页（已移除） |
| 2026-08-06 | X 系列（兑换利润模块） | `8c6393e`→`c9bdeb7` | ExchangePage + AmmoPackageItem + ProfitPage 标签页 + 4 特殊包 + NamedTuple/重命名 |
| 2026-08-04 | R 系列（框架增强 ★ 级） | — | BaseRecord/DataStore[T]/插件式 Widget/CSV 导入/多级聚合/主题 token 50+ |
| 2026-08-02 | F 系列 | `fc28fff` | doc_sync 自动化 + pre-commit 防漂移 + 数据迁移完成标记 |
| 2026-08-03 | J 系列（保留 30 + 多视图） | `569b97f` | RETENTION_LIMIT=30 + 7/30 视图切换（ADR-0003） |
| 2026-08-04 | K 系列（两位小数） | `3efc77c` | save_record 舍入两位 + 现金总变化并排标签 |
| 2026-08-04 | 第二轮架构评审（8 候选） | `3964d83`→`4f76876` | presentation.py 纯函数/汇总四合一/原子写/编排器变薄/VIEW_DAYS 单源等 |
| 2026-08-03 | H 系列（图表样式对齐） | `d2b0076` | 图表样式修正 + 曲线图置底弹性高度 |
| 2026-08-02 | G 系列（图表合并） | `abc7119` | 双曲线合并同一坐标系（双 Y 轴，ADR-0002） |
| 2026-08-02 | D 系列 | `cea6bb7`→`478b23e` | 8 项：趋势收敛/原子写 seam/序列化边界/QTest 真实路径/不变式/浅表面 |
| 2026-07-31 | C 系列 | `8a7b98a`→`0c6b8e3` | 9 项：表格主题冻结/生命周期收敛/格式化去重/InputPanel seam/verify_all |
| 2026-07-30 | T 系列（Phase 4） | `ea68a61` | 展示层颜色剥离/主题收敛/依赖注入/`__all__`/ChartWidget 拆分 |
| 2026-08-01 | O 系列实现（第一批） | `e6d5b64`→`0f16e1c` | O-01~06：logging 替换静默/refresh seam/docstring/CSV 导出/未录入提醒/稀疏提示 |
| 2026-08-01 | O 系列（第二批 P1） | `d0af4d6`→`20b5170` | O-08~10：cash⊆warehouse 校验/顶层 schema 校验/打包配置入版本 |
| 2026-08-01 | O 系列（第三批 P2） | `082ce62` | O-11~15：CSV 金额统一/dev 依赖锁定/编辑态关闭确认/7 日可见性/日志轮转 |
| 2026-08-01 | O 系列（O-17/19/18 批次） | `9df5ee4`/`dd47efa` | 清理文案与轮转语义/CODE_WIKI 失同步/settings 运行态入库清理 |
| 2026-08-01 | O-20 打包瘦身 | `5913a22` | 打包 onedir 化 + 体积瘦身 |
| 2026-08-01 | O-21 UPX 压缩 | `6978182` | dist 117M→64M + `_MEI*` 残留清理闭环 |
| 2026-08-01 | O-22 数据目录统一 | `9835387`/`c2e34f9` | 运行态数据统一用户目录 + 一次性迁移 |
| 2026-08-01 | O 系列（评审关闭） | — | O-C1~C4/O-07 五条：YAGNI/产品决策/架构撤回，各附关闭理由 |
| 2026-08-01 | O 系列（决策拍板） | — | O-16 CSV 大额 K/M 缩写：选 A 保持现状，docstring 注明取舍 |
| 2026-08-02 | E 系列（运维清理） | — | 陈旧产物清理（stale pyc + 旧数据源残留） |
| 2026-08-02 | E 系列（评审关闭） | — | E-01/02/03 三条：7 条可配置化/审计日志/PNG 导出，均关闭附理由 |

---

## 工单状态说明

- **📝 已录入**：已记录但尚未进入开发计划（含未拍板的候选）
- **🔄 进行中**：正在开发中
- **✅ 已完成**：已合并验证通过
- **❌ 已关闭**：经评估决定不实施

> 归档压缩试点见 [docs/ticket-archive-cleanup-research.md](../../conver%20system/docs/ticket-archive-cleanup-research.md)（conver system 先例，2026-08-27）。
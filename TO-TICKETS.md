# To-Tickets — Delta Force Dashboard

> **来源**：2026-08-04 架构迁移（domain/skeleton/adapter 三包分离）+ 后续增强候选
> **规则**：本文件是**仓库内唯一的待办事实来源**。活跃表只保留「未完成」工单；每完成一项 → 移入「已完成归档」并记日期 → 同步 `DEV_LOG.md` → 与本提交一起 commit。
>
> **维护节奏**（绑定到已有流程节点，不新增习惯）：
> 1. 开始实现某工单前，把状态从 📝 已录入 → 🔄 进行中（认领）
> 2. 每会话结束、commit 之前：完成 → ✅/❌ → 移入归档；新评审候选（含未拍板的 `Worth exploring` / `Speculative`）一律先录入活跃表
> 3. 待办**不得写在 memory / 个人笔记里**——不落 TO-TICKETS 就不算数

---

## 活跃工单

> 活跃表（2026-08-12）：当前为空——C4→C5→C6→C7 批次已全部归档；非阻断技术债见下文「技术债」小节。
| Ticket | 标题 | 类型 | 状态 | 强度 |
|--------|------|------|------|------|

---

## 工单详情

### Z 系列（2026-08-10，主题联动收尾，来源：U-03 遗留）

#### Z-01：兑换页 SEPARATOR 分隔线主题联动

**目标**：U-03 评审遗留——兑换页卡片分隔线为构建期内联样式，主题切换后不刷新（light `#d6d3cc` / dark `rgba(255,255,255,.06)` 双主题值不同，亮→暗切换后暗面残留浅色线，直到窗口重建）。

**具体改动**：
1. `app/exchange_page.py` — `_build_package_card` 分隔线引用存入 `card._sep`；`apply_theme()` 在现有包标签刷新循环内补齐 SEPARATOR 色刷新（运行期 `get_color`，增量更新不重建，模式同 chart_widget.apply_theme）
2. `tests/test_theme_roles.py` — 新增用例：双主题循环 set_theme + apply_theme 后断言全部卡片 `_sep` 样式含当前主题 SEPARATOR 值
3. `tests/test_ui_smoke.py` — `test_theme_toggle_updates_exchange_labels` 扩展分隔线断言（集成链路：theme_btn.click → refresh_theme → apply_theme）

**影响范围**：`app/exchange_page.py`、`tests/test_theme_roles.py`、`tests/test_ui_smoke.py`

**验收标准**：
- [ ] 双主题下 apply_theme 后分隔线样式含当前主题 SEPARATOR 色值
- [ ] UI 集成链路（主题按钮点击）下分隔线随主题更新
- [ ] pytest 全绿

---

### U 系列 — UI 视觉打磨（2026-08-09，来源：finesse-ui 审计）

方向共识（用户拍板）：**游戏感强一点**——保留多色点缀与 emoji 风格，不收敛配色；修的是「数字没有家（KPI 层级）、字号没有刻度（排版层级）、颜色没有组织（色彩角色）」三个问题。

#### U-01：KPI 磁贴 + 顶部两栏布局

**目标**：仪表盘最核心的两个数字（总盈亏 / 现金总变化）从裸 QLabel 升级为卡片磁贴，输入区不再全宽拉伸。

**具体改动**：
1. `app/main_window.py` — `_default_registry` 中 summary_widget 改卡片容器（复用 `_build_card` 阴影卡片），磁贴内大数字（20-22px）+ 信号色 + 迷你趋势（可先用文本 delta，不做 sparkline）
2. 顶部区域改两栏：左侧输入卡片限宽（~420-480px），右侧 KPI 磁贴（2 个并排），窗口 ≥ 900px 时生效、窄窗口回退纵向堆叠
3. `app/input_panel.py` — 输入框 `stretch 1` 改限宽，避免宽窗口下无限横向拉伸

**影响范围**：`app/main_window.py`、`app/input_panel.py`、`app/theme.py`（磁贴 QSS）

**验收标准**：
- [ ] 两个 KPI 磁贴有卡片底 + 阴影，数字明显大于正文（对比现状裸 QLabel）
- [ ] 宽窗口（≥1000px）下输入区不再全宽拉伸，与 KPI 并排
- [ ] 主题切换磁贴颜色联动；pytest 全绿

---

#### U-02：排版刻度

**目标**：建立三级字号体系，按钮收敛两级，应用名与页面标题分层，图表获得更多垂直空间。

**具体改动**：
1. `app/theme.py` — `generate_qss` 统一字号 token：display（KPI 数字 20-22）/ section（页面标题 15-16）/ body（正文 12-13）/ meta（10-11）；现状 8px（QStatusBar）/10px 混杂全部归位
2. 按钮两级：primary（保存/查询，13px 600）/ secondary（复用/刷新/导出/主题/置顶，11px 500）；删除 10/12px 游离档
3. 页面标题与应用名分层：`titleLabel`（应用名 18px 保持）与 `FetchPageBase._title`（页面标题改 15-16px）不再同字号
4. `app/main_window.py` — 图表 `setMinimumHeight(140)/setMaximumHeight(220)` 改 min 200 + 弹性分配翻转：表格 stretch 1 但给 max（或图表 stretch 随窗口增长），趋势图优先获得窗口增长空间

**影响范围**：`app/theme.py`、`app/fetch_page_base.py`、`app/main_window.py`、`app/sidebar.py`

**验收标准**：
- [ ] 全 app 字号只有 3 级 + meta 1 级，按钮只有 2 级
- [ ] 应用名 > 页面标题 > 卡片正文 层级肉眼可辨
- [ ] 窗口拉高时图表高度增长、表格不再独占弹性空间
- [ ] pytest 全绿（含最小窗口尺寸断言，若布局收紧需同步调整）

---

#### U-03：色彩角色系统化（保留多色）

**目标**：多色保留（游戏感），但让多色"有组织"——统一明度/饱和度带、语义色与装饰色分离、色板定义去重。

**具体改动**：
1. `app/theme.py` — 检查 7 个包色 + 4 个图表序列色：统一到同一明度/饱和度带（当前 `#7B8CFF`/`#A58BFF` 等明度差异大，混排显脏）；装饰色（包/序列）与语义色（涨跌 FG_POS/FG_NEG）显式分离并注释规则
2. `app/exchange_page.py` — `_PACKAGE_CONFIG` 7 色键收敛为单一角色命名（当前 CHART_SERIES_0~3 + PACKAGE_COLOR_0~2 两套键：**CHART_SERIES 实际只服务兑换页包色、chart_widget 不引用它——键名撒谎**；PACKAGE_COLOR 亮暗同值语义重复）；顺带修正 exchange_page.py:34 注释「hex 回退色」与实现不符（`get_color` 缺失键返回 `""`，`or color` 回退的是键名字符串=无效色，不存在 hex 回退路径）
3. 不做：不收敛为单 accent、不删 emoji、不改红涨绿跌

**影响范围**：`app/theme.py`、`app/exchange_page.py`、`tests/test_fetch_pages.py`（键元组断言随映射同步）；`app/chart_widget.py` 已核实不引用 CHART_SERIES_*，无需改

**评审修复（2026-08-09，code-review）**：包标签色构建期冻结 → `ExchangePage.apply_theme()` 运行期重解析，挂入 `main_window.refresh_theme` 链路（亮暗色板分离后残留即失效）；另修 test_theme_roles 主题状态泄漏、补 6 位 hex 格式断言。

**验收标准**（全部可机器证伪，目检仅辅助）：
- [x] 键名如实：7 包色收敛为单一角色命名一套键（如 PACKAGE_COLOR_0~6），删除 CHART_SERIES_*/PACKAGE_COLOR_* 双套键；亮暗同值键**不抽常亮色**（保留双主题定义防 Locality 坑），随主题变化/固定键清单显式化并注释规则
- [x] 键引用完整：exchange_page 引用的全部色键在 THEMES 双主题下存在且非空（测试断言，防 `get_color` 静默返回 `""` 漏改不报错）
- [x] 装饰 ≠ 语义：双主题下装饰键值 ≠ FG_POS/FG_NEG 值 + HSL 亮度差 ≥ 阈值（**当前 dark 下 CHART_SERIES_2/3 与 FG_POS/FG_NEG 完全同值，必须修**——5 级包标签=亏色、3 级包标签=涨色）
- [x] 明度带量化：7 装饰色 HSL 亮度落统一区间、饱和度 ≥ 下限（colorsys 计算断言）
- [x] 两两可分辨：同主题内 7 装饰色两两色差 ≥ 阈值（防明度统一后 `#7B8CFF`/`#A58BFF` 色相过近更难分）
- [x] 不破坏可读性底线：badge/标签文字对比度维持 U-07 的 AA 4.5:1（浅底深字），明度统一后抽查
- [x] 目检降级为辅助：修复前/后截图对比仅作辅助证据，不作为独立验收（U-09 前科：目检已实锤不可靠，QSS 字体族背景问题目检未发现）

---

#### U-04：侧边栏重做

**目标**：100px 纯文字栏 + 全色块选中态 → 图标+文字导航 + 轻量选中态。

**具体改动**：
1. `app/sidebar.py` — 导航项图标+文字（保留 emoji 风格，见 U-05 统一规则）；宽度 100→120-140px
2. 选中态：全色块（`item:selected` 整条 BTN_BG 实心）改浅底 pill + 左侧 3px accent 指示条；hover 态保留
3. 底部三按钮（主题/置顶/导出）统一为 icon+text 两档样式（与 U-02 按钮分级对齐）

**影响范围**：`app/sidebar.py`、`app/theme.py`、`app/main_window.py`（`_update_theme_btn_text`/`_update_pin_btn_style` 文案联动）

**验收标准**：
- [ ] 选中态视觉轻一个量级（浅底+指示条，非实心色块）
- [ ] 底部按钮与全局按钮分级一致
- [ ] 主题切换联动不变；现有 sidebar 相关测试全绿

---

#### U-05：emoji/图标一致性

**目标**：不删 emoji（游戏感），但消除"基线错位 + 字体混排"的廉价感。

**具体改动**：
1. 全 app emoji 盘点（📒🔧🌙☀️📌🔄💾✓⚠️ 等）：收敛为固定集合，每个含义一个字符，不混用变体
2. Qt 下显式统一 emoji 渲染：QSS/字体设置指定含 emoji 的字体族（Windows 为 Segoe UI Emoji）或改用等宽符号字符，消除与中文文字基线的错位
3. 状态提示（加载/错误/成功）emoji 前缀统一（🔄 加载/⚠️ 失败/✓ 成功），与 U-07 可点重试联动

**影响范围**：`app/sidebar.py`、`app/fetch_page_base.py`、`app/chart_widget.py`、`app/main_window.py`、`app/theme.py`

**验收标准**：
- [ ] emoji 集合有单一来源（常量或注释清单），无散落变体
- [ ] 截图目检：emoji 与文字同一基线、字号一致
- [ ] 功能无回归（按钮文案测试如 `_update_theme_btn_text` 断言同步）

---

#### U-06：反馈型动效

**目标**：product register 的"反馈型动效"底线——hover 过渡、页面切换淡入、曲线绘制动画、保存反馈。

**具体改动**：
1. hover/pressed 过渡：QSS 无 transition 支持，用 `QPropertyAnimation`（背景色/透明度 150ms）或可接受的等效方案，覆盖按钮两级（U-02 后）
2. 页面切换：QStackedWidget 切换 120ms 淡入（`QGraphicsOpacityEffect` + 动画，或 `QStackedWidget` 动画替代方案），尊重系统动画关闭（Windows 设置检测或设置项）
3. 图表：曲线绘制动画（pyqtgraph `setData` 前先 clip/逐点 reveal，或 `pg` 内置动画方案），仅限仓库序列
4. 保存成功：savedIndicator 出现微动效（淡入）+ 可选 KPI 数字滚动（不强制）

**影响范围**：`app/main_window.py`、`app/chart_widget.py`、`app/input_panel.py`、新增动效工具模块（如需）

**验收标准**：
- [ ] 动效均为反馈型（触发后 ≤200ms 完成），无装饰性循环动画
- [ ] 系统关闭动画时全部动效失效但功能完整
- [ ] offscreen 测试不因动画挂起（动画用 QTest.qWait 或直接 set 终态）；pytest 全绿

---

#### U-07：交互小修批量

**目标**：6 条低风险小问题一次清完。

**具体改动**：
1. `app/fetch_page_base.py:141` — 「⚠️ 数据获取失败，点击重试」label 加点击事件（或改文案为「点击刷新按钮重试」），消除"骗人文案"
2. `app/theme.py` — QPushButton 补 `:focus` 样式（2px FOCUS_RING），键盘 Tab 流可见
3. `app/main_window.py:95` — 「今日未录入」从 10px 小字升级为状态 pill（底色 + 边框）
4. `app/main_window.py:103-107` — 日期标签与标题对齐（同侧对齐或取消整页居中）
5. `app/theme.py:619-623` — QStatusBar 死样式删除（从未使用）
6. `app/table_widget.py:81-94` — 中性「—」badge 对比度提升（FG_MUTED 底 + 白字 4.2:1 → 换更浅底或深字，达 AA 4.5:1）

**影响范围**：`app/fetch_page_base.py`、`app/theme.py`、`app/main_window.py`、`app/table_widget.py`

**验收标准**：
- [ ] 错误态 label 可点击重试（或文案不再误导）
- [ ] Tab 焦点在按钮上可见；badge 对比度 ≥ 4.5:1
- [ ] pytest 全绿（状态 pill 若改 objectName 需同步测试）

---

#### L-01：侧边栏导航系统

**目标**：将现有单页应用改为左侧导航栏 + QStackedWidget 多页面架构。

**具体改动**：
1. `app/sidebar.py` — 新增 `Sidebar` 导航组件（QWidget）：
   - 2 个导航项（记账 / 制造），纯文本，点击高亮
   - 底部区域放现有按钮（主题切换、置顶、导出 CSV）
   - 固定宽度 ~100px，深色背景，与当前主题联动
2. `app/main_window.py` — 重写 `_build_ui`：
   - 中央控件改为水平布局：`sidebar | QStackedWidget`
   - 现有仪表盘内容（标题栏 + 日期 + 注册 widgets）提取为 `DashboardPage` 容器作为 Page 0
   - 侧边栏选中项切换 QStackedWidget 的 currentIndex
3. 标题栏按钮（`theme_btn`、`pin_btn`、`export_btn`）移至侧边栏底部，保留全部功能
4. 标题栏和日期标签只在「记账」页面显示（或移至侧边栏顶部）

**影响范围**：`app/main_window.py`、`app/__init__.py`、新增 `app/sidebar.py`

**验收标准**：
- [ ] 侧边栏 2 项可点击切换，当前页高亮
- [ ] 记账页功能与切换前完全一致（输入/保存/表格/图表/主题）
- [ ] 底部按钮（主题/置顶/导出CSV）功能正常
- [ ] 主题切换时侧边栏颜色联动
- [ ] pytest 全绿

---

#### L-02：kkrb.net API 客户端

**目标**：封装对 kkrb.net 的 HTTP 请求，提供干净的 Python 接口。

**具体设计**：
1. `app/kkrb_client.py` — 新增模块（零外部依赖，用 `urllib.request`）：
   - `fetch_ov_data() -> dict` — 调用 `POST /getOVData`，返回制造产物数据
   - CSRF token 管理：首次请求从首页 HTML 提取或从响应头获取，后续复用
   - 超时控制（~10s），失败时抛出自定义异常或返回 None
   - 请求频率限制：不做主动轮询，仅在用户切换到对应页面时拉取
2. 数据模型（dataclass）：
   - `CraftingProduct` — 台位名、产物名、利润、售价、出售时间

**影响范围**：新增 `app/kkrb_client.py`

**验收标准**：
- [ ] `fetch_ov_data()` 返回结构化数据，字段完整
- [ ] 网络超时/失败时优雅降级，不阻塞 UI
- [ ] 不需要额外 pip 依赖（纯 stdlib）

---

#### L-03：制造利润页面

**目标**：展示 4 个制造台位的最新推荐产物。

**具体设计**：
1. `app/crafting_page.py` — 新增 `CraftingPage`（QWidget）：
   - 页面标题：「制造产物推荐」
   - 4 个卡片，每个卡片对应一个制造台位（技术中心/工作台/制药台/防具台）
   - 每个卡片展示：台位名、产物名、当前利润、理想售价、建议出售时间
   - 按利润从高到低排序
   - 用一个「刷新」按钮手动拉取最新数据（不自动轮询）
   - 加载中状态：显示「加载中…」
   - 加载失败：显示「数据获取失败，点击重试」
2. 数据来源于 `kkrb_client.fetch_ov_data()`
3. 注册到 QStackedWidget 作为 Page 1

**影响范围**：新增 `app/crafting_page.py`、`app/__init__.py`、`app/main_window.py`（注册页面）

**验收标准**：
- [ ] 4 个台位卡片正确展示，按利润排序
- [ ] 刷新按钮重新拉取数据
- [ ] 网络失败时显示错误提示，可重试
- [ ] 主题切换时卡片颜色联动
- [ ] 切换页面再切回，数据不丢失

---

#### L-04：卡战备推荐页面

**目标**：输入目标战备值，显示最优的多个市场直购方案。

**具体设计**：
1. `app/gear_page.py` — 新增 `GearPage`（QWidget）：
   - 输入区：QLineEdit 输入目标战备值（支持 K/M/B 后缀，复用现有 `formatting.py`）
   - 「查询」按钮
   - 结果区：展示匹配到的方案列表
   - 每个方案卡片展示：
     - 方案标题（方案 #1, #2...）
     - 总花费、最终战备值
     - 装备清单表格（装备名/磨损度、花费、战备值、来源）
     - **不显示**溢价/差价
   - 匹配逻辑：找到最接近目标值的档位，显示该档位所有方案
   - 无匹配时：显示「未找到匹配方案」
2. 数据来源于 `kkrb_client.fetch_cpv_data()`
3. 注册到 QStackedWidget 作为 Page 2

**影响范围**：新增 `app/gear_page.py`、`app/__init__.py`、`app/main_window.py`（注册页面）

**验收标准**：
- [ ] 输入目标值（如 150000），显示匹配的 112,500 或 187,500 档位方案
- [ ] 方案卡片展示装备名、磨损度、花费、战备值、来源
- [ ] 不展示溢价/差价
- [ ] 输入金额格式兼容（支持 K/M/B、¥ 前缀、千分位）
- [ ] 网络失败时显示错误提示，可重试

---

### 技术债（2026-08-12，C4-债1 批次 code-review 非阻断建议，来源：code-review 子智能体）

| Ticket | 标题 | 类型 | 强度 |
|--------|------|------|------|
| C4-债2 | KPI 动画结构性根治（per-tile 独立动画槽）：共享单槽 + 出槽落终（`setCurrentTime`）是收敛而非根治——每磁贴独立动画槽使出槽动画可寻址，消除「新动画启动即截断旧动画至终值」的视觉语义（A1）；顺带 `_countup_anim`/`_countup_anim_label` 成对读写 Data Clump 并入结构（A2）、`==` 改 `is` 引用比较（S1，app/kpi_presenter.py:189） | 重构（状态模型） | 🟡 Worth exploring |

---

## 已完成归档

### 技术债批次（2026-08-12，kickoff 轻量档，基线 8bc4e68）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C4-债1 | KPI 动画竞态修复（per-label 分槽 + 出槽动画优雅落终，回归 5 用例覆盖 100%） | ✅ 2026-08-12 | `e26f1a6` + `cc937c9`（merge `2a66972`/`8ba15eb`） |

### C7（2026-08-12，kickoff 全自动档）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C7 | 存储 seam 容错收敛（_try_load 委托 + InvalidToken 容错，3 回归用例） | ✅ 2026-08-12 | `c5eecfe` |

### C6（2026-08-12，kickoff 全自动档）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C6 | 删除 Registry 插件系统（registry.py 删除 + AST 守卫 2 测试） | ✅ 2026-08-12 | `c9b7f3e` |

### C5（2026-08-12，kickoff 全自动档）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C5 | calculator 展示边界（比率单源 format_rate + 删孤儿报告，calculator 579→412 行） | ✅ 2026-08-12 | `d718a3e` |

### C4 系列（2026-08-12，kickoff 全自动档，基线 98b2ee1）

| Ticket | 标题 | 完成 | 提交 |
|--------|------|------|------|
| C4-01 | widget 装配抽离（build_dashboard + DashboardBundle，main_window 1002→831 行） | ✅ 2026-08-12 | `f53a1ea` |
| C4-02 | KPI 渲染收敛（KpiPresenter 三出口，main_window 831→764 行） | ✅ 2026-08-12 | `0ed4f76` |
| C4-03 | C4 文档同步收尾（CODE_WIKI 4.18/4.19 + 叙述 + doc_sync） | ✅ 2026-08-12 | 波末文档批次 |
---

### 架构加深 C1/C2/C3（2026-08-11，来源：improve-codebase-architecture 报告候选；功能 merge `633f549` + 评审快修 merge `c78acc4`，527/527）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| 01 | KkrbClient 并发加锁 — `threading.Lock` 整体持锁（缓存检查→握手→请求→缓存写入临界区，`_ensure_csrf` 无锁内重入），并发下握手恰一次、缓存无脏读——C2 共享 client 必要前提 | 架构（并发安全） | 2026-08-11 | `dbd6488` |
| 02 | 注入 seam + 共享 client + ProfitPage 单出口 — `FetchPageBase`/`ProfitPage`/`MainWindow` 构造注入 client（None → 自建，生产唯一创建点仍在 MainWindow）；利润页两子页共享单一 client；`profit_page.preload()/apply_theme()` 单出口扇出（C1 前过渡态仅扇出 exchange，行为与现状等价）；测试由此获得「注入 fake 即断网」能力 | 架构（seam） | 2026-08-11 | `45ae7f6` |
| 03 | 删除 offscreen 哨兵 + 测试迁移构造注入 — `preload()` 不再读取 `QT_QPA_PLATFORM` 环境变量；16 处直构点全部迁移构造注入 stub client，零真实网络、零实例级私有属性 monkeypatch | 架构（测试 seam） | 2026-08-11 | `df59a60` |
| 04 | CraftingPage 渲染对齐 — 每卡构建期持有全部标签直接引用（删 `layout.itemAt` 回读）；空数据显示显式占位文案；删除模块级 `_EMPTY_STATION` 假领域对象——空数据渲染不构造任何 CraftingProduct 实例 | 架构（深模块） | 2026-08-11 | `fa73589` |
| 05 | 错误/空态分离（`_render_error` 钩子） — 基类新增钩子，默认实现 = 空态渲染（与既有 `_on_fetch_error` 行为逐字节等价）；`_on_fetch_error` = status label 逻辑 + `_render_error()`；制造页覆盖为「加载失败，点击重试」卡片，与空态「暂无数据」可区分 | 功能（UX 修复） | 2026-08-11 | `2a5340d` |
| 06 | get_color 未知键 warning — 未知键 `logger.warning`（含键名）后返回 `""` 不 raise；`generate_qss` 直接索引语义不变——「漏改键 → 静默失效」变「日志可见」 | 架构（契约） | 2026-08-11 | `d8fd496` |
| 07 | TableWidget/CraftingPage `apply_theme` 钩子 — 表格基于 `draw()` 缓存（`_last_records/_last_today`）重渲染行内颜色、**不重新取数**；制造页显式空实现（样式全部由 QSS 选择器驱动）；ProfitPage 扇出 crafting + exchange | 架构（契约） | 2026-08-11 | `2d21325` |
| 08 | 树遍历契约 + refresh_theme 重写 — 启动期递归收集 `_theme_refreshers`（自顶向下、父拥有子树）；`refresh_theme` = QSS + 按钮/置顶样式 + refreshers 统一调用，与数据刷新彻底解耦；KPI 磁贴 `_apply_kpi_styles()` 另法保持；启动期同样执行一次 refreshers（保 sidebar 首帧主题完整） | 架构（深模块） | 2026-08-11 | `644e7fb` |
| 09 | AST 全键守卫 + 全链路抽查 — app/ 下 `get_color` 字面量调用点 + `_PACKAGE_CONFIG`/图表 series color_key → 双主题均存在且非空；light→dark→light 全链路抽查（exchange 标签/分隔线、table 行按钮、sidebar、chart、input）；craft 卡内联 styleSheet 无颜色字面量断言 | 测试（防复发） | 2026-08-11 | `45ddffc` |
| 10 | SettingsStore schema 所有者 — 公开 `DEFAULTS`（geometry/pinned/theme/animations）与 `KNOWN_KEYS`；`update(patch)` 读当前原始 dict → 合并（未知键保留）→ 原子写 → 返回新 dict，取代全量覆盖写；`encode_settings` 降级模块私有 `_encode_window_state` | 架构（深模块） | 2026-08-11 | `9678349` |
| 11 | MainWindow 设置接线 + 常量收敛 + AST 守卫 — `__init__` 设置读取改走 `_KEY_*` 模块常量（消灭裸字符串键）；`_save_settings` = `_encode_window_state` + animations 启动值 + current_account 合并 + `update()` 返回值回写——animations 纳入持久化闭环、未知键端到端保留 | 架构（收敛） | 2026-08-11 | `a96775d` |

### AA 系列（2026-08-11，架构加深批次 code-review 非阻断建议；merge `25082df`，532/532）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| AA-01 | KPI signal 计算抽取 — `_apply_kpi_styles` 与 `_update_summary` 重复段抽模块级纯函数 `_kpi_signal`（委托 presentation.format_window_text，信号判定单一来源）；两调用点 + AST 锁定 | 重构（消除重复） | 2026-08-11 | `70cb749` |
| AA-02 | craft 卡重置抽取 — `_render_data` 空槽位循环与 `_render_error` 抽 `_reset_card(card, product_text)`；「暂无数据」/「加载失败，点击重试」文案保持可区分 | 重构（消除重复） | 2026-08-11 | `31773c9` |
| AA-03 | `kkrb_client.reset()` 纳入锁边界 — `with self._lock:` 与 `_post_json` 同边界（无锁内重入）；确定性锁边界测试 + 并发 fetch×6+reset 压力测试 | 健壮性（并发边界） | 2026-08-11 | `379fa6a` |
| AA-04 | 编码函数公开命名 — `_encode_window_state` → `encode_window_state`（纳入 `__all__`），main_window import 与调用点同步——`__all__` 私有与真实跨模块依赖矛盾消除 | 重构（协议表面） | 2026-08-11 | `10423c6` |

### Z 系列（2026-08-10，主题联动收尾，来源：U-03 遗留）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| Z-01 | 兑换页 SEPARATOR 分隔线主题联动 — `_build_package_card` 分隔线引用存 `card._sep`；`apply_theme()` 循环内补齐分隔线运行期刷新（构建期冻结 → 亮→暗切换残留浅色线，SEPARATOR 双主题值不同已实证）；`tests/test_theme_roles.py` 新增双主题循环用例 + `test_ui_smoke.py` 集成断言扩展（theme_btn 点击链路）；Falsify 红验证（摘刷新 → 2 测试实红 → 恢复全绿）；测试 483→484 | 修复（主题联动） | 2026-08-10 | 本提交 |

### Y 系列（2026-08-10，多账号记账，kickoff 2026-08-10 基线 `e5a62c2`；功能 merge `900f50a` + 评审修复 merge `39d9595`）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| Y-01 | 账号存储层 — `account_store.py` 业务模块（`AccountStore(accounts_dir=DATA_DIR/accounts)`：list_accounts 目录扫描/稳定排序、create_account 返回 None=成功/可读拒绝原因（H5 空库起步只建目录）、resolve_account 兜底回退主账号 + 空库自建、new_store/account_dir DataStore 路径注入继承原子写/损坏恢复/滚动备份；`DEFAULT_ACCOUNT_NAME=主账号`、`ACCOUNTS_DIR_NAME=accounts`、`validate_account_name` 校验）；ADR-0005 落档；test_account_store.py 30 用例（list 三态/create 14 非法名 parametrize/resolve 四态/DataStore 注入/全新环境，全 tmp_path 显式注入） | 功能（新增） | 2026-08-10 | `c816de2` |
| Y-02 | 旧数据迁移 — `migrate_legacy_to_default(data_dir=None)`：accounts/ 不存在 **且** 旧 data.json 存在 → 复制 data.json + 全部 `data.json.bak*` 到 accounts/主账号/ 并写 `.migrated_v2` marker；accounts/ 已存在（含空）/marker 存在 → 跳过（幂等）；复制非移动永不删源（O-22 铁律）；OSError → warning 不中断不写 marker；main.py 接线（O-22 迁移之后、MainWindow 构造之前，AST 顺序断言防复发）；+9 用例 | 功能（数据迁移） | 2026-08-10 | `9296c40` |
| Y-03 | 启动解析当前账号 — MainWindow 注入 seam 定案（`__init__` 新增 `account_store` 参数；**仅当未注入 store/logic 时才走账号解析**）：settings.current_account → resolve_account 兜底（缺失/非字符串/目录不存在 → 回退主账号）→ new_store 构造 DataStore；`_save_settings` 合并 current_account（注入模式不写 key，geometry/pinned/theme 不丢）；`_update_account_title` 标题栏「Delta Force Dashboard · <账号名>」；settings_store.py 零改动；+8 用例（account_window_factory 注入完整解析链路 + UI 层 AST 防复发——main_window/sidebar 不得含 "accounts" 字面量） | 功能（新增） | 2026-08-10 | `0da9b09` |
| Y-04 | 侧边栏账号区 — sidebar 顶部账号区（「👤 账号」标题 + QComboBox account_combo + 「➕ 新建账号」按钮），信号 account_selected(str)/create_account_requested()；`set_accounts(names, current)`（blockSignals 防程序刷新误触发）/`set_account_area_visible()`；130px 宽度保持（不动 width()==130 断言）；MainWindow `_create_account`（QInputDialog 命名 → create_account 校验，非法名 QMessageBox 可读提示、零目录 → 刷新列表，当前账号不变决策 6，注入模式防御 return）；`app/ui_text.py` EMOJI 扩展 account/new_account；账号区 QSS；+19 用例 | 功能（UI） | 2026-08-10 | `c1b5525` |
| Y-05 | 账号切换 — `_on_account_selected(name)` 接线 sidebar.account_selected：目标账号 new_store + 重载 logic → cancel_edit/clear_fields/cancel_reuse（防跨账号污染）→ count-up 上一帧归零（数据源更换不做误导动画）→ refresh_display 全量刷新（表格/曲线/汇总/今日状态）→ 标题 + 下拉选中同步 → `_save_settings` 落盘 current_account；同账号 no-op（不重载不落盘）；未知账号/注入模式防御 return；利润页零触碰；+10 用例 | 功能（UI） | 2026-08-10 | `37b8fb4` |
| Y 系列评审修复 | code-review 三轴（固定点 `4fc4019`）：F1 `validate_account_name` 补控制字符拒绝（ord<32）+ `MAX_ACCOUNT_NAME_LEN=64`（65 拒/64 边界合法）+ create_account mkdir try/except OSError → 可读原因；F2 `_ensure_default_account` mkdir OSError → warning 仍返回主账号名（启动兜底不崩）；F3 resolve_account 命中目录分支补 validate_account_name（非法目录名回退主账号）；S2 `set_account_area_visible(visible)` 简化为无参 `hide_account_area()`；S3 `_two_account_env` 固定日期改相对 now（保存/删除断言与墙钟解耦）；不改动 S1/F4/F5（已确认安全）；+9 用例；全量 477/477、覆盖率 92.75% | 修复（评审） | 2026-08-10 | `09fa722` |

### W 系列（2026-08-09，微交互打磨，来源：U-06 遗留方向）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| W-01 | KPI 数字 count-up — `motion.animate_value`（数值插值动画，动效开关关闭直接落终态）+ `_set_kpi_value`（旧值→新值 300ms 滚动，复用 format_signed_money 逐帧格式化，数据不足/数值未变直接设置）+ `_last_summary_total/_last_cash_delta` 上一帧值 | 功能（UI） | 2026-08-09 | `03989ea` |
| W-02 | 非法输入 shake — `MoneyLineEdit._shake`（QPropertyAnimation 150ms 水平平移 [-6,6,-4,4] 回原位，状态从非 invalid 变 invalid 时触发防抖） | 功能（UI） | 2026-08-09 | `03989ea` |
| W-03 | 按钮 pressed 下沉反馈 — QSS 全局 `QPushButton:pressed` 1px 下沉（saveBtn/refreshBtn/queryBtn 各自 pressed padding 覆盖优先，补齐其余按钮一致） | 功能（UI） | 2026-08-09 | `03989ea` |
| W-04 | 图表 hover 数据点高亮 — `_hover_markers`（仓库/现金各一 ScatterPlotItem，13px 大圆点 + 主题底填充 + 系列色描边），hover 时 setData 定位、离开隐藏、主题切换描边色跟随 | 功能（UI） | 2026-08-09 | `03989ea` |

### V 系列（2026-08-09，架构深化，来源：improve-codebase-architecture 报告候选 1）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| V-01 | kkrb_client 解析拆出 — `kkrb_models.py` 零依赖叶子（CraftingProduct/AmmoPackageItem/KkrbError）+ `kkrb_parsing.py` 纯函数解析（parse_ov_response/parse_ammo_package_response，畸形输入矩阵 28 用例）+ `kkrb_client.py` 收敛为会话/传输/缓存（删除类内私有解析方法，`__all__` 重新导出保持协议表面，调用方零改动） | 架构（深模块） | 2026-08-09 | `4c0f590` |
| V-02 | fetch_page_base 状态机拆分 — `app/load_state.py` LoadState 四态状态机（idle/loading/loaded/failed，`can_load()` 仅挡 loading 防重入不挡手动刷新 + preload 补 is_loaded 守卫）+ `is_loaded` 公开 property（测试不再访问 `_loaded_once`/`_loading` 私有字段）+ 转移矩阵 8 用例 + 刷新回归测试；worker 生命周期与 client 注入点保留 | 架构（深模块） | 2026-08-09 | `11858da` |
| V-03 | SettingsCodec 纯函数 — `settings_store.py` 增 `decode_geometry_hex`（hex→bytes，损坏/过短兜底 None）/`decode_legacy_geometry`（旧 Tkinter 格式含负坐标，正则 fullmatch）/`encode_settings`（bytes hex 编码），保持零 Qt 依赖；`main_window._setup_window` 双格式解析与 `_save_settings` 改走 codec（-25 行手写分支）+ 编解码 10 用例 | 架构（深模块） | 2026-08-09 | `11858da` |
| V-04 | 主题双轨收敛 — 删除 `button_style()`（edit_save 与 QSS #saveBtn 重复、danger 改 QSS 属性选择器 `QPushButton#reuseBtn[state="danger"]`，input_panel 用 setProperty+repolish 切换）+ exchange 包标签内联字号收敛进 QSS（只留动态色）+ `tests/test_theme_qss.py` 4 用例（选择器/色值/删除守卫/属性切换） | 架构（深模块） | 2026-08-09 | `11858da` |
| V-05 | kkrb_client 传输层补测（V-01 收尾）— `tests/test_kkrb_client.py` FakeOpener 脚本式注入（替换 `client._opener` seam）：CSRF 握手成功+缓存复用/首页/getMenu/ValueError 降级/cookie 缺 token 重握手、TTL 缓存命中/过期、OSError/ValueError/畸形 JSON/空响应→KkrbError、请求头完整性、reset 清会话、两 fetch_* 端到端真实传输共 22 用例；模块覆盖率 36%→100%（总 93%）；附 `_user_agent` 残留 `ProfitCalculator/1.0`→`DeltaForceDashboard/1.0` | 测试（补强） | 2026-08-09 | `59275d9` |

### U 系列（2026-08-09，UI 视觉打磨）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| U-01 | KPI 磁贴 + 顶部两栏 — 汇总拆「说明行 + 数值行」磁贴（summary_style 22px 信号色/16px 数据不足）、输入卡限宽 520 与 KPI 卡并排（`_split_kpi_text`） | 功能（UI） | 2026-08-09 | `b5d230e` |
| U-02 | 排版刻度 — 按钮两级（primary 13/600、secondary 11/500）、页面标题 `pageTitleLabel` 16px 分层、字号归位（10→11/14→15/craftProduct 18→16）、图表弹性翻转（min 200 + 表格 vertical AsNeeded 滚动兜底） | 功能（UI） | 2026-08-09 | `251baec` |
| U-04 | 侧边栏重做 — 宽度 130、选中态浅底 pill（NAV_SELECT_BG）+ 3px accent 指示条（border-left 透明占位零位移） | 功能（UI） | 2026-08-09 | `222787d` |
| U-05 | emoji/图标一致性 — 新增 `app/ui_text.py` EMOJI 单一来源（9 键），4 文件散落字面量清零 + 全局 font-family 补 Segoe UI Emoji | 功能（UI） | 2026-08-09 | `f0741ff` |
| U-06 | 反馈型动效 — 新增 `app/motion.py`（fade_in_widget/animate_property）：切页 120ms 淡入、曲线 opacity 0→1 揭示 250ms、保存指示 180ms 淡入；hover 过渡因 QSS 无 transition 跳过（DEV_LOG 记取舍） | 功能（UI） | 2026-08-09 | `d430cd7` |
| U-07 | 交互小修批量 — 可点「重试」label（`_ClickableLabel` + 手型光标）/ QPushButton `:focus` outline 焦点态 / 今日未录入状态 pill（WARNING 系底+边框）/ 日期标签左对齐（消轴线错位）/ QStatusBar 死样式删除 / 中性 badge 浅底深字（MUTED_BG+TEXT_SECONDARY，AA ≥4.5:1） | 修复（UI） | 2026-08-09 | `7d5878c` |
| U-08 | code-review 评审修复 — 动效全局开关（settings `animations=false`）+ fade_in 竞态防护（stop 旧动画）+ `animate_property` 类型收紧 QObject / exchangePackageLabel 内联 14→15px（U-02 归位失真修复）/ `EMOJI['ok']` 收敛 main_window CSV 提示 + 测试 regex 补 ✓、Path 绝对化 / 曲线动画 250→200ms（feedback-only 上限） | 修复（UI） | 2026-08-09 | `a77bcfb` |
| U-09 | 用户实测反馈修复 — ①图表弹性回退：chart 固定小卡片 stretch 0、表格恢复 stretch 1（U-02 翻转挤压表格，用户要求全量展示）②30 天视图全量：行高固定 26px + 视图按钮 28→24 + 卡片边距压缩 ③「今日未录入」pill 亮色不可见 → #F1D9A0/#6E4A08 ④利润页亮色背景纯黑（全局 QWidget 字体族规则致 palette.window 背景）→ profitPage/profitContainer 显式主题 BG ⑤**方案 A 屏幕自适应**：`_window_preset(screen_h)` 纯函数——可用高 ≥1000 → 窗口 1020 + 图表 [160,240]（1080p 图表 +90px），小屏回退 920/[140,150]；两档表格全量参数一致 | 修复（UI） | 2026-08-09 | `a70d594` / `8b4661e` |
| U-10 | 利润页启动预加载 — `_preload_profit_page` 同时预加载制造产物 + 兑换利润（此前兑换利润等首次点击才拉取 10s HTTP，点击卡顿）；各自后台线程 + kkrb 60s TTL 缓存复用；测试用轮询等待消除 qWait 固定时长与线程调度的竞态（首跑通过次跑失败问题） | 功能（性能） | 2026-08-09 | `eb2e4c7` |
| U-11 | 崩溃修复（用户实测：点利润→切回→再点利润闪退）— 根因：U-06 切页淡入的 QGraphicsOpacityEffect 挂在 QStackedWidget 页面上，快速 hide/show 触发 Qt 崩溃路径；修复：移除切页淡入动画（保留曲线/保存指示动画）+ `fade_in_widget` 补 dynamic property 悬空指针清理（DeleteWhenStopped 后 QObject* 悬空）+ main.py 崩溃现场捕获（faulthandler crash.log + sys.excepthook + qInstallMessageHandler Qt 钩子）+ 切页 20 次循环回归测试 | 修复（崩溃） | 2026-08-09 | `86b8ae0` |
| U-03 | 色彩角色系统化（保留多色）— 7 包色收敛单一装饰键 `PACKAGE_COLOR_0~6`（删 CHART_SERIES_*/PACKAGE_COLOR_* 双套键；键名如实——CHART_SERIES 实际只服务兑换页包色，chart_widget 不引用）；亮暗同值键不抽常亮色（保留双主题定义防 Locality）；装饰≠语义（**dark 曾 CHART_SERIES_2/3 与 FG_POS/FG_NEG 完全同值**——5 级包=亏色/3 级包=涨色，已修）；明度带量化（light L∈[0.20,0.32] / dark L∈[0.72,0.84]，S≥0.55，colorsys 断言）；两两 ΔE76≥25 可分辨；AA 4.5:1 对比度底线 + `tests/test_theme_roles.py` 8 机器断言（全可证伪，目检降级）；修正 exchange_page.py:34「hex 回退色」谎言（`get_color` 缺失键返回 `""`，旧 `or color` 回退键名字符串=无效色）+ **评审修复**（code-review 三轴：ExchangePage.apply_theme 主题切换重解析包标签色——改动前双主题同值潜伏、改动后残留对比度 1.26:1 被 Falsify 轴抓到；theme_guard fixture 防主题状态泄漏；6 位 hex 格式断言封 8 位静默丢 alpha/rgba 裸崩） | 架构（UI） | 2026-08-09 | `ff81407`/`99efd87` |

### M 系列（2026-08-05，修复）

| Ticket | 标题 | 类型 | 完成日期 |
|--------|------|------|----------|
| M-01 | 暗色主题图表网格色 `rgba(255,255,255,.05)` 无法被 pyqtgraph 解析崩溃（`ValueError: Unable to convert rgba(...) to QColor`）→ `CHART_GRID` 改 `#RRGGBBAA` 八位十六进制 + 回归测试（双主题全图表取色键 `pg.mkColor` 解析校验） | 修复（启动崩溃） | 2026-08-05 |

### L 系列（2026-08-05，Delta Force 游戏工具扩展，ADR-0004）

| Ticket | 标题 | 类型 | 完成日期 |
|--------|------|------|----------|
| L-01 | 侧边栏导航系统 — 左侧栏 + QStackedWidget 页面切换 + 现有按钮移至侧栏底部 | 架构（UI） | 2026-08-05 |
| L-02 | kkrb.net API 客户端 — `kkrb_client.py`，封装 `getOVData` 调用（战备 `getCPVData` 随 L-04 移除） | 功能（新增） | 2026-08-05 |
| L-03 | 制造利润页面 — 4 台位推荐产物展示（台位名/产物名/利润/售价/出售时间） | 功能（新增） | 2026-08-05 |
| L-04 | 卡战备推荐页面 — 输入目标值 → 匹配档位 → 多方案展示（含装备名/磨损度/花费/战备值/来源） | 功能（已移除） | 2026-08-05 |

### X 系列（2026-08-06，子弹自选包兑换利润模块）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| X-01 | 子弹自选包兑换利润模块 — `ExchangePage` + `AmmoPackageItem`/`fetch_ammo_package_data()` + `ProfitPage` 标签页容器 + 侧边栏「制造」→「利润」 | 功能（新增） | 2026-08-06 | `8c6393e` |
| X-02 | 兑换利润页面增加 4 种特殊子弹自选包 — 通行证基础/高级、进阶物流、特级物流 + 7 包 4 列网格 | 功能（扩增） | 2026-08-06 | `7977de6` |
| X-03 | 消除两个代码气味 — `_PACKAGE_CONFIG` NamedTuple（Primitive Obsession）+ `exchangeGradeAndCount` 重命名（Mysterious Name） | 重构（代码气味） | 2026-08-06 | `c9bdeb7` |

### R 系列（2026-08-04，框架增强 ★ 级）

| Ticket | 标题 | 类型 | 完成日期 |
|--------|------|------|----------|
| R-01 | Entity 抽象基类：`BaseRecord` — `DayRecord` 泛化为可继承基类，新项目只需定义字段 | 架构（泛化） | 2026-08-04 |
| R-02 | DataStore 泛型化 `DataStore[T]` — 支持多数据文件、多实体，独立序列化/验证规则 | 架构（泛化） | 2026-08-04 |
| R-03 | 插件式 Widget 注册 — `app.register_widget()`，增减 widget 无需改 MainWindow | 架构（可扩展） | 2026-08-04 |
| R-04 | CSV 导入 — 基于已有 `export_csv` 对称实现导入功能 | 功能（新增） | 2026-08-04 |
| R-05 | 多层级聚合 — 日→周→月→季→年 多级下钻展示 | 功能（新增） | 2026-08-04 |
| R-09 | 主题 token 标准化 — 30 token → 50+ 通用设计 token，可独立发布 | 架构（UI） | 2026-08-04 |

### F 系列（2026-08-02）

| Ticket | 标题 | 类型 | 强度 | 完成日期 | 提交 |
|--------|------|------|------|----------|------|
| F-01 | 文档同步自动化：`scripts/doc_sync.py`（测试数/模块行数/方法表）+ pre-commit 防漂移钩子 | 运维（文档自动化） | 🟡 Worth exploring | 2026-08-02 | `fc28fff` |
| F-02 | 数据迁移「源清理时间点」策略 + `.migrated` 完成标记 | 运维（数据迁移） | ⚪ Speculative | 2026-08-02 | `fc28fff` |

### J 系列（2026-08-03，保留 30 + 多视图 7/30 切换，规格见 `CONSENSUS.md` §7 / ADR-0003）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| J-01 | 保留上限 7→30：`config` 新增 `RETENTION_LIMIT=30` + `rotate_weekly` 改引用它 + `format_summary`/`format_saved_indicator` 文案联动（N 不写死 7） | 功能（数据模型） | 2026-08-03 | `569b97f` |
| J-02 | 视图切换 7/30：`TableWidget` 按钮组（7/30）+ `view_changed(int)` 信号 + 分栏均分 `mid=ceil(n/2)`；`MainWindow` 持 `_view_n`（默认 7）、`_get_records`/`_update_summary` 走 `_view_n`；`chart` 随 records 自适应 | 功能（UI） | 2026-08-03 | `569b97f` |

### K 系列（2026-08-04，保存保留两位小数 + 现金总变化展示）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| K-01 | 数据保存保留两位小数：`save_record` 存储前 `round(cash/warehouse, 2)`（银行家舍入），不变式告警用舍入后值 | 功能（数据精度） | 2026-08-04 | `3efc77c` |
| K-02 | 汇总条并排双标签：`cash_summary`/`format_cash_summary` 纯函数 + `_cash_summary_label`（最近 7/30 条现金总变化，随视图联动） | 功能（UI） | 2026-08-04 | `3efc77c` |

### 第二轮架构评审（2026-08-04，8 候选全实施）

| 候选 | 标题 | 类型 | 强度 | 完成日期 | 提交 |
|------|------|------|------|----------|------|
| 1 | 展示文本簇拆出 `presentation.py`（format_* 纯函数） | 重构（深模块） | 🟢 Strong | 2026-08-04 | `3964d83` |
| 6 | 汇总四合一参数化 — `format_window_text` 替代 format_summary + format_cash_summary | 重构（去重） | 🟢 Strong | 2026-08-04 | `3964d83` |
| 3 | 原子写协议合一 — DataStore 委托 `json_file.atomic_write_json` | 重构（去重） | 🟢 Strong | 2026-08-04 | `3964d83` |
| 2 | MainWindow 编排器变薄 — `reuse_candidate` 下沉 + `summary_style` 进 theme + `view_n` property | 重构（编排器） | 🟡 Worth exploring | 2026-08-04 | `3368a2c` |
| 4 | VIEW_DAYS 单源化 — 常规定义移入 `config.py` | 重构（常量） | 🟡 Worth exploring | 2026-08-04 | `d1e39cf` |
| 5 | 信号→颜色映射收敛进 theme — `signal_color` 统一入口 | 重构（收敛） | 🟡 Worth exploring | 2026-08-04 | `7ea4a26` |
| 7 | MoneyLineEdit 补 `set_value` 公开方法 — `_formatting` 泄漏消除 | 重构（seam） | 🟡 Worth exploring | 2026-08-04 | `4275479` |
| 8 | 图表几何抽纯函数 — `adaptive_range` 公开 + `ChartState` 只读状态 | 重构（可测试性） | 🟡 Worth exploring | 2026-08-04 | `4f76876` |

### H 系列（2026-08-03，图表样式对齐 + 布局）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| H-01 | 图表样式对齐原型评审修正版（删填充 + hover 改所属 ViewBox 堆叠定位）+ 曲线图置底为 7/30 天表格预留弹性高度 | 功能（图表样式/布局） | 2026-08-03 | `d2b0076` |

### G 系列（2026-08-02，图表合并）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| G-01 | 图表双曲线合并到同一坐标系（双 Y 轴，方案 B，ADR-0002） | 功能（重构图表） | 2026-08-02 | `abc7119` |

### D 系列（2026-08-02）

| Ticket | 标题 | 强度 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| D-01 | 趋势判定收敛：`format_signed_money` 纯函数 | 🟢 Strong | 2026-08-02 | `cea6bb7` |
| D-02 | 原子写 seam：`json_file.py` + `SettingsStore` | 🟡 Worth exploring | 2026-08-02 | `4a5ede4` |
| D-03 | 序列化边界：`data`→`dict[str, DayRecord]` + `serialize()` | 🟡 Worth exploring | 2026-08-02 | `54a23d0` |
| D-04 | 被测试的路径=真实路径：QTest 打事件链路 | 🟡 Worth exploring | 2026-08-02 | `cfb15e1` |
| D-05 | 现金⊆仓库不变式单一所有者 | ⚪ Speculative | 2026-08-02 | `2349139` |
| D-06 | 删浅表面：`DayRecord.total` 删除 | ⚪ Speculative | 2026-08-02 | `2349139` |
| D-07 | 展示渲染移出编排器 | 🟡 Worth exploring | 2026-08-02 | `2349139` |
| D-08 | D 系列评审修正：signals 叶子收敛（层反转）+ 读取告警异常详情 + 文档漂移同步 | 🟡 Worth exploring | 2026-08-02 | `478b23e` |

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
| C5 | verify_all 覆盖并入 pytest | 2026-08-01 | `0c6b8e3` |

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
| O-06 | 图表稀疏数据提示 | 功能（新增） | 2026-08-01 | `0f16e1c` |

### O 系列（2026-08-01，第二批 P1）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-08 | 保存前校验 cash ≤ warehouse 不变式 | 功能（新增校验） | 2026-08-01 | `d0af4d6` |
| O-09 | 加载时顶层 dict schema 校验 | 重构（健壮性） | 2026-08-01 | `d0af4d6` |
| O-10 | 打包配置纳入版本控制 | 运维 | 2026-08-01 | `20b5170` / `fa16d77` |

> 两个并行分支（A：O-01~O-03；B：O-04~O-05）经 merge 合入 main，合并提交 `c01c2c2` / `fdeca85`。合并时 `main_window.py` 模块级 logger 命名冲突（`logger` vs `_logger`）已收敛为 `logger`。

### O 系列（2026-08-01，第三批 P2）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-11 | CSV 导出金额统一格式化 | 重构（显示一致性） | 2026-08-01 | `082ce62` |
| O-12 | dev 依赖清单与版本锁定 | 运维 | 2026-08-01 | `082ce62` |
| O-13 | 编辑态关闭窗口确认 | 功能（新增） | 2026-08-01 | `082ce62` |
| O-14 | 7 日自动删除的可见性 | 功能（新增） | 2026-08-01 | `082ce62` |
| O-15 | 日志文件轮转 | 重构 | 2026-08-01 | `082ce62` |

### O 系列（2026-08-01，O-17/O-19/O-18 批次）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-17 | 自动清理提示文案与轮转语义不符（附显示基准统一为录入条数） | 修复 | 2026-08-01 | `9df5ee4` |
| O-19 | CODE_WIKI 与实现失同步（方法表/依赖版本/测试计数） | 文档 | 2026-08-01 | `9df5ee4` |
| O-18 | settings.json 运行态入库清理 | 运维 | 2026-08-01 | `dd47efa` |

### O 系列（2026-08-01，O-20 打包瘦身）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-20 | 打包 onedir 化 + 体积瘦身（exe 过大 + 启动慢） | 运维/性能 | 2026-08-01 | `5913a22` |

### O 系列（2026-08-01，O-21 UPX 压缩）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-21 | 打包 UPX 压缩瘦身（dist 117M→64M，源自优化清单 C 可选）+ O-20 `_MEI*` 残留清理待办闭环（905MB） | 运维/性能 | 2026-08-01 | `6978182` |

### O 系列（2026-08-01，O-22 数据目录统一）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| O-22 | 运行态数据统一到用户目录（exe 重建/移动不丢数据 + 一次性迁移） | 重构（数据路径） | 2026-08-01 | `9835387`/`c2e34f9` |

### O 系列（2026-08-01，评审关闭）

| Ticket | 标题 | 类型 | 关闭日期 | 关闭原因 |
|--------|------|------|----------|----------|
| O-C1 | `event.position()` 兼容 fallback | 防御性兼容 | 2026-08-01 | requirements 下限 PySide6>=6.6.0，`QMouseEvent.position()` 自 6.2 起保证存在；无真实触发路径（YAGNI） |
| O-C2 | 多选日期范围（7 日→30/90 日） | 核心数据模型变更 | 2026-08-01 | 7 日限制是产品决策；双栏表格（左 4 右 3）、图表、summary、rotate_weekly 均围绕 7 日架构，改动需重做表格布局与数据流，风险高、收益未明。若确需长周期视图应另立「多视图」工单而非扩展 |
| O-C3 | AppController 拆分 | 架构重构 | 2026-08-01 | 采纳清单撤回判断：MainWindow 514 行职责内聚（窗口/主题/置顶/信号/数据流/刷新），对当前规模是合理的协调者，拆分引入不必要间接层 |
| O-C4 | QSS 模板文件化 | 架构重构 | 2026-08-01 | 采纳清单撤回判断：两套主题用 f-string 生成 QSS 是社区常见做法；模板化需处理 PyInstaller 资源路径，收益低 |
| O-07 | 收益率目标参考线 | 功能（新增） | 2026-08-01 | 目标语义未定义（累计收益 vs 逐日收益率），画在哪条序列上不明确；实现成本高于收益，YAGNI 关闭 |

### O 系列（2026-08-01，决策拍板）

| Ticket | 标题 | 类型 | 拍板日期 | 结论 |
|--------|------|------|----------|------|
| O-16 | CSV 导出大额金额 K/M 缩写精度丢失 | 重构/决策 | 2026-08-01 | ✅ 选 A 保持现状，`export_csv` docstring 注明取舍；B/C 留作备选 |

---

### E 系列（2026-08-02，运维清理）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| E-04 | 陈旧产物清理（stale pyc + 根目录旧数据源残留） | 运维 | 2026-08-02 | 随本提交（见 DEV_LOG 2026-08-02 运维条目） |

### E 系列（2026-08-02，评审关闭）

| Ticket | 标题 | 类型 | 关闭日期 | 关闭原因 |
|--------|------|------|----------|----------|
| E-01 | 数据保留「最近 7 条」可配置化 | 功能（新增） | 2026-08-02 | 用户拍板不做：不知道配置对用户有什么实际作用；当前按录入条数保留最近 7 条已满足单用户日常。报告论据失效——其引用的 `config.DATA_RETENTION_DAYS` 常量 O-17 已删除，现为 `rotate_weekly(days=WEEK_DAYS)` |
| E-02 | 用户操作审计日志 | 功能（新增） | 2026-08-02 | 单用户本地工具无追责/合规场景；报告「为未来撤销铺路」不成立——覆盖写后日志只留「何时改」不留旧值，救不了撤销；真做撤销应做历史快照（`serialize()` 已具备基础）而非日志 |
| E-03 | 图表 PNG 脚本化导出 | 功能（新增） | 2026-08-02 | 用户明确不需要；唯一消费路径是 GUI 按钮，机器可读导出已有 `export_csv` 纯函数覆盖；无脚本化消费场景则 YAGNI 关闭（呼应 O-07 先例） |

---

## 工单状态说明

- **📝 已录入**：已记录但尚未进入开发计划（含未拍板的候选）
- **🔄 进行中**：正在开发中
- **✅ 已完成**：已合并验证通过
- **❌ 已关闭**：经评估决定不实施

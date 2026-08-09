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

> 活跃表（2026-08-09）：U-01~U-07 已归档，仅剩 U-03（色彩角色系统化）待办，等 U-01 完成后再评估是否要做。

| Ticket | 标题 | 类型 | 状态 | 强度 |
|--------|------|------|------|------|
| U-03 | 色彩角色系统化（不收敛单 accent）：多色保留，但统一明度/饱和度带 + 语义色与装饰色分离 + 兑换页/图表序列共用同一色板定义（去重复键） | 架构（UI） | 📝 已录入 | 🟡 Worth exploring |

---

## 工单详情

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
2. `app/exchange_page.py` — `_PACKAGE_CONFIG` 色键与图表序列共用色板键（当前 CHART_SERIES_0~3 与 PACKAGE_COLOR_0~2 两套定义，亮暗主题同值但语义重复），收敛为单一角色命名
3. 不做：不收敛为单 accent、不删 emoji、不改红涨绿跌

**影响范围**：`app/theme.py`、`app/exchange_page.py`、`app/chart_widget.py`

**验收标准**：
- [ ] 兑换页 7 色与图表序列色出自同一色板定义，无重复键
- [ ] 亮暗两主题下装饰色与语义色（涨跌）不混淆（评审目检 + 既有取色键测试覆盖）
- [ ] 两主题切换后颜色不变脏（与现状视觉对比）

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

## 已完成归档

### V 系列（2026-08-09，架构深化，来源：improve-codebase-architecture 报告候选 1）

| Ticket | 标题 | 类型 | 完成日期 | 提交 |
|--------|------|------|----------|------|
| V-01 | kkrb_client 解析拆出 — `kkrb_models.py` 零依赖叶子（CraftingProduct/AmmoPackageItem/KkrbError）+ `kkrb_parsing.py` 纯函数解析（parse_ov_response/parse_ammo_package_response，畸形输入矩阵 28 用例）+ `kkrb_client.py` 收敛为会话/传输/缓存（删除类内私有解析方法，`__all__` 重新导出保持协议表面，调用方零改动） | 架构（深模块） | 2026-08-09 | `待填` |

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

# Delta Force Dashboard — 项目介绍书

> **一句话**：每日记录现金和仓库价值两项数据，自动保留最近 30 条记录并绘制收益曲线，计算盈亏（视图 7/30 可切换）。
> **技术栈**：Python PySide6 + pyqtgraph
> **打包**：PyInstaller onedir（`dist/Delta Force Dashboard/`，exe + `_internal/`）

---

## 一、项目概述

Delta Force Dashboard 是一款 Windows 桌面工具，主要面向个人投资者。

**核心场景**：用户每天记录「当前现金」和「仓库价值（含现金）」两个数字，工具自动保留最近 30 条实际录入记录（间断录入不丢历史），视图 7/30 可切换，以表格展示每日盈亏变化，并以双曲线图可视化趋势。

**当前状态**：功能完整，架构已优化。PySide6 迁移完成，三阶段 P0-P5 + Phase 4（T-01~T-05）+ C 系列（C1~C9）+ O 系列（O-01~O-22）+ D 系列（D-01~D-08）+ F 系列运维（F-01 文档同步 / F-02 迁移源清理标记）+ J 系列（J-01 保留上限 30 / J-02 视图 7/30 切换，ADR-0003）+ K 系列（K-01 保存保留两位小数 / K-02 现金总变化展示）全部完成（O-07 经评估 YAGNI 关闭）。477 项测试全部通过。**L 系列**（2026-08-04）：Delta Force 游戏工具扩展——侧边栏 + 制造利润排行（ADR-0004），L-04 卡战备推荐已移除。**X 系列**（2026-08-06）：子弹自选包兑换利润模块——kkrb_client 新增 `AmmoPackageItem`/`fetch_ammo_package_data()`（7 种包类型网格展示，X-02 扩展通行证基础/高级 + 进阶/特级物流 4 包）、制造板块更名利润（X-01）、代码气味消除（X-03）；ProfitPage 重构为制造产物 + 兑换利润纵向堆叠。**Y 系列**（2026-08-10）：多账号记账——`account_store.py` 账号存储层（ADR-0005：`accounts/<账号名>/data.json` 目录即账号名、无元数据文件）+ 旧数据复制迁移为「主账号」（`.migrated_v2` 幂等、永不删源）+ 启动解析 `current_account`（settings.json，兜底回主账号）+ 侧边栏账号区（下拉 + 新建账号，H5 新账号空库）+ 账号切换（整体重载 + 取消编辑/复用态 + 落盘，同账号 no-op，利润页零改动）+ code-review 修复（F1~F3 边界防护 / S2-S3 简化）；477/477 测试绿，覆盖率 92.75%。主要能力：单实例保证、CSV 导出、今日未录入提醒、图表稀疏提示、文件日志（含轮转）、现金≤仓库不变式校验、加载结构校验、编辑态关窗确认、视图 7/30 切换（存储保留 30 条，切回 7 不丢数据）、数据目录统一到用户目录、迁移后旧数据源清理提示（F-02）、JSON 原子写 seam + 设置持久化收敛、序列化边界收敛（`data`→`dict[str, DayRecord]` + `serialize()`，ADR-0001）、共享信号叶子 `signals.py`（D-01 收敛）、现金⊆仓库谓词收敛（D-05）、展示渲染纯函数化（D-07）、CODE_WIKI 机械标记文档同步 + pre-commit 防漂移钩子（F-01）。**架构加深批次**（2026-08-11）：主题契约（C1-06 `get_color` 未知键 warning 化返回 `""` / C1-07 TableWidget·CraftingPage `apply_theme` 钩子 / C1-08 树遍历契约——启动期收集 `_theme_refreshers`、`refresh_theme` 重写与数据刷新解耦 / C1-09 AST 全键守卫 + 全链路抽查）、Fetch 家族（C2-01 KkrbClient `threading.Lock` 并发加锁、握手恰一次 / C2-02 构造注入 seam + 利润页共享 client / C2-03 删 offscreen 哨兵改测试构造注入 / C2-04 渲染对齐删 `_EMPTY_STATION` 假领域对象 / C2-05 `_render_error` 错误/空态分离钩子）、Settings schema（C3-10 SettingsStore 成为 schema 所有者——`DEFAULTS`/`KNOWN_KEYS`/`update(patch)` 合并语义未知键保留 / C3-11 `animations` 纳入持久化闭环 + 窗口层 `_KEY_*` 常量收敛）；**527/527 测试全绿，覆盖率 94%**。**C4→C7 架构批次**（2026-08-12，kickoff 全自动档，基线 98b2ee1 → f76828b）：C4 仪表盘装配直构（`app/dashboard_page.py` `build_dashboard` + DashboardBundle 8 成员，替代 registry 间接层；main_window 1002→764 行）+ KPI 双磁贴渲染收敛（`app/kpi_presenter.py` 三出口 update/apply_theme_styles/reset，reset 终止在途动画防账号切换残留帧）；C5 calculator 展示边界收敛（收益率文案单源 `format_rate` + 删除孤儿 HTML 报告，calculator 579→412 行）；C6 删除 registry 插件系统（`app/registry.py` 物理删除 + AST 守卫 2 测试，全库零残留）；C7 存储 seam 容错收敛（`_try_load` 委托 `try_load_json` 读写对称 + InvalidToken 容错降级）；**561/561 测试全绿**。**技术债批次**（2026-08-12，kickoff 轻量档，基线 8bc4e68）：C4-债1 KPI 动画竞态修复——per-label 分槽 + 出槽动画优雅落终（`setCurrentTime` 终帧防残留帧覆盖直落终态），回归 5 用例、kpi_presenter 覆盖 100%；**566/566 测试全绿**（延续债项 C4-债2 per-tile 根治见 TO-TICKETS 技术债区）。**技术债批次**（2026-08-12，kickoff 轻量档，基线 d33def8）：C4-债2 KPI 动画结构性根治——per-tile 独立动画槽 `_countup_anims: dict[QLabel, ...]` 取代共享单槽 + 出槽落终（A1 顶出截断消除 / A2 Data Clump 消解 / S1 引用比较随 dict 身份寻址消失），落值入口统一 pop + 优雅落终，测试 20→24、kpi_presenter 覆盖 100%；**570/570 测试全绿**（延续债项 C4-债3 动画子对象生命周期收敛见 TO-TICKETS 技术债区）。**技术债批次**（2026-08-12，kickoff 轻量档，基线 d3fbeff）：C4-债3 KPI 动画对象生命周期收敛——动画自然结束即回收（finished 回调 weakref 闭包破引用环 + identity 检查移除 entry + deleteLater；reset 显式 stop + deleteLater），presenter Qt children 与 dict 双双有界（原无界累积消除），顺带 4 label 互异前置条件 docstring + logic 类型标注；测试 24→26、kpi_presenter 覆盖 99%；**572/572 测试全绿，技术债区清零**。**技术债批次**（2026-08-12，kickoff 轻量档，基线 dcb941e）：C4-债4 chart 绘制动画生命周期收敛——`_play_draw_anim` 启动前 stop 旧动画（消除同目标 opacity 残帧竞态抖动，可见 bug）+ finished→identity→deleteLater 回收（动画子对象无界累积消除，chart 单文件闭环，motion 零改动）；测试 96→99；**575/575 测试全绿**（延续债项 C4-债5 图表动画生命周期后续观察见 TO-TICKETS 技术债区，⚪ Speculative）。**技术债批次**（2026-08-13，kickoff 轻量档，基线 641ab0c）：C4-债5 图表动画生命周期加固——`_clear_all` 停止在途绘制动画（stop + deleteLater + 句柄复位，语义即时化）；复核中发现的 `_shake` 收敛遗漏点一并加固（DWS 自删 + finished 清句柄，weakref 破环——工单「不用 weakref」定案被 Falsify 实测推翻：DWS + 强闭包环在「在途销毁」路径确定性 access violation，C4-债3 同款定案）；第 4 实例复核关闭（动画点全量盘点 5 处，不抽 motion helper）；**576/576 测试全绿**（延续债项 C4-债6/7/8 见 TO-TICKETS 技术债区）。**技术债批次**（2026-08-13，kickoff 轻量档全自动，基线 5103092）：C4-债6 fade_in_widget 生命周期收敛——stop 后同步清 `_fade_anim` property（DWS 不发 finished 的残留窗口结构性消除）+ finished 闭包 weakref 破环（C4-债3/5 同款定案，motion 覆盖 100%）；C4-债7 `_shake` finished 加 identity 检查（实证：Qt 同 target 同 property 自动停旧动画，并发路径从根上不可构造——identity 为防御/一致性对齐）；C4-债8 测试环境态自持（动效开关 prev + try/finally，真红真绿）；**578/578 测试全绿**（延续债项 C4-债9~12 见 TO-TICKETS 技术债区）。**技术债批次**（2026-08-13，kickoff 轻量档全自动，基线 f70347d）：C4-债9 fade_in_widget duration 护栏 `max(1, duration_ms)`（duration=0 实测比预测更硬——access violation 致 pytest 进程 abort，修复后返回有效动画 + property 收敛）；C4-债10 identity 惯用法提取候选复核关闭（显式 identity 比较恰 3 处，第 5 实例未出现）；C4-债11 删 `_saved_indicator_anim` 只写句柄（补契约测试填补 InputPanel 公开 API 链路缺口）；C4-债12 identity 测试时序加固（`anim2.state() == Running` 辅助断言）；**580/580 测试全绿，技术债区清零（C4-债1~12 全部消费完毕）**。**BD 批次**（2026-08-13，kickoff 标准档，基线 `4a235ca`，分支 kickoff/bd-bonus-door，merge `16026e6`）：桌面端第三模块「密码门」（来源 DESIGN_MOBILE v5 §5.2，先做桌面端移动端暂缓）——BD-01 kkrb 数据层（`BonusDoorItem` + `BONUS_DOOR_NAMES` 映射单源 + `parse_bonus_door_response` 纯函数 + `fetch_bonus_door_data()`，`az3r6` 单点剔除）；BD-02 密码门页面（`BonusDoorPage` 动态卡片网格，地图名 + 密码大字，不展示更新时间）；BD-03 装配（侧边栏第三导航 + 共享 client + 启动预加载 + closeEvent 回收）；BD-04 文档收尾；**614/614 测试全绿，覆盖率 94%**，期末四轴 0 阻断，非阻断 3 项入技术债区（BD-债1~3）。

---

## 二、数据模型

### 核心数据结构

```python
# data.json 格式（日期为 key）
{
  "2026-07-27": {
    "cash": 88541000.0,        # 当前现金 (float)
    "warehouse": 460900000.0   # 仓库价值 = 含现金的总收益 (float)
  },
  ...
}
```

**重要业务规则**：
- `cash` 是 `warehouse` 的组成部分（现金 ⊆ 仓库）
- **总收益 = warehouse**（不是 warehouse + cash）
- 数据最多保留最近 30 条实际录入记录（超出时删除最旧，按记录数而非日历天数）；视图 7/30 按钮组切换（切回 7 不丢数据）
- 日期格式 `YYYY-MM-DD`，硬编码在 `config.DATE_FORMAT`

### 关键计算

```python
# 较前日差值
delta = today.warehouse - prev_day.warehouse
# 显示为 ▲ +¥xx / ▼ ¥-xx / — ¥0.00（红涨绿跌）

# 收益率
rate = (today.warehouse - prev_day.warehouse) / prev_day.warehouse * 100
# 显示为 +2.4% / -1.3%（1位小数，红涨绿跌）

# 盈亏标签
盈 ← today.warehouse > prev_day.warehouse
亏 ← today.warehouse < prev_day.warehouse
— ← 无前日数据
```

---

## 三、关键决策

| 决策 | 内容 |
|------|------|
| **数据格式** | JSON 本地文件，无数据库依赖 |
| **持久化策略** | 原子写入（先 tmp 再 replace）+ 3 份滚动备份 + 兼容旧单文件备份 |
| **数据保留** | 最多保留最近 30 条实际录入记录，超出删除最旧；视图 7/30 可切换（产品决策，见 CONSENSUS §7 / ADR-0003） |
| **金额模型** | cash 和 warehouse 均为 float，warehouse 已含 cash |
| **输入解析** | 兼容 ¥/￥/$、千分位、K/M/B 后缀、负号、首尾空格 |
| **主题系统** | 两套完整色板（light/dark），约 30 个语义化 token，运行时 `get_color()` 解析 |
| **图表** | pyqtgraph 原生渲染，双图（仓库价值 + 现金），持久化 PlotCurveItem 增量更新（仅 setData 不重建） |
| **打包** | PyInstaller onedir（`dist/Delta Force Dashboard/`，exe + `_internal/`），`app_icon.ico` 设 exe 图标 + 运行窗口图标 |

---

## 四、常碰坑点

1. **主题切换**：运行时切换主题必须调用 `get_color(key)` 而非直接引用模块级常量——常量在 import 时固定为 light 主题。
2. **单实例保证**：`main.py` 通过 QLocalServer/QLocalSocket 防止多开；崩溃后残留 socket 会自动清理，无需手动删除。
3. **保留条数限制**：`ProfitCalculatorLogic.rotate_weekly()` 每次 `save_today()` 后执行，按「录入条数」超过保留上限 `RETENTION_LIMIT=30` 时从最旧开始删（满 30 不删、第 31 条才删）；表格/图表/汇总同以当前视图 7/30 条实际录入记录为基准（`recent_records`/`summary`，随按钮组切换），而非日历天。
4. **现金⊆仓库不变式**：判定收敛于 `ProfitCalculatorLogic.is_cash_under_warehouse()`（告警/拦截/红框三处共用）；总收益 = 仓库价值（已含现金），非 warehouse + cash。
5. **编辑模式**：编辑回填时使用 `unformat_input_value()` 转为纯数字，保存时用原日期覆盖写入。
6. **增量 vs 全量图更新**：`ChartWidget` 使用持久化的 `PlotCurveItem`（双序列），更新时仅 `setData()` 不重建组件（原生无填充区域，H-01 删填充）。

---

## 五、技术细节

详细的模块架构（文件布局、各模块职责与方法签名）、测试体系、运行与打包说明见 **[CODE_WIKI.md](CODE_WIKI.md)**——技术维基作为技术事实的唯一来源，本文件不再重复维护易漂移的技术细节。界面交互见 [README.md](README.md)，开发历史见 [DEV_LOG.md](DEV_LOG.md)，待办与归档见 [TO-TICKETS.md](TO-TICKETS.md)。

---

*本文档定位为项目介绍（背景 / 目标 / 关键决策 / 经验坑点）。技术细节统一以 CODE_WIKI.md 为准。*

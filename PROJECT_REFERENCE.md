# Delta Force Dashboard — 项目介绍书

> **一句话**：每日记录现金和仓库价值两项数据，自动保留最近 30 条记录并绘制收益曲线，计算盈亏（视图 7/30 可切换）。
> **技术栈**：Python PySide6 + pyqtgraph
> **打包**：PyInstaller onedir（`dist/Delta Force Dashboard/`，exe + `_internal/`）

---

## 一、项目概述

Delta Force Dashboard 是一款 Windows 桌面工具，主要面向个人投资者。

**核心场景**：用户每天记录「当前现金」和「仓库价值（含现金）」两个数字，工具自动保留最近 30 条实际录入记录（间断录入不丢历史），视图 7/30 可切换，以表格展示每日盈亏变化，并以双曲线图可视化趋势。

**当前状态**：功能完整，架构已优化。PySide6 迁移完成，三阶段 P0-P5 + Phase 4（T-01~T-05）+ C 系列（C1~C9）+ O 系列（O-01~O-22）+ D 系列（D-01~D-08）+ F 系列运维（F-01 文档同步 / F-02 迁移源清理标记）+ J 系列（J-01 保留上限 30 / J-02 视图 7/30 切换，ADR-0003）+ K 系列（K-01 保存保留两位小数 / K-02 现金总变化展示）全部完成（O-07 经评估 YAGNI 关闭）。477 项测试全部通过。**L 系列**（2026-08-04）：Delta Force 游戏工具扩展——侧边栏 + 制造利润排行（ADR-0004），L-04 卡战备推荐已移除。**X 系列**（2026-08-06）：子弹自选包兑换利润模块——kkrb_client 新增 `AmmoPackageItem`/`fetch_ammo_package_data()`（7 种包类型网格展示，X-02 扩展通行证基础/高级 + 进阶/特级物流 4 包）、制造板块更名利润（X-01）、代码气味消除（X-03）；ProfitPage 重构为制造产物 + 兑换利润纵向堆叠。**Y 系列**（2026-08-10）：多账号记账——`account_store.py` 账号存储层（ADR-0005：`accounts/<账号名>/data.json` 目录即账号名、无元数据文件）+ 旧数据复制迁移为「主账号」（`.migrated_v2` 幂等、永不删源）+ 启动解析 `current_account`（settings.json，兜底回主账号）+ 侧边栏账号区（下拉 + 新建账号，H5 新账号空库）+ 账号切换（整体重载 + 取消编辑/复用态 + 落盘，同账号 no-op，利润页零改动）+ code-review 修复（F1~F3 边界防护 / S2-S3 简化）；477/477 测试绿，覆盖率 92.75%。主要能力：单实例保证、CSV 导出、今日未录入提醒、图表稀疏提示、文件日志（含轮转）、现金≤仓库不变式校验、加载结构校验、编辑态关窗确认、视图 7/30 切换（存储保留 30 条，切回 7 不丢数据）、数据目录统一到用户目录、迁移后旧数据源清理提示（F-02）、JSON 原子写 seam + 设置持久化收敛、序列化边界收敛（`data`→`dict[str, DayRecord]` + `serialize()`，ADR-0001）、共享信号叶子 `signals.py`（D-01 收敛）、现金⊆仓库谓词收敛（D-05）、展示渲染纯函数化（D-07）、CODE_WIKI 机械标记文档同步 + pre-commit 防漂移钩子（F-01）。**架构加深批次**（2026-08-11）：主题契约（C1-06 `get_color` 未知键 warning 化返回 `""` / C1-07 TableWidget·CraftingPage `apply_theme` 钩子 / C1-08 树遍历契约——启动期收集 `_theme_refreshers`、`refresh_theme` 重写与数据刷新解耦 / C1-09 AST 全键守卫 + 全链路抽查）、Fetch 家族（C2-01 KkrbClient `threading.Lock` 并发加锁、握手恰一次 / C2-02 构造注入 seam + 利润页共享 client / C2-03 删 offscreen 哨兵改测试构造注入 / C2-04 渲染对齐删 `_EMPTY_STATION` 假领域对象 / C2-05 `_render_error` 错误/空态分离钩子）、Settings schema（C3-10 SettingsStore 成为 schema 所有者——`DEFAULTS`/`KNOWN_KEYS`/`update(patch)` 合并语义未知键保留 / C3-11 `animations` 纳入持久化闭环 + 窗口层 `_KEY_*` 常量收敛）；**527/527 测试全绿，覆盖率 94%**。**C4→C7 架构批次**（2026-08-12，kickoff 全自动档，基线 98b2ee1 → f76828b）：C4 仪表盘装配直构（`app/dashboard_page.py` `build_dashboard` + DashboardBundle 8 成员，替代 registry 间接层；main_window 1002→764 行）+ KPI 双磁贴渲染收敛（`app/kpi_presenter.py` 三出口 update/apply_theme_styles/reset，reset 终止在途动画防账号切换残留帧）；C5 calculator 展示边界收敛（收益率文案单源 `format_rate` + 删除孤儿 HTML 报告，calculator 579→412 行）；C6 删除 registry 插件系统（`app/registry.py` 物理删除 + AST 守卫 2 测试，全库零残留）；C7 存储 seam 容错收敛（`_try_load` 委托 `try_load_json` 读写对称 + InvalidToken 容错降级）；**561/561 测试全绿**。**技术债批次**（2026-08-12，kickoff 轻量档，基线 8bc4e68）：C4-债1 KPI 动画竞态修复——per-label 分槽 + 出槽动画优雅落终（`setCurrentTime` 终帧防残留帧覆盖直落终态），回归 5 用例、kpi_presenter 覆盖 100%；**566/566 测试全绿**（延续债项 C4-债2 per-tile 根治见 TO-TICKETS 技术债区）。

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
| **图表** | pyqtgraph 原生渲染，双图（仓库价值 + 现金），持久化 PlotCurveItem/FillBetweenItem 增量更新 |
| **打包** | PyInstaller onedir（`dist/Delta Force Dashboard/`，exe + `_internal/`），`app_icon.ico` 设 exe 图标 + 运行窗口图标 |

---

## 四、常碰坑点

1. **主题切换**：运行时切换主题必须调用 `get_color(key)` 而非直接引用模块级常量——常量在 import 时固定为 light 主题。
2. **单实例保证**：`main.py` 通过 QLocalServer/QLocalSocket 防止多开；崩溃后残留 socket 会自动清理，无需手动删除。
3. **保留条数限制**：`ProfitCalculatorLogic.rotate_weekly()` 每次 `save_today()` 后执行，按「录入条数」超过保留上限 `RETENTION_LIMIT=30` 时从最旧开始删（满 30 不删、第 31 条才删）；表格/图表/汇总同以当前视图 7/30 条实际录入记录为基准（`recent_records`/`summary`，随按钮组切换），而非日历天。
4. **现金⊆仓库不变式**：判定收敛于 `ProfitCalculatorLogic.is_cash_under_warehouse()`（告警/拦截/红框三处共用）；总收益 = 仓库价值（已含现金），非 warehouse + cash。
5. **编辑模式**：编辑回填时使用 `unformat_input_value()` 转为纯数字，保存时用原日期覆盖写入。
6. **增量 vs 全量图更新**：`_ChartPanel` 使用持久化的 `PlotCurveItem` + `FillBetweenItem`，更新时仅 `setData()` 不重建组件；填充边界曲线也持久化，避免重建开销。

---

## 五、技术细节

详细的模块架构（文件布局、各模块职责与方法签名）、测试体系、运行与打包说明见 **[CODE_WIKI.md](CODE_WIKI.md)**——技术维基作为技术事实的唯一来源，本文件不再重复维护易漂移的技术细节。界面交互见 [README.md](README.md)，开发历史见 [DEV_LOG.md](DEV_LOG.md)，待办与归档见 [TO-TICKETS.md](TO-TICKETS.md)。

---

*本文档定位为项目介绍（背景 / 目标 / 关键决策 / 经验坑点）。技术细节统一以 CODE_WIKI.md 为准。*

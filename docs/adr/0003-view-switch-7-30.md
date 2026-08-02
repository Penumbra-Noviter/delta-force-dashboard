# ADR-0003: 保留上限 7→30 + 视图 7/30 可切换（存储与视图解耦）

## 决策背景
用户需求「记录天数上限从 7 扩到 30」：现状 `rotate_weekly(days=7)` 只保留最近 7 条录入，
超出即删最旧。用户想积累更长的账目，但**不想牺牲 7 天视图的沉浸感**——一次看 30 条太密。
需求背后是两种口径：**存储保留上限**（最多留多少条账）与**视图展示窗口**（一次看几条）。
先经 Grilling Q1–Q11 收敛（记录在 `CONSENSUS.md` §7，原型 `MultiViewModel` 分支
`prototype/multiview` commit `f39c66f` 验证数据流不断裂），再落实现。本 ADR 记录方向性选择。

## 可选方案
1. **方案 A 纯后台扩容**：`rotate_weekly` 上限 7→30，视图仍固定 7。
   - 优势：改动最小（抬一个常量），数据流零重构。
   - 代价：用户攒到 30 条后，**老记录永远看不到**（视图还是 7），30 条库存成了死数据——
     O-C2 用户原意是「既能保留 30 条，又能切回 7 天视图」，此方案不满足需求。
2. **方案 B 存储/视图解耦（采纳）**：保留上限走独立常量 `RETENTION_LIMIT=30`，
   视图 7/30 由 `TableWidget` 按钮组切换，`MainWindow` 只按当前视图条数筛窗展示。
   - 优势：存储恒定 30、视图解耦，**切回 7 不丢数据**；`recent_records(days)`/`summary(days)`
     已按 `days` 参数化（现状），联动改动点收敛在 `MainWindow` 两处接入点 + 表格加控件；
     深模块（Q8）——表格是视图窗口主人，`MainWindow` 只订阅信号。
   - 代价：视图切换是会话内存态（不持久化，Q6/§7.5 明确），重开回到默认 7——按设计非缺陷。
3. **方案 C 日历天数口径**：按「最近 N 个日历天」而非「最近 N 条录入」展示/保留。
   - 优势：语义直观（"30 天"字面）。
   - 代价：间断录入（假期/出差）时日历天会被空档挤掉真实记录；与 O-17 已拍板的
     「录入条数」度量口径冲突，Q1 明确否掉，不做。

## 最终选择
✅ **方案 B（存储/视图解耦）** + Q11 保留边界「满 30 不删、第 31 条才删最旧」。

## 理由
- 用户意图（Q4）是「**加 7/30 视图切换**」，纯后台扩容（A）无感知、不满足；B 是唯一
  同时保留 30 条库存与 7 天视图沉浸感的形态，且 `MultiViewModel` 原型已验证数据流不断裂。
- 「录入条数」度量（Q1）延续 O-17，`recent_records`/`rotate_weekly`/`summary` 已全部
  按 `days` 参数化——真正改动点少：`rotate_weekly` 默认改引用 `RETENTION_LIMIT`，
  `MainWindow._get_records`/`_update_summary` 去掉硬编码 `WEEK_DAYS` 改走 `_view_n`。
- 控件选按钮组（Q6）、进 `TableWidget` 内部 + `view_changed(int)` 信号（Q8），
  切 30 时表格/曲线图/汇总**全联动**（Q9/Q10，同源自 `recent_records(_view_n)`），
  避免「表格 30/图表 7」断链——这是单一开关驱动三处同变的最简形态。
- 双栏均分 `mid=ceil(n/2)`（Q7）：7→4+3 现状不变，30→15+15，不引入单栏长滚动的布局回归。

## 影响
- 正面：存储保留上限 30 条（`config.RETENTION_LIMIT`），视图 7/30 会话内可切，
  切回 7 不丢数据（Q5）；「最近N条」文案联动——`format_summary(days)` 前缀随视图走、
  `format_saved_indicator(keep_days=RETENTION_LIMIT)` 清理提示「已保留最近 30 条」。
- 代价：视图切换不持久化（重启回到默认 7，§7.5 范围边界）；30 条视图下曲线图 X 轴变密集
  （`ChartWidget.draw` 随传入 records 长度自适应，不改图表结构）。
- 保留边界语义（Q11）：满 30 不删、第 31 条才删最旧，与现状 `rotate_weekly(days=7)` 行为一致
  （"最多 N 条账"），只抬 N。

## 原型与验证
- 原型：`MultiViewModel`（分支 `prototype/multiview`，commit `f39c66f`）——
  验证 RETENTION_LIMIT / view_days 解耦形态下数据流不断裂（切视图、保存、裁剪互不干扰）。
- 规格：Grilling Q1–Q11 收敛记录于 `CONSENSUS.md` §7；数据模型/UI 变更设计见 §7.3/§7.4。
- 测试：视图切换 UI 用例（默认 7 + 按钮组状态、切 30 信号/15+15/汇总联动、
  切回 7 不丢存储）+ `format_summary(days)`/`summary(days)` 参数化纯函数用例。

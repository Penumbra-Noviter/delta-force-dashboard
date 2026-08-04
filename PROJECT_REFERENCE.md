# 收益计算器 — 项目介绍书

> **一句话**：每日记录现金和仓库价值两项数据，自动保留最近 30 条记录并绘制收益曲线，计算盈亏（视图 7/30 可切换）。
> **技术栈**：Python PySide6 + pyqtgraph
> **打包**：PyInstaller onedir（`dist/收益计算器/`，exe + `_internal/`）

---

## 一、项目概述

收益计算器（Profit Calculator）是一款 Windows 桌面工具，主要面向个人投资者。

**核心场景**：用户每天记录「当前现金」和「仓库价值（含现金）」两个数字，工具自动保留最近 30 条实际录入记录（间断录入不丢历史），视图 7/30 可切换，以表格展示每日盈亏变化，并以双曲线图可视化趋势。

**当前状态**：功能完整，架构已优化。PySide6 迁移完成，三阶段 P0-P5 + Phase 4（T-01~T-05）+ C 系列（C1~C9）+ O 系列（O-01~O-22）+ D 系列（D-01~D-08）+ F 系列运维（F-01 文档同步 / F-02 迁移源清理标记）+ J 系列（J-01 保留上限 30 / J-02 视图 7/30 切换，ADR-0003）+ K 系列（K-01 保存保留两位小数 / K-02 现金总变化展示）全部完成（O-07 经评估 YAGNI 关闭）。253 项测试全部通过。主要能力：单实例保证、CSV 导出、今日未录入提醒、图表稀疏提示、文件日志（含轮转）、现金≤仓库不变式校验、加载结构校验、编辑态关窗确认、视图 7/30 切换（存储保留 30 条，切回 7 不丢数据）、数据目录统一到用户目录、迁移后旧数据源清理提示（F-02）、JSON 原子写 seam + 设置持久化收敛、序列化边界收敛（`data`→`dict[str, DayRecord]` + `serialize()`，ADR-0001）、共享信号叶子 `signals.py`（D-01 收敛）、现金⊆仓库谓词收敛（D-05）、展示渲染纯函数化（D-07）、CODE_WIKI 机械标记文档同步 + pre-commit 防漂移钩子（F-01）。

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
| **打包** | PyInstaller onedir（`dist/收益计算器/`，exe + `_internal/`），`app_icon.ico` 设 exe 图标 + 运行窗口图标 |

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

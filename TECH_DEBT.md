# TECH_DEBT: Delta Force Dashboard

> **技术债候选池**（未立项子集）与**处置记录**。本文件与 `TO-TICKETS.md`（任务池）分离——候选不等于任务，不自动进入任何 session 的 preflight 认领；消费 = 显式「立项」（从候选区取出 → 转入 `TO-TICKETS.md` 活跃工单并声明归属方向，或标记 ❌ 不立项附理由）。
> 读取契约与强度消费规则见 project-kickoff 步骤 0 预检（`AGENTS.md` §3 任务清单生命周期）。
>
> 本文件自 2026-08-24 起从 `TO-TICKETS.md` 技术债区独立化（对齐 AGENTS.md §3 规范）；
> 迁移时技术债区净清零。历史技术债消费批次（IC-债1/2、BD-债1~3、C4-债1~12 系列）的
> 处置明细见 `TO-TICKETS.md`「已完成归档」，本文件不重复搬运。

---

## 规范说明

### 条目格式

候选区每行对应一条技术债，含 6 个字段：

| 字段 | 含义 |
|------|------|
| **编号** | 项目前缀递增唯一（如 `DFD-N`） |
| **遗留项** | 什么问题、在哪个文件、当前影响 |
| **来源** | 产生此条目的审核/讨论/评审（如「波 1 Falsify」「期末四轴 Architecture」） |
| **强度** | `Strong` / `Worth exploring` / `Speculative`（见下方消费规则） |
| **状态** | `📝 待立项` / `🔄 进行中` / `✅ 已修` / `❌ 复核关闭` |
| **归属方向** | 此条目的业务方向（如 `数据管道` / `GUI`），session 只认领匹配方向的条目 |

### 强度消费规则

| 强度 | 消费规则 |
|------|----------|
| **Strong** | 必入工单清单（下一轮 kickoff 的 plan-tickets 必须包含） |
| **Worth exploring** | 入候选由 Grilling 拍板（做/关闭），无默认方向 |
| **Speculative** | 可关闭，关闭须「`git grep` 复核现状仍成立」一句话理由 |

### 清出机制（防膨胀）

1. 候选区只留开放条目（📝 待立项 / 🔄 进行中）；条目处置后整行移出候选区，处置详情写入「技术债处置记录」
2. ❌ 关闭条目压缩：具复核价值的关闭项（防 review 重复提出的 Speculative 类）保留单行摘要于「复核关闭」表，其余直接删除
3. 处置记录按日期分节，滚动保留最近 **2 节**（同日多批次合并计为一节）；更早归档由 git 历史承担（`git log -p -- TECH_DEBT.md`）
4. 清出动作绑定既有维护节点：每会话结束、commit 之前同步执行，不新增仪式

### 多 session 防污染

1. **任务所有权分离**：`TO-TICKETS.md` 是唯一任务池（preflight 只读它）；本文件是候选池（只写不认领）
2. **条目归属标注**：每条目必填「来源」与「归属方向」，session 只认领自己方向匹配的条目
3. **消费显式化**：从候选区转工单必须带一句话理由（强度 + 方向匹配），禁止静默批量认领
4. **写冲突隔离**：候选人落盘写本文件（评审 session 独占），任务状态变更写 `TO-TICKETS.md`（认领 session 独占），不同 session 写不同文件，不互踩

---

## 技术债候选区

| 编号 | 遗留项 | 来源 | 强度 | 状态 | 归属方向 |
|------|--------|------|------|------|----------|
| DFD-1 | `_kpi_signal` 是 `format_window_text(...)[1]` 的 1 行转发，却躺在最大的枢纽模块里，并制造 main_window ↔ kpi_presenter 循环依赖（kpi_presenter 用调用期延迟导入绕环）；删除测试通过（纯浅透传） | 架构评审 C2 | Strong | 📝 待立项 | GUI |
| DFD-2 | `fetch_page_base._data` 三处赋值零读取（删除测试通过）；基类 `_render_error` 默认 = `_render_data([])` 使空/错态不可分，三子类各写一遍占位清空逻辑（exchange 未写，错误态与空态共用） | 架构评审 C3 | Strong | 📝 待立项 | 数据页/GUI |
| DFD-3 | `kpi_presenter` 用展示文案字面量 `value != "数据不足"` 决定动画分支（presentation 改文案即静默改变行为）；「暂无数据」×7、「加载中…」×2 写法散落 5 模块 | 架构评审 C4 | Strong | 📝 待立项 | GUI |
| DFD-4 | `build_dashboard(mw)` 经副作用写回 `mw._dashboard_page`，MainWindow 随后私读 dashboard 私有属性（`_title_label` 等）；测试需伪造「长得像 MainWindow」的整对象 | 架构评审 C5 | Strong | 📝 待立项 | GUI |
| DFD-5 | 视图窗口同一事实两份（`TableWidget._view_days` 与 `MainWindow._view_n`），仅靠 `view_changed` 信号维持相等；非按钮路径的程序化改动会漂移（测试双断言钉住） | 架构评审 C6 | Worth exploring | 📝 待立项 | GUI |
| DFD-6 | 主题刷新是约定制：`hasattr` 树遍历收集 + 六组件各自私藏「换色记忆」；同一 `apply_theme` 下 TableWidget 实为整表重绘、ChartWidget 才是真增量（隐藏代价差异） | 架构评审 C7 | Worth exploring | 📝 待立项 | GUI |

### 复核关闭（Speculative 类，防重复提议）

| 编号 | 遗留项（压缩摘要） | 来源 | 强度 | 状态 |
|------|--------|------|------|------|

## 技术债处置记录

### 2026-09-08（架构评审批次）

| 编号 | 遗留项 | 处置 | 提交 |
|------|--------|------|------|
| C1 | 动画生命周期知识复制 4 处（`motion.fade_in_widget` / `_shake` / `_countup_anims` / `_draw_anim`），C4-债 同族 bug 反复修 ≥5 次 | ✅ 已修（立项 → TO-TICKETS C1 → 在途注册表深化 + 落点迁移） | 本提交 |

---

## 处置记录说明

- 候选区只保留开放条目（📝 待立项 / 🔄 进行中），处置后条目移入「技术债处置记录」按日期分节。
- ❌ 复核关闭的 Speculative 类条目在候选区「复核关闭」表中保留单行压缩摘要防重复提议。
- 处置记录滚动保留最近 2 节；更早的归档由 git 历史承担（`git log -p -- TECH_DEBT.md`）。
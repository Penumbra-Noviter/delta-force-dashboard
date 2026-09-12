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

### 复核关闭（Speculative 类，防重复提议）

| 编号 | 遗留项（压缩摘要） | 来源 | 强度 | 状态 |
|------|--------|------|------|------|
| DFD-9 | `_select_theme` 未校验 name（未知名时 `_theme` 已更新但 `_current_theme` 未变，一次性不一致） | 期末四轴 Falsify F3 | Speculative | ❌ 复核关闭 2026-09-13 |
| DFD-10 | `resolve_palette` 只查 CUSTOM 形状不查 overrides hex（依赖 register_custom 隐式契约） | 期末四轴 Architecture A2 | Speculative | ❌ 复核关闭 2026-09-13 |
| DFD-11 | `resolve_palette`/`register_custom` 未运行时校验非 str（签名已 str、生产调用链不可触发） | 期末四轴 Falsify F1/F2 | Speculative | ❌ 复核关闭 2026-09-13 |

## 技术债处置记录

### 2026-09-13（Speculative 复核关闭）

| 编号 | 遗留项 | 处置 | 提交 |
|------|--------|------|------|
| DFD-9 | `_select_theme` 未校验 `name`（未知名时 `_theme` 已更新但 `_current_theme` 未变） | ❌ 复核关闭（`git grep` 现状成立：`main_window.py:544` 无条件写 `self._theme`，`theme.py:395` 才有 `name in THEMES or name in CUSTOM` 守卫；信号源只发预设名、不可触发，表面加固不做） | 本提交 |
| DFD-10 | `resolve_palette` 只查 `CUSTOM` 形状不查 overrides 值 hex | ❌ 复核关闭（`git grep` 现状成立：`theme.py:306` 仅 `isinstance(overrides, dict)` 不校验 hex；只能经 `register_custom`（含 `clean_overrides`）写，生产调用链固定，表面加固不做） | 本提交 |
| DFD-11 | `resolve_palette`/`register_custom` 未运行时校验非 str 输入 | ❌ 复核关闭（`git grep` 现状成立：`theme.py:300/318` 直接 `name in THEMES`、`:324` 直接 `CUSTOM[name]`，无 `isinstance(str)` 守卫；签名已 str、生产调用链不可触发，表面加固不做） | 本提交 |

### 2026-09-09（多主题批次技术债消费）

| 编号 | 遗留项 | 处置 | 提交 |
|------|--------|------|------|
| DFD-8 | 预设主题名单三处散落（`THEMES` keys / `Sidebar.THEME_NAMES`+`THEME_LABELS` / `theme_dialog._PRESET_NAMES`），未来新增预设需三处同步 | ✅ 已修（立项 → TO-TICKETS DFD-8 → 收敛为 `theme.PRESET_NAMES`/`PRESET_LABELS` 单源 + set 守卫） | `8fb2cda` |

---

## 处置记录说明

- 候选区只保留开放条目（📝 待立项 / 🔄 进行中），处置后条目移入「技术债处置记录」按日期分节。
- ❌ 复核关闭的 Speculative 类条目在候选区「复核关闭」表中保留单行压缩摘要防重复提议。
- 处置记录滚动保留最近 2 节；更早的归档由 git 历史承担（`git log -p -- TECH_DEBT.md`）。
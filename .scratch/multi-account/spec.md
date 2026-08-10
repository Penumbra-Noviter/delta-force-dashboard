# 多账号（multi-account）— Spec

> 来源：Grilling 共识结论 R1-R9（用户逐条确认）+ 源码探索核实。
> 工单编号：Y 系列（Y-01 ~ Y-05）。本文档不包含文件路径与代码片段（快速过时），实现细节以工单为准。

## Problem Statement

当前记账模块是单账号的：所有记账数据固定落在统一数据目录的 data.json，用户无法在同一台机器上为不同用途（不同游戏角色 / 区服 / 子账本）分别记账。切换账本只能靠手动备份文件，容易混淆与丢失。同时，本功能升级后必须保证既有用户数据平滑迁入默认账号「主账号」，数据绝不丢失、绝不自动删除。

## Solution（用户视角）

- 侧边栏顶部新增「账号」区：当前账号下拉框 +「新建账号」按钮。
- 新建账号：弹命名对话框，校验通过后在账号列表中出现新账号；当前账号不跳变（留在当前，需手动切换）。
- 切换账号：下拉选择后记账页整体重载（输入区、表格、曲线图、汇总磁贴、今日状态），标题栏显示当前账号名；利润页不受任何影响。
- 重启后回到上次使用的账号。
- 首次升级运行：旧 data.json（含全部滚动备份）自动复制到「主账号」下，旧文件保留不删；之后不再重复迁移。

## User Stories

1. As a user, I want to create a new account with an empty ledger, so that I can keep separate bookkeeping for different purposes without mixing data.
2. As a user, I want the first account to be named 主账号 and to hold my existing data, so that upgrading keeps my experience unchanged and loses nothing.
3. As a user, I want to switch accounts while the app is running, so that I can alternate between ledgers without restarting.
4. As a user, I want the ledger page to fully reload after switching, so that I never see another account's data mixed into my view.
5. As a user, I want the app to remember my last account across restarts, so that reopening returns to where I left off.
6. As a user, I want invalid account names (empty / duplicate / forbidden characters / leading-trailing space or dot) to be rejected with clear feedback, so that the filesystem stays safe.
7. As a user, I want new accounts to start empty, so that I don't inherit data by accident.
8. As a user, I want the current account name shown in the ledger title bar, so that I can always tell which ledger I'm looking at.
9. As a user, I want CSV export to act on the current account, so that exported data always matches what I see.
10. As a user, I want the profit page to keep working unchanged regardless of account switching, so that switching never disturbs my profit lookups.
11. As a user, I want creating an account not to switch me away from my current account, so that I can set up several accounts without losing my place.

## Implementation Decisions

- **存储布局**：`accounts/<账号名>/data.json`，每账号自带滚动备份；复用 DataStore 路径注入（data_file/backup_file），原子写 / 损坏恢复 / 3 份备份全部继承。账号目录名即账号名，目录扫描发现账号；不引入 accounts.json 元数据文件。
- **新业务模块 account_store**：`list_accounts()` / `create_account(name)` / `resolve_account(current)` / `migrate_legacy_to_default()`；UI 层不直接接触文件系统。账号名校验：非空、不重名、不含 `\ / : * ? " < > |`、首尾不得为空格或点（目录名即账号名，必须 sanitize）。
- **默认账号「主账号」**；settings.json 新增 `current_account` 字段，重启恢复上次账号；字段缺失 / 非字符串 / 指向不存在目录 → 回退「主账号」；`accounts/` 为空 → 自动创建「主账号」空数据。
- **首次运行迁移（v2）**：`accounts/` 不存在且旧 data.json 存在 → 复制 data.json 与全部 `.bak` 系列到 `accounts/主账号/`，写 `accounts/.migrated_v2` 完成标记；标记存在即跳过（幂等）；复制非移动、永不自动删源（O-22 铁律）。`accounts/` 已存在 → 一律不迁移、不覆盖任何已有账号目录。
- **主窗口持有当前账号**：切换时用目标账号路径构造新 DataStore 并重新加载逻辑，随后整页刷新（表格 / 曲线 / 汇总 / 今日状态 / 标题栏账号名）；保存 / 删除已即时落盘到 self.store，换 store 即换落盘目标；切换时取消未保存的编辑 / 复用状态，防止跨账号污染。
- **UI**：侧边栏顶部账号区 = 当前账号下拉框 +「新建账号」按钮（命名对话框）；记账页标题栏显示当前账号名。
- **利润模块零改动**：ProfitPage 纯 kkrb.net API 查询，无本地持久化，切换账号不触碰；主题 / 置顶 / 动画 / geometry 等全局设置与账号无关，保持全局共享。

## Testing Decisions

- **好测试的定义**：只测外部行为——业务层测「文件系统上的真实效果」（tmp_path 显式注入），UI 层测「公开信号 / 公开方法触发的可观察状态」（复用 conftest 的 qapp / settings_guard fixtures 与既有 MainWindow 注入模式，绝不触碰真实用户目录）。
- **要测的模块**：
  - account_store：列出 / 新建 / 重名拒绝 / 非法名拒绝 / 兜底回退 / 空目录自动建主账号；
  - 迁移：幂等 / marker 跳过 / 复制非移动 / 不删源 / 全新环境首次运行无迁移；
  - UI 集成：切换后表格 / 曲线 / 汇总刷新、current_account 落盘回读、新建出现在列表且不切换、标题更新、编辑态取消、利润页不受影响。
- **结构防复发**：AST 静态断言「UI 层不得直接拼装账号路径」（沿用 test_migration 的 AST 先例）。
- **覆盖率**：维持 ≥ 90%。
- **参考先例**：DataStore 注入测试、迁移 + AST 防复发测试、MainWindow 注入 + settings_guard 的 UI 烟测组织方式。

## Out of Scope

- 利润模块任何改动（切换账号不影响利润页，零改动）。
- 账号重命名、账号删除（不存在「删到零账号」高危路径）。
- CSV 导入 UI 接线（import_csv 纯函数继续存在但不接线）；导出保持现状并自动作用于当前账号。
- 单实例、主题 / 置顶 / 动画 / geometry 全局设置语义不变。
- accounts.json 元数据文件；按账号隔离的个性化设置（theme 等保持全局）。
- Windows 保留设备名（CON/NUL 等）不在账号名校验范围内（已知边界，不做扩展）。

## Further Notes

- 建议补 ADR-0005「多账号存储布局」记录本决策（docs/adr 惯例），并入 Y-01 交付。
- 工单编号：Y 系列（Y-01 ~ Y-05），延续 U/V/W 系列惯例。
- 账号区如需新 emoji，走 app/ui_text.py 的 EMOJI 单一来源扩展（U-05 约定）。
- 本 spec 与工单落盘 `.scratch/multi-account/`；TO-TICKETS.md 由主会话决定是否同步录入。

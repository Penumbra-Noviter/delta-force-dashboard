# Y-02：旧数据迁移到 accounts/主账号（v2 迁移）

- **Blocked by**: Y-01（账号存储层）
- **Status**: ready-for-agent

## What to build

用户视角：升级后第一次启动，旧的 data.json（含全部滚动备份）自动出现在「主账号」下，数据无感迁移；之后重启不再重复迁移，旧文件原样保留。

端到端验证：构造旧布局（统一数据目录下 data.json + `.bak` 系列）→ 运行迁移 → `accounts/主账号/` 出现完整数据 + `accounts/.migrated_v2` 标记，源文件保留不动；二次运行幂等跳过。

## 文件范围

- 修改 `account_store.py`（新增 `migrate_legacy_to_default()`，复用 Y-01 布局常量与 DataStore）
- 修改 `main.py`（启动接线：v2 迁移必须在 O-22 旧目录迁移之后、MainWindow 构造之前）
- 修改 `tests/test_account_store.py`（迁移用例组）

## 高不确定实现点

无 major。唯一易错点：与既有 O-22 迁移（旧目录 → 统一数据目录）的先后顺序——O-22 先执行（填充统一目录 data.json），v2 再迁入 `accounts/主账号/`；顺序由验收标准固化并有测试守卫。

## 验收标准

- [ ] 迁移触发条件严格遵循决策 2：`accounts/` 不存在 **且** 统一数据目录 data.json 存在 → 复制 data.json + 全部 `data.json.bak*` 到 `accounts/主账号/`，写 `accounts/.migrated_v2`
- [ ] `accounts/` 已存在 → 一律不迁移、不覆盖任何已有账号目录（含 `accounts/` 存在但为空的场景）
- [ ] marker 存在 → 跳过（幂等，二次运行不重复复制、数据不被覆盖）
- [ ] 复制非移动：源文件保留；任何路径下绝不自动删除源文件（O-22 铁律）
- [ ] 全新环境（无 accounts、无旧 data.json）→ 无迁移、无 marker
- [ ] 迁移失败（OSError）→ warning 日志、不中断启动
- [ ] 启动接线：main.py 中 v2 迁移调用顺序正确（O-22 迁移之后、窗口构造之前），有顺序测试或 AST 断言
- [ ] 独立用例覆盖：迁移幂等 / marker 跳过 / 复制非移动 / 不删源 / 全新环境首次运行 / 失败不中断
- [ ] 覆盖率维持 ≥ 90%

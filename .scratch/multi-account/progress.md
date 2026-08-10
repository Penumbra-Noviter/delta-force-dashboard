# Y 系列实施进度（Implement 波 1 串行链）

> 工作树版 progress.md 已随工作树删除；本文件于 main 仓库重建，补记评审修复节。

## Y-01 ~ Y-05 串行链（工作树 kickoff-y-multi-account，已合并 main）

- Y-01 账号存储层 `c816de2` → Y-02 旧数据迁移 `9296c40` → Y-03 启动解析 `0da9b09`
  → Y-04 侧边栏账号区 `c1b5525` → Y-05 账号切换 `37b8fb4`（merge `900f50a`）。
- 一轮评审修复（F1/F2/F3/S2/S3）`09fa722`（merge `39d9595`）。

## 二轮评审修复（main `0eb9bbf`）

- **F-P1** 非法目录账号失联（P1）：`list_accounts` 过滤目录名非法的条目
  （如手工创建的点开头目录）——与 resolve_account/create_account 校验语义一致，
  消除「选中非法目录 → 写入 → 重启静默失联」整条路径（spec H2「目录名=账号名」
  的目录发现语义保留，仅加 sanitize 边界）；`_on_account_selected` 补
  validate_account_name 防御（绕过过滤直接触发 → 可读提示 + 零写入 + 不重载）。
- **casefold 重名**（P2）：`create_account` 重名检测加 casefold 变体（Windows
  大小写不敏感）——已有 "Abc" 时新建 "abc" 此前 mkdir no-op 静默假成功，现
  明确拒绝并指出重名对象。
- **SP2** 迁移半成品（P2）：`migrate_legacy_to_default` 失败分支新增
  `_cleanup_failed_migration`——删除本次创建的 accounts/主账号/ 副本并恢复
  「accounts/ 不存在」触发条件（绝不碰源文件，O-22 铁律），下次启动可重试；
  旧行为：半成品残留导致备份历史永不迁移。
- **AST 防复发改造**（P2）：`test_ui_layers_do_not_build_account_paths` 由裸文本
  检查改为真 AST（ast.parse + ast.walk 提取字符串字面量与 f-string 分段，
  跳过 docstring 以允许文档引用 list_accounts/set_accounts 方法名）；
  新增绕过演示用例（单引号/f-string/拼接变体必须被抓到）。
- 不改动项备忘：SP1（accounts 为文件病理态，P2 备忘）、S1/S2/S3（判断项）、
  CON/NUL 保留设备名（spec 已知豁免）。
- 测试：+6（非法目录过滤 / casefold 拒绝 / 迁移半成品清理 + 重试成功 /
  切换非法名拒绝 / 启动下拉排除非法目录 / AST 变体捕获演示）。
  全量 483/483 绿；覆盖率 92.82%（account_store 96% / main_window 92% /
  sidebar 99%）；doc_sync OK。

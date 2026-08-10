# Y-01：账号存储层（account_store 业务模块）

- **Blocked by**: None — can start immediately
- **Status**: ready-for-agent

## What to build

账号能力的业务地基（用户视角暂无 UI，纯后端能力）：任何账号操作（列出 / 新建 / 解析 / 兜底）都有可测试的业务实现，后续所有账号功能（新建 / 切换 / 迁移 / 恢复）都调用本层，UI 不碰文件系统。

端到端验证：pytest 直接驱动文件系统效果（tmp_path 注入），无 Qt 依赖。

## 文件范围

- 新建 `account_store.py`（业务层，含账号名校验、路径布局常量、DataStore 路径注入）
- 新建 `tests/test_account_store.py`
- 新建 `docs/adr/0005-multi-account-storage.md`（记录存储布局决策，docs/adr 惯例）

## 高不确定实现点

无（复用既有 DataStore / json_file 原子写 seam）。已知边界：Windows 保留设备名（CON/NUL 等）不在 H1 校验范围内，不做扩展，记录于 spec Out of Scope。

## 验收标准

- [ ] `list_accounts()` 扫描 accounts 目录返回账号名列表（目录名 = 账号名）；空目录返回 `[]`；目录缺失返回 `[]`
- [ ] `create_account(name)` 创建账号目录（新账号从空数据开始，H5）
- [ ] 账号名校验：拒绝空名 / 重名 / 含 `\ / : * ? " < > |` 的名字 / 首尾空格或点的名字；拒绝时不产生任何目录，返回可读拒绝原因
- [ ] `resolve_account(current)` 兜底：current 缺失 / 非字符串 / 指向不存在目录 → 回退「主账号」；accounts/ 为空 → 自动创建「主账号」目录（空数据）
- [ ] 每账号以 `DataStore(data_file, backup_file)` 路径注入构造，原子写 / 损坏恢复 / 滚动备份全部继承（有针对性测试）
- [ ] 全部测试 tmp_path 显式注入，零真实用户目录触碰（「全新环境首次运行」独立用例）
- [ ] 模块 type hints + docstring + `__all__`；无 `except: pass`
- [ ] ADR-0005 落地（存储布局 / 目录即账号名 / 无元数据文件 / v2 marker 约定）
- [ ] 覆盖率维持 ≥ 90%

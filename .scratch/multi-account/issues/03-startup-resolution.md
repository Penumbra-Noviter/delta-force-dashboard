# Y-03：启动解析当前账号（current_account 持久化 + 兜底恢复）

- **Blocked by**: Y-01（账号存储层）、Y-02（v2 迁移——先迁移后解析，保证老用户首启落在主账号）
- **Status**: ready-for-agent

## What to build

用户视角：启动后自动回到上次使用的账号；设置里没有记录或记录失效时回到「主账号」；记账页数据来自该账号；标题栏显示当前账号名。

端到端验证：注入带 `current_account` 的 settings → 启动 MainWindow → 内部 store 指向对应账号路径、标题显示账号名；关窗后 settings.json 回写 `current_account`；缺字段 / 失效字段回退主账号。

## 文件范围

- 修改 `app/main_window.py`（启动解析、持有当前账号、标题更新、`_save_settings` 合并 current_account）
- 修改 `settings_store.py`（如需：编码辅助扩展，保持容错读写语义不变）
- 修改 `tests/test_ui_smoke.py`（启动解析 + 落盘回读 + 兜底回退集成用例）
- 修改 `tests/test_account_store.py`（resolve 兜底补用例，如 Y-01 未覆盖）

## 高不确定实现点

**【需设计确认】MainWindow 的账号解析注入 seam**：如何在新增账号解析的同时保持既有 ~15 个 `MainWindow(store=..., logic=...)` 注入测试零改动、零真实用户目录触碰。建议方向：仅当未注入 store 时才走账号解析（生产默认路径），注入 store 时跳过解析保持现状；切换 / 账号相关测试显式注入 account_store。实现前建议以最小 spike 或评审定案，避免破坏现有测试注入模式。

## 验收标准

- [ ] settings.json 新增 `current_account`；`_save_settings` 持久化当前账号，与 encode_settings 输出合并（geometry / pinned / theme 不丢）
- [ ] 启动解析：current_account 缺失 / 非字符串 / 指向不存在目录 → 回退「主账号」
- [ ] accounts/ 为空 → 自动创建「主账号」空数据（走 resolve_account 兜底）
- [ ] 生产路径（未注入 store）下 MainWindow 从解析出的账号路径构造 DataStore / logic
- [ ] 既有注入模式不破坏：现有 MainWindow 注入用例行为不变、不触碰真实用户目录（全量 pytest 绿）
- [ ] 记账页标题栏显示当前账号名
- [ ] AST 防复发：UI 层（main_window / sidebar）不得直接拼装账号路径字符串，必须走业务层
- [ ] 新增集成用例：启动解析 / 关窗落盘回读 / 兜底回退；覆盖率维持 ≥ 90%

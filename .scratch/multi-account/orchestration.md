# Orchestration — Y 系列（多账号 / 账号切换）

> 编排状态落盘文件。主会话只持有本路径 + 当前状态指针；元数据全文在此，abort 现状清单由此生成。

## 档位与基线

- 档位：标准档（5 工单，无并行组 → 单 Implement 串行链）
- 基线 commit：`e5a62c21b8c505d0ef3e1b88d5fa28ac2b76adb6`（main，2026-08-10）
- 分支：`kickoff/Y-multi-account`（单分支，每工单一个 commit）
- 分发：1 × Implement 子智能体（串行链连续完成 Y-01→Y-05）

## 工单元数据表

| 编号 | 标题 | Blocked by | 文件范围 |
|------|------|-----------|---------|
| Y-01 | 账号存储层（account_store 业务模块） | — | `account_store.py`、`tests/test_account_store.py`、`docs/adr/0005-multi-account-storage.md` |
| Y-02 | 旧数据迁移到 accounts/主账号（v2 迁移） | Y-01 | `account_store.py`、`main.py`、`tests/test_account_store.py` |
| Y-03 | 启动解析当前账号（current_account 持久化 + 兜底） | Y-01, Y-02 | `app/main_window.py`、`settings_store.py`（如需）、`tests/test_ui_smoke.py`、`tests/test_account_store.py` |
| Y-04 | 侧边栏账号区（下拉框 + 新建 + 命名对话框） | Y-03 | `app/sidebar.py`、`app/main_window.py`、`app/ui_text.py`（如需）、`tests/test_ui_smoke.py` |
| Y-05 | 账号切换（运行中切换 + 整体重载 + 落盘） | Y-04 | `app/main_window.py`、`app/sidebar.py`、`tests/test_ui_smoke.py` |

## 波次计划

- 波 1（唯一波）：Y-01→Y-05 串行链，单 Implement 连续完成；每工单完成 → commit + progress.md 阶段摘要
- merge 点：全部完成后合并回 main（`--no-ff`）
- 期末：全量测试 → code-review 三轴（固定点 = 基线 `e5a62c2`）

## spike 处置（评审定案，无原型）

- Y-03 注入 seam：定案「仅未注入 store 时解析账号」，既有注入测试零改动
- Y-04 侧边栏 130px：允许适度扩宽（同步更新 `width()==130` 断言）

## 遥测

| 波 | 时长 | 并行数 | 回退/冲突 | 增量审核 findings |
|----|------|--------|-----------|-------------------|
| 1  | —    | 1（串行） | — | 期末统一三轴 |

## 现状指针

- 当前阶段：Implement 波 1 执行中（Y-01 起始）
- 待办：波末 merge → 全量测试 → code-review → Neat

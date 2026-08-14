# CLAUDE.md — Delta Force Dashboard

## 项目一句话

Windows 桌面收益追踪工具（PySide6）：每日记录现金/仓库价值，最近 7/30 条视图 + 双曲线图；侧边栏三模块——记账仪表盘、利润（kkrb.net 制造产物 + 兑换利润）、密码门（每日地图密码，BD 批次）。

## 怎么跑

```bash
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt -r requirements-dev.txt
python main.py                                # 运行（运行态数据落在 ~/Delta Force Dashboard/）
pytest                                        # 全量测试（631 项，Qt 用例自动 offscreen）
python scripts/doc_sync.py --check            # CODE_WIKI 机械标记防漂移（pre-commit 钩子自动跑）
python scripts/doc_sync.py                    # 改代码后刷新 CODE_WIKI 的测试数/行数/签名标记
```

## 技术栈

Python 3.10+ / PySide6 / pyqtgraph / pytest；PyInstaller onedir 打包（`dist/Delta Force Dashboard/`）；kkrb.net 客户端纯 stdlib 零外部依赖。

## 目录与约定

- **层**：`app/` UI 层（页面 + 主题 + 动效 + 装配）；`kkrb_client.py`+`kkrb_models.py`+`kkrb_parsing.py` 数据层；`calculator.py`/`presentation.py` 业务与展示纯函数；`json_file.py`/`data_store.py`/`settings_store.py`/`account_store.py` 持久化
- **文档事实分层**：CODE_WIKI.md = 技术唯一来源（doc_sync 机械标记）；README = 界面/使用；TO-TICKETS.md = 待办唯一来源（完成 → 移归档 → 同步 DEV_LOG → 一起 commit）；DEV_LOG = 已做记录（倒序）；CONSENSUS = 共识；CONTEXT = 领域词汇
- **契约红线**（详见 CODE_WIKI §10 与 status 记忆）：绝不在模块顶层调 `get_color()`；测试构造注入 stub client 即断网（`tests/conftest.make_stub_client`）；kkrb 解析纯函数畸形输入不抛；`az3r6` 排除策略单点（client 层剔除，两端硬排除）；`BONUS_DOOR_NAMES` 定义顺序即解析输出顺序；新增测试文件或 §4 模块标题需在 CODE_WIKI 补对应标记（否则 doc_sync --check 拦截提交）
- **入库边界**：运行态 data.json/settings.json、`.scratch/`、`.worktrees/`、`.pytest_cache/`、`build/`、`dist/` 均已 gitignore

## 当前状态与下一步（2026-08-15）

- F-01 增强（doc_sync files 文件级引用校验，`122dea9`）+ CODE_WIKI 补 motion/load_state/fetch_worker 小节（`2274f9b`）+ 浅色主题柔和化（`78ca2e1`，暖白卡面 + 主/语义色降饱和）已完成：**631/631 测试**、doc_sync 双绿
- main 与 origin/main 已同步（最近三提交已推送）
- 清场已完成：`.worktrees/` 与 `.scratch/` 均已清空，分支仅保留 main
- 下一步：无遗留待办（技术债区净清零，见 TO-TICKETS）

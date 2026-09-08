# CLAUDE.md — Delta Force Dashboard

## 项目一句话

Windows 桌面收益追踪工具（PySide6）：每日记录现金/仓库价值，最近 7/30 条视图 + 双曲线图；侧边栏三模块——记账仪表盘、利润（kkrb.net 制造产物 + 兑换利润）、密码门（每日地图密码，BD 批次）。

## 怎么跑

```bash
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt -r requirements-dev.txt
python main.py                                # 运行（运行态数据落在 ~/Delta Force Dashboard/）
pytest                                        # 全量测试（642 项，Qt 用例自动 offscreen；沙箱内加 --basetemp=.pytest_cache\tmp）
python scripts/doc_sync.py --check            # CODE_WIKI 机械标记防漂移（pre-commit 钩子自动跑）
python scripts/doc_sync.py                    # 改代码后刷新 CODE_WIKI 的测试数/行数/签名标记
```

## 技术栈

Python 3.10+ / PySide6 / pyqtgraph / pytest；PyInstaller onedir 打包（`dist/Delta Force Dashboard/`）；kkrb.net 客户端纯 stdlib 零外部依赖。

## 目录与约定

- **层**：`app/` UI 层（页面 + 主题 + 动效 + 装配）；`kkrb_client.py`+`kkrb_models.py`+`kkrb_parsing.py` 数据层；`calculator.py`/`presentation.py` 业务与展示纯函数；`json_file.py`/`data_store.py`/`settings_store.py`/`account_store.py` 持久化
- **文档事实分层**：CODE_WIKI.md = 技术唯一来源（doc_sync 机械标记）；README = 界面/使用；TO-TICKETS.md = 待办唯一来源（完成 → 移归档 → 同步 DEV_LOG → 一起 commit）；DEV_LOG = 已做记录（倒序）；CONTEXT = 领域词汇；`docs/archive/CONSENSUS.md` = 历史共识（已归档）
- **契约红线**（详见 CODE_WIKI §10 与 status 记忆）：绝不在模块顶层调 `get_color()`；测试构造注入 stub client 即断网（`tests/conftest.make_stub_client`）；kkrb 解析纯函数畸形输入不抛；`az3r6` 排除策略单点（client 层剔除，两端硬排除）；`BONUS_DOOR_NAMES` 定义顺序即解析输出顺序；新增测试文件或 §4 模块标题需在 CODE_WIKI 补对应标记（否则 doc_sync --check 拦截提交）
- **入库边界**：运行态 data.json/settings.json、`.scratch/`、`.worktrees/`、`.pytest_cache/`、`build/`、`dist/` 均已 gitignore

## 当前状态与下一步（2026-09-08）

- 架构评审按强度顺序推进（`improve-codebase-architecture` 全库审查 7 项候选）：
  - **C1 ✅**：动画句柄生命周期回归 `app/motion.py`——在途注册表（target 弱键）+ `is_running`/`stop`/`finish` + 四工厂 bool 化 + `shake` 内化；四落点迁移 + `tests/test_motion.py` 11 例
  - **C2 ✅**：删 `main_window._kpi_signal` 1 行中继与 kpi_presenter 绕环延迟导入，判定归位私有 `_window_signal`
  - **C3 ✅**：FetchPageBase 删只写不读的 `_data`；空/错态占位文案单源为类常量 `_EMPTY_TEXT`/`_ERROR_TEXT`；ExchangePage 补 `_render_error`（错误态不再与空态同形）
  - **C4 ✅**：KPI count-up 判据改纯语义（删展示文案判据）+ 源码守卫；加载中文案单源 `_LOADING_TEXT`
  - **C5 ✅**：仪表盘页族同构 `DashboardPage(QWidget)`（构造参数即接口、标签公开）；7 组信号接线归 `MainWindow._connect_signals`；`_build_card` 内迁 `_card_frame()`
  - **C6 ✅**：删 `MainWindow._view_n` 镜像，视图条数唯一来源 `table.current_view()`（回归 ADR-0003 Q8 定案）
  - 状态：**642/642 测试**、doc_sync 双绿；候选 C7（Worth exploring）在 TECH_DEBT 候选池（另有 C4 验收发现的 DFD-7 测试基建项）
- 下一步：C7（主题刷新从约定制变接口）
- 清场保持：`.worktrees/` 与 `.scratch/` 空，分支仅 main

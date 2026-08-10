# Y-05：账号切换（运行中切换 + 记账页整体重载 + 落盘）

- **Blocked by**: Y-04（侧边栏账号区）
- **Status**: ready-for-agent

## What to build

用户视角：下拉选择另一个账号 → 记账页立即整体重载为新账号数据（表格、曲线图、汇总磁贴、今日状态、标题栏账号名全部刷新），输入区清空、未保存的编辑 / 复用被取消；之后的保存 / 删除 / CSV 导出都落在新账号；利润页不受任何影响；重启后仍在新账号；选择当前账号本身不触发重载。

端到端验证：两个账号各存不同数据 → 切换 → 表格 / 曲线 / 汇总显示新账号数据、标题更新、settings.json 写入 current_account；保存一条记录后关窗重开 → 数据与账号都正确恢复。

## 文件范围

- 修改 `app/main_window.py`（切换处理：换 DataStore/logic → refresh_display → 取消编辑/复用 → 更新标题与落盘）
- 修改 `app/sidebar.py`（切换信号接线）
- 修改 `tests/test_ui_smoke.py`（切换集成用例组）

## 高不确定实现点

无 major（逻辑换载路径简单：save_today / _delete_record 已即时落盘到 self.store，换 store 即换落盘目标）。需在验收中覆盖的次要风险：KPI count-up 动画状态（_last_summary_total 等）与输入面板编辑态不跨账号泄漏。

## 验收标准

- [ ] 切换信号 → MainWindow 以目标账号路径构造新 DataStore 并重新加载 logic → `refresh_display()` 全量刷新（表格 / 曲线 / 汇总 / 今日状态）
- [ ] 标题栏账号名与下拉框选中态同步新账号；`_save_settings` 写入 current_account（重启回到新账号，有回读断言）
- [ ] 切换时取消编辑 / 复用模式（input_panel 退出编辑与复用态），防止跨账号污染
- [ ] 切换后保存 / 删除 / CSV 导出即时落在新账号（集成断言：数据写入目标账号文件，原账号文件不变）
- [ ] 选择当前账号本身 → no-op（不重载、不落盘）
- [ ] 利润页零改动：切换不触碰 profit_page 状态（有断言）
- [ ] 集成用例：切换后三处刷新 / 落盘回读 / 编辑态取消 / 利润页不受影响 / 同账号 no-op；覆盖率维持 ≥ 90%

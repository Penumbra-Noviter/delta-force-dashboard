# 收益计算器 — 项目状态

## 技术栈
- Python 3.12+ / PySide6 / pyqtgraph
- 打包：PyInstaller（单文件 exe）
- 测试：pytest（103 项）

## 开发阶段
1. **第一阶段**（Tkinter 内增强）✅ — 表格新增收益率列 + 盈亏标签
2. **第二阶段**（PySide6 迁移）✅ — 全量迁移至 PySide6 + pyqtgraph
3. **第三阶段**（架构优化）✅ — P0-P4 全部完成 + 单实例保证

## 关键决策
- UI 框架：PySide6（LGPL，Qt 官方绑定）
- 图表库：pyqtgraph（原生 Qt 渲染）
- 单实例：QLocalServer/QLocalSocket（Qt 原生方案）
- 数据持久化：JSON 原子写入 + 3 份滚动备份

## 文件结构
- `main.py` — 入口，含单实例检查
- `app/main_window.py` — QMainWindow 核心
- `app/input_panel.py` — 输入面板（含 debounce）
- `app/chart_widget.py` — pyqtgraph 图表（增量主题切换）
- `app/table_widget.py` — 7 日数据表格
- `app/theme.py` — QSS 样式生成
- `calculator.py` — 业务逻辑
- `data_store.py` — JSON 持久化
- `formatting.py` — 金额格式化/解析
- `config.py` — 路径、字体、主题色板

## 注意事项
- 主题切换时用 `get_color(key)` 而非模块级常量
- `warehouse` 包含 `cash`（总收益 = warehouse）
- 编辑模式使用 `unformat_input_value()` 转为纯数字

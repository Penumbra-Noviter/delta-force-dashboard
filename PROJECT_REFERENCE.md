# 收益计算器 — 项目介绍书

> **一句话**：每日记录现金和仓库价值两项数据，自动绘制 7 日收益曲线，计算盈亏。  
> **技术栈**：Python PySide6 + pyqtgraph  
> **打包**：PyInstaller → 单 exe

---

## 一、项目概述

收益计算器（Profit Calculator）是一款 Windows 桌面工具，主要面向个人投资者。

**核心场景**：用户每天记录「当前现金」和「仓库价值（含现金）」两个数字，工具自动记录最近 7 天数据，以表格展示每日盈亏变化，并以双曲线图可视化趋势。

**当前状态**：功能完整，架构已优化。PySide6 迁移完成，第三阶段 P0-P5 + Phase 4（T-01~T-05）+ C 系列（C1/C2）架构优化已完成，新增单实例保证。116 项测试全部通过。

---

## 二、数据模型

### 核心数据结构

```python
# data.json 格式（日期为 key）
{
  "2026-07-27": {
    "cash": 88541000.0,        # 当前现金 (float)
    "warehouse": 460900000.0   # 仓库价值 = 含现金的总收益 (float)
  },
  ...
}
```

**重要业务规则**：
- `cash` 是 `warehouse` 的组成部分（现金 ⊆ 仓库）
- **总收益 = warehouse**（不是 warehouse + cash）
- 数据只保留最近 7 天（超出时删除最旧记录）
- 日期格式 `YYYY-MM-DD`，硬编码在 `config.DATE_FORMAT`

### 关键计算

```python
# 较前日差值（已有）
delta = today.warehouse - prev_day.warehouse
# 显示为 ▲ +¥xx / ▼ ¥-xx / — ¥0.00（红涨绿跌）

# 收益率（待添加，第一阶段）
rate = (today.warehouse - prev_day.warehouse) / prev_day.warehouse * 100
# 显示为 +2.4% / -1.3%（1位小数，红涨绿跌）

# 盈亏标签（待添加，第一阶段）
盈 ← today.warehouse > prev_day.warehouse
亏 ← today.warehouse < prev_day.warehouse
— ← 无前日数据
```

---

## 三、模块架构

### 3.1 文件布局

```
Profit Calculator/
├── main.py                  ← [主入口] PySide6 QApplication
├── app/
│   ├── __init__.py          ← app 包标记
│   ├── main_window.py       ← [UI 骨架] QMainWindow 组件协调
│   ├── input_panel.py       ← 输入面板：现金 + 仓库输入框、校验、编辑模式
│   ├── table_widget.py      ← 7 日数据表格：日期、现金、仓库、较前日、操作
│   ├── chart_widget.py      ← pyqtgraph 双曲线图 + PNG 导出
│   ├── config.py            ← 配置 + 主题 (QSS)
├── calculator.py            ← [业务逻辑] DayRecord + 查询/差值计算
├── config.py                ← [基础配置] 路径、字体、亮暗主题色表
├── data_store.py            ← [持久化] JSON 原子写入 + 滚动备份 + 损坏恢复
├── formatting.py            ← [工具] 金额格式化/输入清洗（K/M/B 后缀）
├── tests/
│   ├── test_calculator.py   ← 21 个测试
│   ├── test_data_store.py   ← 18 个测试
│   └── test_formatting.py   ← 31 个测试
├── data.json                ← 运行态数据
├── settings.json            ← 窗口几何 + 置顶 + 主题持久化
├── CONSENSUS.md             ← 开发共识文档
├── PROJECT_REFERENCE.md     ← 项目介绍书
├── requirements.txt         ← PySide6 + pyqtgraph
└── 收益计算器.exe            ← 已打包的可执行文件
```

### 3.2 模块职责明细

#### `main.py`（~34 行）
PySide6 入口点。创建 QApplication（高 DPI 缩放），实例化 `MainWindow`，进入事件循环。`if __name__ == "__main__": main()`

#### `app/main_window.py`（~450 行）
核心类 `MainWindow`（QMainWindow），管理：
- 窗口初始化：DPI 感知、几何恢复（兼容 Tkinter 旧格式）、缩放
- 组件协调：实例化 InputPanel / TableWidget / ChartWidget，串接数据流（信号/槽）
- 键盘绑定：QAction → Enter 保存 / Esc 清空
- 主题切换：QSS 样式表一键切换，主题按钮文字联动
- 置顶切换：`windowFlags() ^ WindowStaysOnTopHint`
- 数据流：`save_today()` → parse → validate → save → 旋转 7 日 → 持久化 → 刷新表格+图表
- 编辑模式：`_start_edit()` → 回填数据到输入面板，修改后 `save_today()` 写回原日期
- 删除模式：确认对话框 → `logic.delete_record(date)` → 持久化 → 刷新

#### `calculator.py`（~107 行）
纯业务逻辑，无 UI 依赖：
- `DayRecord`：frozen dataclass，`cash` / `warehouse` / `date`，property `total` = `warehouse`
- `ProfitCalculatorLogic.get_record(date)`：查单日数据，异常返回 None
- `ProfitCalculatorLogic.save_record(date, cash, warehouse)`：写数据
- `ProfitCalculatorLogic.last_record_before(date)`：向前回溯最近有效记录（跳过空/无效日）
- `ProfitCalculatorLogic.get_weekly_records(end_date, days=7)`：获取连续 N 天数据（含 None 占位）
- `ProfitCalculatorLogic.delete_record(date)`：删除单日记录（不存在时返回 False）
- `ProfitCalculatorLogic.rotate_weekly(days=7)`：7 日保留策略，超过上限删除最旧记录
- `ProfitCalculatorLogic.summary(end_date, days=7)`：7 日窗口总盈亏（末日−首日仓库值）
- `ProfitCalculatorLogic.format_diff(diff)`：返回 `(符号, 格式化金额, 颜色)` 三元组

#### `config.py`（~154 行）
- 路径：`DATA_FILE` / `BACKUP_FILE` / `SETTINGS_FILE`
- 字体：Microsoft YaHei 系列（标题 18 / 输入 13 / 标签 11 / 表格 10 / 按钮 12）
- 主题：`THEMES` 字典，`light` + `dark` 两套，各有 ~30 个颜色 token（CHART_ / TABLE_ / FG_ / BG_ / BTN_ / BORDER_ 系列）
- 模块级函数：`get_theme()` / `set_theme(name)` / `get_color(key)`
- **注意**：模块级常量（FG_POS / FG_NEG 等）在导入时固定为 light，运行时主题切换需用 `get_color()`

#### `data_store.py`（~110 行）
`DataStore` 类，负责 JSON 持久化：
- `load()`：先读主文件 → 损坏则依次尝试 `.bak.1` → `.bak.2` → `.bak.3` → `.bak` → 空字典
- `save(data)`：滚动备份（`_rotate_backups`）→ 原子写入（`.tmp` → `os.replace`）
- 滚动机制：`max_backups=3`，每次保存前备份当前文件为 `.bak.1`，旧备份后移
- 兼容旧版单文件 `.bak`（与 `.bak.1` 内容相同）

#### `formatting.py`（~106 行）
金额处理工具：
- `format_money(value)`：`¥1,234.56` / `¥5,378.1K` / `¥419.9M` / None → `—`
- `parse_money_input(text)`：支持 `¥/$/￥`、千分位逗号、`K/M/B` 后缀、空格、负号
- `is_valid_money_input(text)`：空字符串合法（占位），`"abc"` 非法
- `format_input_value(value)` / `unformat_input_value(text)`：焦点进出的格式转换

#### `data_store.py`（~110 行）

---

## 四、测试体系

- **框架**：pytest
- **覆盖范围**：
  - `calculator.py`：DayRecord 属性、增删改查、差值计算、7 日滚动查询、集成流程 — 21 用例
  - `data_store.py`：保存/加载回环、滚动备份编号、损坏恢复、原子写入残留 — 18 用例
  - `formatting.py`：金额格式化（大/小/零/负/None）、输入解析（符号/后缀/空格/中文）、校验边界 — 31 用例
- **运行**：项目根目录执行 `pytest`
- **注意**：当前无 UI 测试（Tkinter + matplotlib 测试困难），PySide6 迁移后可考虑 `pytest-qt`

---

## 五、UI 界面结构

```
┌─────────────────────────────────────────────┐
│  收益计算器               🌙暗色  📌置顶    │  ← 标题栏
│  2026-07-28                                 │  ← 日期
├─────────────────────────────────────────────┤
│  [卡片框]                                    │
│  当前现金       [___________]               │  ← 输入框
│  仓库价值(含现金) [___________]               │
│  [保存今日数据] [取消编辑]  ✓已保存...       │  ← 按钮栏
├─────────────────────────────────────────────┤
│  [卡片框]                                    │
│ ┌─────┬──────┬──────┬──────┬──────┬────┬────┐ │
│ │日期 │ 现金 │仓库   │较前日 │收益率 │盈亏│操作│ │  ← 7列（已完成）
│ ├─────┼──────┼──────┼──────┼──────┼────┼────┤ │
│ │07/27│¥88.5K│¥460.9M│+¥10.7M│+2.4% │ 🟢盈│✎✕ │ │
│ │...  │      │      │      │    │    │    │ │
│ └─────┴──────┴──────┴──────┴────┴────┴────┘ │
├─────────────────────────────────────────────┤
│  [卡片框 / 图表区]                           │
│  ┌─────────────────────────────────────────┐│
│  │ ↑ 仓库价值（总收益）曲线                ││
│  │  ╱╲    ╱╲    ╱╲                        ││
│  │ ╱  ╲  ╱  ╲  ╱  ╲                       ││
│  │╱    ╲╱    ╲╱    ╲                      ││
│  │─────────────────────────────────────────││
│  │ ↓ 现金（子项）曲线                      ││
│  │...                                      ││
│  └─────────────────────────────────────────┘│
├─────────────────────────────────────────────┤
│  Enter保存 │ Ctrl+A全选 │ Esc清空 │ K/M/B  │  ← 底部提示
└─────────────────────────────────────────────┘
```

---

## 六、关键决策架构记录

| 决策 | 内容 |
|------|------|
| **数据格式** | JSON 本地文件，无数据库依赖 |
| **持久化策略** | 原子写入（先 tmp 再 replace）+ 3 份滚动备份 + 兼容旧单文件备份 |
| **数据保留** | 最多 7 天，超出删除最旧（第一次见到这个限制时要确认是否合理） |
| **金额模型** | cash 和 warehouse 均为 float，warehouse 已含 cash |
| **金额显示** | < 1M 显示为 ¥x,xxx.xx；≥ 1M → K 后缀；≥ 100M → M 后缀 |
| **输入解析** | 兼容 ¥/￥/$、千分位、K/M/B 后缀、负号、首尾空格 |
| **主题系统** | 两套完整色板（light/dark），约 30 个语义化 token |
| **图表** | pyqtgraph 原生渲染，双图（仓库价值 + 现金），持久化 PlotCurveItem/FillBetweenItem，增量 setData 更新 |
| **打包** | PyInstaller 单文件（`dist/收益计算器.exe`），无需 hiddenimports |
| **未来规划** | ② 整体迁移 PySide6 + pyqtgraph（第一阶段：表格新增收益率 + 盈亏标签 ✅ 已完成） |

---

## 七、常碰坑点

1. **主题切换**：模块级常量（`FG_POS` 等）在 `import` 时固定为 light 主题，运行时切换主题必须调用 `get_color(key)` 而非直接引用常量。
2. **单实例保证**：`main.py` 通过 QLocalServer/QLocalSocket 防止多开；崩溃后残留 socket 会自动清理，无需手动删除。
3. **7 日限制**：`ProfitCalculatorLogic.rotate_weekly()` 在每次 `save_today()` 后执行，排序后从最旧开始删，确保不超过 7 条。
4. **day_record.total**：`total` 直接返回 `warehouse`（不是 warehouse + cash）。现金是 warehouse 的组成部分。
5. **编辑模式**：编辑回填时使用 `unformat_input_value()` 转为纯数字，保存时用原日期覆盖写入。
6. **增量 vs 全量图更新**：`_ChartPanel` 使用持久化的 `PlotCurveItem` + `FillBetweenItem`，更新时仅 `setData()` 不重建组件；填充边界曲线也持久化，避免此前 FillBetweenItem 重建开销。

---

## 八、与 Agent 合作建议

- **第一阶段改动范围小**：主改 `ui/table.py`（增列）+ `calculator.py`（可能加收益率方法），风险低
- **第一阶段可直接用当前 Agent 执行**：改 2-3 文件，无需额外环境准备
- **第二阶段启动前验证环境**：`pip install PySide6 pyqtgraph`
- **第二阶段迁移策略**：先搭 QMainWindow 骨架 → 逐步移植子组件 → 每移植一个验证一次
- **data.json 的现有数据**：有 6 天真实数据（2026-07-20 ~ 2026-07-27），开发过程中注意备份
- **测试**：`pytest` 在项目根目录运行，测试不依赖 UI

---

*本文档覆盖范围截至 2026-07-28。配合 `CONSENSUS.md` 使用以了解下一步操作。*

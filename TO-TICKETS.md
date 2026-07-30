# To-Tickets — 收益计算器架构优化工单

> **来源**：2026-07-30 Python Architecture Review  
> **状态**：已录入，待评估  
> **前置阶段**：第三阶段 P0-P5 架构优化 ✅ 已完成

---

## 工单总览

| Ticket | 标题 | 类型 | 优先级 | 预估工时 | 依赖 | 关联 |
|--------|------|------|--------|----------|------|------|
| T-01 | 从业务逻辑中剥离展示层颜色 | 重构 | **P0** | ~1h | 无 | T-02 |
| T-02 | 主题系统收敛至 `app/theme.py` | 重构 | **P1** | ~1h | T-01 | — |
| T-03 | MainWindow 注入点 | 重构 | **P2** | ~1.5h | 无 | — |
| T-04 | UI 模块定义 `__all__` | 规范 | **P3** | ~0.5h | 无 | — |
| T-05 | ChartWidget 拆分 `_ChartPanel` | 重构 | **P4** | ~2h | 无 | — |

---

## T-01: 从业务逻辑中剥离展示层颜色

- **类型**：重构 (Boundary Leak)
- **优先级**：P0 — 基石工单，阻塞 T-02
- **预估工时**：~1 小时
- **文件范围**：`calculator.py`, `config.py`, `app/table_widget.py`, `tests/test_calculator.py`, `verify_all.py`

### 问题描述

`ProfitCalculatorLogic.format_rate()` 和 `get_pnl_label()` 返回 `(str, hex_color)` 元组——业务层调用了 `config.get_color()` 来获取 UI 颜色值。

```python
# calculator.py — 当前问题
from config import get_color

@staticmethod
def format_rate(rate: float | None) -> tuple[str, str]:
    if rate is None:
        return "—", get_color("FG_MUTED")   # ← 业务方法返回颜色
    if rate > 0:
        return f"+{rate:.1f}%", get_color("FG_POS")
```

**架构问题**：
- 业务逻辑（`calculator.py`）依赖 UI 配置（`config.get_color`），违反依赖方向
- 颜色值在 import 时已确定，运行时主题切换时不会更新
- 测试代码也必须导入 `get_color` 来断言颜色值

### 解决思路

将业务方法改为返回 **结构化语义数据**，UI 层负责映射为颜色：

```python
from enum import Enum

class RateSignal(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    NONE = "none"

# 改为:
@staticmethod
def format_rate(rate: float | None) -> tuple[str, RateSignal]:
    ...
    return f"+{rate:.1f}%", RateSignal.POSITIVE
```

UI 层（`table_widget.py`）负责将 `RateSignal` 映射为当前主题的颜色值。

### 涉及改动

| 文件 | 改动 |
|------|------|
| `calculator.py` | 新增 `RateSignal`/`PnL信号` 枚举；`format_rate()` 返回 `(str, RateSignal)`；`get_pnl_label()` 返回 `(str, PnL信号)`；移除 `import config` |
| `app/table_widget.py` | `draw()` 中添加信号→颜色映射逻辑 |
| `tests/test_calculator.py` | 断言改为检查枚举值而非颜色字符串；移除 `from config import get_color` |
| `verify_all.py` | 更新断言以匹配新返回值 |

### 验收标准

- [ ] `pytest tests/` 全部通过
- [ ] `verify_all.py` 全部通过
- [ ] 表格收益率列/盈亏标签显示颜色与当前主题一致
- [ ] 切换主题后颜色正确更新（不依赖业务层）
- [ ] `calculator.py` 不再 import `config.get_color`

---

## T-02: 主题系统收敛至 `app/theme.py`

- **类型**：重构 (Pass-through elimination)
- **优先级**：P1 — 依赖 T-01 完成
- **预估工时**：~1 小时
- **文件范围**：`config.py`, `app/theme.py`, `app/__init__.py`, `app/main_window.py`, `app/input_panel.py`, `app/table_widget.py`, `app/chart_widget.py`, `app/config.py`, `tests/` (不变)

### 问题描述

主题数据 (`THEMES` 字典) 和主题函数 (`get_color`, `set_theme`, `get_theme`) 定义在根目录 `config.py` 中。`app/theme.py` 从 `config.py` 导入并重新导出（添加 `generate_qss`）。`app/__init__.py` 又从中重新导出 3 个函数。

结果是三个不同的导入路径指向同一个函数——消费者可能从 `config`、`app.theme` 或 `app` 导入 `get_color`，取决于他们所在的层。

### 解决思路

- 将 `THEMES`、`get_color`、`set_theme`、`get_theme` 从 `config.py` 移至 `app/theme.py`
- `app/__init__.py` 移除重新导出
- 所有消费者统一从 `app.theme` 导入主题函数
- `config.py` 保留路径/字体/日期常量

**前置条件**：T-01 必须已完成——`calculator.py` 停止 import `get_color` 后才可移动主题数据。

### 涉及改动

| 文件 | 改动 |
|------|------|
| `config.py` | 删除 `THEMES`、`get_theme()`、`set_theme()`、`get_color()`；保留路径、字体、`DATE_FORMAT` 常量 |
| `app/theme.py` | 将 `THEMES`、`get_theme()`、`set_theme()`、`get_color()` 移入此处（非 import，而是直接定义） |
| `app/__init__.py` | 移除 `from app.theme import ...` + `__all__` 重新导出 |
| `app/config.py` | 删除此文件（已为空） |
| `app/main_window.py` | `from app.theme import ...`（已有，不需要改） |
| `app/input_panel.py` | `from app.theme import ...`（已有，不需要改） |
| `app/table_widget.py` | `from app.theme import ...`（已有，不需要改） |
| `app/chart_widget.py` | `from app.theme import ...`（已有，不需要改） |

### 验收标准

- [ ] `pytest tests/` 全部通过
- [ ] `verify_all.py` 全部通过
- [ ] `grep -r "from config import.*get_color\|from config import.*set_theme\|from config import.*get_theme" \*.py` 返回空
- [ ] `grep -r "from app import"` 中不包含 `get_color`/`set_theme`/`get_theme`

---

## T-03: MainWindow 依赖注入接口

- **类型**：重构 (Seam creation)
- **优先级**：P2
- **预估工时**：~1.5 小时
- **文件范围**：`app/main_window.py`, `verify_all.py`

### 问题描述

`MainWindow.__init__()` 在构造函数中直接创建 `DataStore()` 和 `ProfitCalculatorLogic(self.data)`：

```python
def __init__(self) -> None:
    ...
    self.store = DataStore()
    self.data = self.store.load()
    self.logic = ProfitCalculatorLogic(self.data)
```

为此，`verify_all.py` 中的测试必须设置临时 `SETTINGS_FILE` 路径并依赖真实的文件 I/O，无法注入 mock 存储。

### 解决思路

为构造函数添加可选参数：

```python
class MainWindow(QMainWindow):
    def __init__(self, store: DataStore | None = None,
                 logic: ProfitCalculatorLogic | None = None) -> None:
        ...
        self.store = store or DataStore()
        self.data = self.store.load()
        self.logic = logic or ProfitCalculatorLogic(self.data)
```

`verify_all.py` 测试可注入 `store` 和 `logic`，避免文件 I/O 副作用。

### 涉及改动

| 文件 | 改动 |
|------|------|
| `app/main_window.py` | `__init__` 添加可选参数 `store` 和 `logic`；默认行为不变 |
| `verify_all.py` | 考虑为使用 mock store 的测试添加注入版本（可选改进） |

### 验收标准

- [ ] `pytest tests/` 全部通过
- [ ] `verify_all.py` 全部通过
- [ ] 原始无参调用 `MainWindow()` 行为保持不变
- [ ] 手写的测试可以注入 mock store 而无需文件系统

---

## T-04: UI 模块定义 `__all__`

- **类型**：规范 (Protocol surface)
- **优先级**：P3
- **预估工时**：~0.5 小时
- **文件范围**：`app/main_window.py`, `app/input_panel.py`, `app/table_widget.py`, `app/chart_widget.py`

### 问题描述

`app/` 包中 4 个模块缺少 `__all__`。尽管内部辅助方法以 `_` 为前缀（按约定为私有），但无显式协议表面。IDE 无法区分公共表面和内部细节。

对比：`calculator.py`、`formatting.py`、`data_store.py`、`app/theme.py` 均已定义 `__all__`。

### 解决思路

为每个模块添加 `__all__`，只列出该模块的公共表面：

| 模块 | `__all__` |
|------|-----------|
| `app/main_window.py` | `MainWindow` |
| `app/input_panel.py` | `MoneyLineEdit`, `InputPanel` |
| `app/table_widget.py` | `PnLBadge`, `TableWidget` |
| `app/chart_widget.py` | `ChartWidget` |

### 涉及改动

每个文件只需添加一行 `__all__ = [...]` 后紧跟模块 docstring。

### 验收标准

- [ ] `pytest tests/` 全部通过
- [ ] `verify_all.py` 全部通过
- [ ] 每个 UI 模块在文件顶部定义 `__all__`
- [ ] 对外部消费者无行为变化

---

## T-05: ChartWidget 拆分 `_ChartPanel` ✅ 已完成

- **类型**：重构 (Duplication elimination)
- **优先级**：P4
- **预估工时**：~2 小时
- **文件范围**：`app/chart_widget.py`

### 问题描述

`ChartWidget` 管理 20 多个实例变量，跟踪上下两个图表面板的子元素（`_plot_widget_top`、`_curve_top`、`_fill_warehouse`、`_vline_top`、`_hover_label_top`、`_proxy_top`……与 `_bottom` 对称版本配对）。

`_update_theme_colors()` 长 ~80 行，必须镜像 `_create_chart()` 的结构——这是一个需维护的不变量。顶部和底部面板的创建/主题更新代码约 80% 完全相同。

### 解决思路

提取 `_ChartPanel` 辅助类，拥有一个 PlotWidget 及其所有子元素。`ChartWidget` 委托给两个 `_ChartPanel` 实例：

```python
class _ChartPanel(QWidget):
    """管理单个图表面板（一条曲线 + 填充 + hover + 标签）。"""
    def __init__(self, label: str, color_key: str, style: dict) -> None: ...

    def draw(self, x, values, dates) -> None: ...
    def update_data(self, x, values) -> None: ...
    def update_theme(self) -> None: ...
    def export(self) -> pg.PlotWidget: ...
```

`ChartWidget` 简化为：

```python
class ChartWidget(QWidget):
    def __init__(self) -> None:
        self._top = _ChartPanel("仓库价值", "CHART_WAREHOUSE", {...})
        self._bottom = _ChartPanel("现金", "CHART_CASH", {...})
```

### 涉及改动

| 文件 | 改动 |
|------|------|
| `app/chart_widget.py` | 新增 `_ChartPanel` 类；`ChartWidget` 委托给两个实例；删除重复的 `_*.top`/`_*.bottom` 变量；`_update_theme_colors` 缩减为两行循环 |

### 验收标准

- [ ] `pytest tests/` 全部通过
- [ ] `verify_all.py` 全部通过
- [ ] 上下两个图表面板外观与之前完全相同
- [ ] 主题切换后两个面板颜色均正确更新
- [ ] hover 十字线和数值标签在两张图上均正常工作
- [ ] PNG 导出功能正常

---

## 进度记录

| 日期 | Ticket | 操作 | 状态 |
|------|--------|------|------|
| 2026-07-30 | T-01 ~ T-05 | 创建工单 | 📝 已录入 |
| 2026-07-30 | T-01 | 完成 — 从业务逻辑剥离展示层颜色 | ✅ 已完成 |
| 2026-07-30 | T-02 | 完成 — 主题系统收敛至 `app/theme.py` | ✅ 已完成 |
| 2026-07-30 | T-03 | 完成 — MainWindow 依赖注入接口 | ✅ 已完成 |
| 2026-07-30 | T-04 | 完成 — UI 模块定义 `__all__` | ✅ 已完成 |
| 2026-07-30 | T-05 | 完成 — ChartWidget 拆分 `_ChartPanel` | ✅ 已完成 |

---

## 工单状态说明

- **📝 已录入**：已记录但尚未进入开发计划
- **🔜 待排期**：已确认需求，等待排入迭代
- **🔄 进行中**：正在开发中
- **✅ 已完成**：已合并验证通过
- **❌ 已关闭**：经评估决定不实施

# 收益计算器 (Profit Calculator)

一款为个人投资者打造的 Windows 桌面收益追踪工具。每天记录「当前现金」与「仓库价值」两个数字，自动计算盈亏变化、收益率，并以表格和双曲线图直观展示最近 7/30 条记录的趋势（视图可切换）。

**纯本地运行，无需联网，数据以 JSON 文件存储于本地。**

---

## 核心功能

- **每日数据录入** — 记录现金与仓库价值，支持 K/M/B 后缀快捷输入（如 `1.2M` = ¥1,200,000）
- **30 条滚动留存 + 7/30 视图切换** — 自动保留最近 30 条实际录入记录（间断录入不丢历史），表格/曲线图/汇总随视图 7/30 一键切换，切回 7 不丢数据
- **双曲线图可视化** — 仓库价值（主色）与现金（副色）双轴对比，支持鼠标悬停查看精确数值
- **最近 7/30 条总盈亏汇总** — 表格上方实时显示当前视图窗口的总盈亏金额，红绿色标，随视图切换联动
- **复用昨日数据** — 一键填入昨日数据后微调，无需重复输入大额数字
- **编辑 / 删除** — 可随时修改或删除任意日期的记录
- **CSV 导出** — 一键导出全部记录为 CSV（Excel 可直接打开），便于外部查看/备份
- **今日未录入提醒** — 今日尚未记录时标题栏常驻提示，保存后自动消失
- **亮 / 暗双主题** — 亮色 Sage Ledger 青绿暖纸 + 暗色 Midnight & Amber 琥珀午夜，降低长时间使用疲劳
- **窗口置顶** — 可将窗口固定在最前，方便边操作其他软件边录入
- **数据安全** — JSON 原子写入 + 滚动备份 + 损坏自动恢复 + 运行日志（`profit_calculator.log`）
- **单实例运行** — 防止多开冲突

---

## 界面预览

应用采用左侧边栏导航 + 右侧页面区布局，包含以下页面：

### 记账仪表盘
1. **标题栏** — 应用名称、今日未录入提醒、当前日期
2. **输入卡片** — 现金 / 仓库输入框 + 复用昨日按钮 + 保存按钮
3. **最近 7/30 条汇总条** — 总盈亏金额实时显示（随视图切换）
4. **数据表格** — 7/30 条视图可切换（按钮组），含日期、现金、仓库、较前日、收益率、盈亏 Badge、操作按钮
5. **双曲线图** — 仓库价值与现金双轴对比趋势
6. **提示栏** — 键盘快捷键说明

### 利润（制造产物 + 兑换利润）
- **制造产物**：4 个制造台位（技术中心/工作台/制药台/防具台）的最新推荐产物，按利润降序排列
- **兑换利润**：7 种子弹自选包（3/4/5 级 + 通行证基础/高级 + 进阶/特级物流）中利润最高的子弹兑换方案

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.10+ |
| UI 框架 | PySide6 (Qt for Python) |
| 图表库 | pyqtgraph |
| 数据存储 | 本地 JSON（原子写入 + 滚动备份） |
| 打包工具 | PyInstaller |
| 测试框架 | pytest（300 项测试，含 offscreen UI 烟测 + kkrb.net API 单元测试） |

---

## 快速开始

### 方式一：直接运行打包版（推荐）

前往 [Releases](../../releases) 下载 `收益计算器` 打包目录（压缩包），解压后双击目录内 `收益计算器.exe` 即可运行，无需安装 Python 环境。运行态数据（`data.json`/`settings.json`/日志）统一生成在用户目录 `C:\Users\<你的用户名>\收益计算器\`（开发版与打包版共用；旧版 exe 目录/项目根内的数据会在首次启动时自动迁移过去；迁移完成后若旧源仍存在，启动时会提示可手动清理旧数据源，应用不会自动删除）。

### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/Penumbra-Noviter/profit-calculator.git
cd profit-calculator

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

---

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 保存当前输入 |
| `Esc` | 清空当前聚焦的输入框 |
| `Tab` | 在现金 → 仓库 → 按钮间切换焦点 |
| `Ctrl+A` | 全选当前输入框内容 |

---

## 数据与隐私

- 所有数据存储于本地 `data.json` 文件（`C:\Users\<你的用户名>\收益计算器\data.json`），**不联网、不上传、不收集任何信息**
- 每次保存自动生成滚动备份，最多保留 4 份历史备份（3 份滚动 + 1 份兼容旧版）
- 数据文件损坏时可自动从最近备份恢复
- 窗口位置、主题、置顶状态等设置保存于 `settings.json`（同一目录）

---

## 项目结构

```
profit-calculator/
├── main.py                  # 程序入口（单实例 + 应用图标）
├── app/
│   ├── __init__.py          # app 包标记
│   ├── main_window.py       # 主窗口（组件协调与数据流）
│   ├── sidebar.py           # 左侧导航栏（记账/利润 + 底部操作按钮）
│   ├── crafting_page.py     # 制造产物推荐页面（4 台位卡片）
│   ├── exchange_page.py     # 兑换利润页面（7 种子弹自选包）
│   ├── profit_page.py       # 利润页面（标签页容器：制造产物 + 兑换利润）
│   ├── input_panel.py       # 输入面板（校验 + 编辑模式）
│   ├── table_widget.py      # 7/30 视图可切换数据表格
│   ├── chart_widget.py      # 双曲线图 + PNG 导出
│   └── theme.py             # 主题色板 + QSS 样式表生成
├── calculator.py            # 业务逻辑（DayRecord + 盈亏计算）
├── config.py                # 路径、日期格式、数据保留条数（RETENTION_LIMIT=30）
├── data_store.py            # JSON 持久化（原子写入 + 备份）
├── formatting.py            # 金额格式化与输入解析
├── json_file.py             # JSON 原子写 seam（atomic_write_json / try_load_json，D-02）
├── kkrb_client.py           # kkrb.net API 客户端（纯 stdlib，零外部依赖）
├── settings_store.py        # 设置持久化（SettingsStore，D-02）
├── signals.py               # 共享信号叶子（RateSignal / PnLSignal，D-08）
├── scripts/                 # F-01 文档同步工具链（doc_sync.py + pre-commit 钩子源）
├── tests/                   # 测试（292 项，含 offscreen UI 烟测）
├── app_icon.ico             # 应用图标（exe 文件 + 运行窗口）
├── 收益计算器.spec           # PyInstaller 打包配置
├── requirements.txt         # 运行时依赖（版本锁定）
└── requirements-dev.txt     # 开发依赖（pytest）
```

---

## 开发

### 运行测试

```bash
python -m pytest tests/ -q
```

### 打包

```bash
python -m PyInstaller 收益计算器.spec --noconfirm
```

打包产物位于 `dist/收益计算器/`（onedir：`收益计算器.exe` + `_internal/`，整目录分发或 zip 压缩）。O-20 起由单文件改为 onedir——免去每次启动把 80MB 包解压成 181MB 的开销，启动从 ~2-4s 降至 ~1.5s；体积经 excludes（matplotlib/PIL）+ Qt 模块白名单 + 翻译文件剔除瘦身。exe 文件图标与运行窗口图标均来自 `app_icon.ico`（spec `icon=` + `datas=` 内嵌）。

---

## 许可证

本项目为个人使用工具，未发布开源许可证。

# Delta Force Dashboard

一款为个人投资者打造的 Windows 桌面收益追踪工具。每天记录「当前现金」与「仓库价值」两个数字，自动计算盈亏变化、收益率，并以表格和双曲线图直观展示最近 7/30 条记录的趋势（视图可切换）。附带 Delta Force 游戏工具：制造产物/兑换利润速查与每日地图密码门（数据源 kkrb.net）。

**记账数据纯本地存储（JSON，不联网）；联网仅用于利润页与密码门查询 kkrb.net 公开接口（60 秒缓存，不发送任何本地数据）。**

---

## 核心功能

- **每日数据录入** — 记录现金与仓库价值，支持 K/M/B 后缀快捷输入（如 `1.2M` = ¥1,200,000）
- **30 条滚动留存 + 7/30 视图切换** — 自动保留最近 30 条实际录入记录（间断录入不丢历史），表格/曲线图/汇总随视图 7/30 一键切换，切回 7 不丢数据
- **KPI 双磁贴** — 仪表盘顶部实时展示「总盈亏」与「现金总变化」大数字（信号色 + count-up 滚动动画，数据不足自动降级）
- **双曲线图可视化** — 仓库价值（主色）与现金（副色）双轴对比，支持鼠标悬停查看精确数值
- **最近 7/30 条总盈亏汇总** — 表格上方实时显示当前视图窗口的总盈亏金额，红绿色标，随视图切换联动
- **复用昨日数据** — 一键填入昨日数据后微调，无需重复输入大额数字
- **编辑 / 删除** — 可随时修改或删除任意日期的记录
- **CSV 导出** — 一键导出全部记录为 CSV（Excel 可直接打开），便于外部查看/备份
- **今日未录入提醒** — 今日尚未记录时标题栏常驻状态 pill，保存后自动消失
- **亮 / 暗双主题** — 亮色 Sage Ledger 青绿暖纸 + 暗色 Midnight & Amber 琥珀午夜，降低长时间使用疲劳；图标为内嵌 SVG 矢量（Material 系风格），颜色随主题切换
- **窗口置顶** — 可将窗口固定在最前，方便边操作其他软件边录入
- **数据安全** — JSON 原子写入 + 滚动备份 + 损坏自动恢复 + 运行日志（`delta_force_dashboard.log`，1MB 轮转 ×3）+ 崩溃现场捕获（`crash.log`）
- **利润速查（kkrb.net）** — 制造产物页（4 台位最新推荐产物，按利润降序）+ 兑换利润页（7 种子弹自选包利润最高的兑换方案），60 秒缓存，启动后台预加载
- **每日密码门速查（kkrb.net）** — 密码门页面实时展示 6 张地图（零号大坝/长弓溪谷/巴克什/航天基地/潮汐监狱/AZ3）每日密码大字卡片，与利润页共享连接、随启动预加载
- **单实例运行** — 防止多开冲突
- **多账号记账** — 侧边栏账号区可新建 / 切换多个账号，各账号独立数据（`accounts/<账号名>/data.json`，目录即账号名），旧数据自动复制迁移为「主账号」（永不删源）；当前账号持久化于 `settings.json`，重启自动回到上次账号

---

## 界面预览

应用采用左侧边栏导航（图标 + 文字）+ 右侧页面区布局，包含以下页面：

### 记账仪表盘
1. **标题栏** — 应用名称（含当前账号名）、今日未录入状态 pill、当前日期
2. **KPI 磁贴** — 总盈亏 / 现金总变化双卡片（大数字 + 信号色 + count-up 动画）
3. **输入卡片** — 现金 / 仓库输入框 + 复用昨日按钮 + 保存按钮（含保存成功提示）
4. **最近 7/30 条汇总条** — 总盈亏金额实时显示（随视图切换）
5. **数据表格** — 7/30 条视图可切换（按钮组），含日期、现金、仓库、较前日、收益率、盈亏 Badge、操作按钮
6. **双曲线图** — 仓库价值与现金双轴对比趋势（右键菜单可导出 PNG）
7. **提示栏** — 键盘快捷键说明

### 利润（制造产物 + 兑换利润）
- **制造产物**：4 个制造台位（技术中心/工作台/制药台/防具台）的最新推荐产物，按利润降序排列
- **兑换利润**：7 种子弹自选包（3/4/5 级 + 通行证基础/高级 + 进阶/特级物流）中利润最高的子弹兑换方案

### 密码门（每日地图密码）
- 6 张地图卡片（零号大坝/长弓溪谷/巴克什/航天基地/潮汐监狱/AZ3），地图名 + 密码大字
- 数据源 kkrb.net `getBonusDoorData`，与利润页共享连接、随启动预加载；空态/错误态占位可点击重试

---

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| UI 框架 | PySide6 (Qt for Python) |
| 图表库 | pyqtgraph |
| 图标 | 内嵌 SVG 矢量（Material 系，24×24 单色路径 + 主题色注入，HiDPI 2x 渲染） |
| 数据存储 | 本地 JSON（原子写入 + 滚动备份） |
| 打包工具 | PyInstaller（onedir） |
| 测试框架 | pytest（630 项测试，含 offscreen UI 烟测 + kkrb.net API 单元测试） |

---

## 快速开始

### 方式一：直接运行打包版（推荐）

前往 [Releases](../../releases) 下载 `Delta Force Dashboard` 打包目录（压缩包），解压后双击目录内 `Delta Force Dashboard.exe` 即可运行，无需安装 Python 环境。运行态数据（`data.json`/`settings.json`/`accounts/`/日志）统一生成在用户目录 `C:\Users\<你的用户名>\Delta Force Dashboard\`（开发版与打包版共用；旧版 exe 目录/项目根内的数据会在首次启动时自动迁移过去；迁移完成后若旧源仍存在，启动时会提示可手动清理旧数据源，应用不会自动删除）。

### 方式二：从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/Penumbra-Noviter/delta-force-dashboard.git
cd delta-force-dashboard

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

- **记账数据纯本地**：`data.json` 与多账号目录 `accounts/`（`C:\Users\<你的用户名>\Delta Force Dashboard\`）仅保存在本机，**不联网、不上传、不收集任何信息**
- **联网边界**：仅利润页与密码门会请求 kkrb.net 公开接口（制造产物/兑换利润/密码门数据），请求不含任何本地数据；结果 60 秒缓存复用
- 每次保存自动生成滚动备份，最多保留 4 份历史备份（3 份滚动 + 1 份兼容旧版）
- 数据文件损坏时可自动从最近备份恢复
- 窗口位置、主题、置顶状态、当前账号等设置保存于 `settings.json`（同一目录）

---

## 项目结构

```
delta-force-dashboard/
├── main.py                  # 程序入口（单实例 + 崩溃现场捕获 + 日志轮转）
├── app/
│   ├── __init__.py          # app 包标记
│   ├── main_window.py       # 主窗口（组件协调与数据流）
│   ├── dashboard_page.py    # 记账仪表盘装配（build_dashboard 直构，C4）
│   ├── kpi_presenter.py     # KPI 双磁贴渲染（count-up + 主题只换色，C4）
│   ├── sidebar.py           # 左侧导航栏（记账/利润/密码门 + 账号区 + 底部操作按钮）
│   ├── crafting_page.py     # 制造产物推荐页面（4 台位卡片）
│   ├── exchange_page.py     # 兑换利润页面（7 种子弹自选包）
│   ├── bonus_door_page.py   # 密码门页面（地图密码大字卡片）
│   ├── fetch_page_base.py   # 数据页公共基类（懒加载四态 + 后台取数 + 错误重试）
│   ├── fetch_worker.py      # 后台请求 worker（QThread，网络调用移出 UI 线程）
│   ├── profit_page.py       # 利润页面（纵向堆叠：制造产物 + 兑换利润）
│   ├── motion.py            # 反馈型动效（fade_in_widget / animate_property）
│   ├── load_state.py        # 数据页四态状态机（idle/loading/loaded/failed）
│   ├── icons.py             # SVG 矢量图标（ICONS 表 + render_icon，主题色注入，ADR-0006）
│   ├── input_panel.py       # 输入面板（校验 + 编辑模式）
│   ├── table_widget.py      # 7/30 视图可切换数据表格
│   ├── chart_widget.py      # 双曲线图 + PNG 导出
│   └── theme.py             # 主题色板 + QSS 样式表生成
├── calculator.py            # 业务逻辑（DayRecord + 盈亏计算）
├── account_store.py         # 多账号存储层（账号目录管理 + 校验 + 旧数据迁移）
├── config.py                # 路径、日期格式、数据保留条数（RETENTION_LIMIT=30）
├── data_store.py            # JSON 持久化（原子写入 + 备份）
├── formatting.py            # 金额格式化与输入解析
├── presentation.py          # 展示纯函数（format_* 文案/信号，C5 边界）
├── json_file.py             # JSON 原子写 seam（atomic_write_json / try_load_json，D-02）
├── kkrb_client.py           # kkrb.net API 客户端（纯 stdlib，零外部依赖）
├── kkrb_models.py           # kkrb.net 数据模型（CraftingProduct/AmmoPackageItem/BonusDoorItem）
├── kkrb_parsing.py          # kkrb.net 响应解析纯函数（畸形输入容错）
├── settings_store.py        # 设置持久化（SettingsStore，D-02）
├── signals.py               # 共享信号叶子（RateSignal / PnLSignal，D-08）
├── scripts/                 # F-01 文档同步工具链（doc_sync.py + pre-commit 钩子源）
├── tests/                   # 测试（630 项，含 offscreen UI 烟测）
├── app_icon.ico             # 应用图标（exe 文件 + 运行窗口）
├── delta_force_dashboard.spec           # PyInstaller 打包配置
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
python -m PyInstaller delta_force_dashboard.spec --noconfirm
```

打包产物位于 `dist/Delta Force Dashboard/`（onedir：`Delta Force Dashboard.exe` + `_internal/`，整目录分发或 zip 压缩，约 67MB）。O-20 起由单文件改为 onedir——免去每次启动把 80MB 包解压成 181MB 的开销，启动从 ~2-4s 降至 ~1.5s；体积经 excludes（matplotlib/PIL）+ Qt 模块白名单 + 翻译文件剔除瘦身。exe 文件图标与运行窗口图标均来自 `app_icon.ico`（spec `icon=` + `datas=` 内嵌）。

---

## 许可证

本项目为个人使用工具，未发布开源许可证。

# ADR-0006：SVG 矢量图标替换 emoji（方案 C）

## 决策背景

UI 层 12 个 emoji 装饰图标（U-05 收敛至 `app/ui_text.py` 的 `EMOJI` 表，11 个 emoji
+ 1 个 ✓ 文本符号）存在三类固有缺陷：

1. **彩色 emoji 不随主题色**：emoji 是彩色的，暗色主题下与界面脱节；部分 emoji
   在暗底上有白底观感，与「跟随主题」的视觉契约冲突（U-03 同款矛盾）。
2. **渲染不可控**：依赖系统 `Segoe UI Emoji` 字体；字体缺失的系统渲染豆腐块；
   不同 Windows 版本 emoji 风格不同（Emoji 14/15 变体），基线错位问题只能靠
   字体族缓解（U-05 的折中），无法根治。
3. **语义弱**：emoji 是文字字符，无法换色、无法表达选中/悬停状态、无法做
   HiDPI 多分辨率。

方案 B（系统字体图标 Segoe Fluent Icons）曾为备选：实现路径与 emoji 相同、
改动小，但码位不可读、Win10/11 字体名不同需 fallback 链、非 Windows 零渲染，
且选中态换色同样无解。用户拍板走**方案 C：SVG 矢量图标 + QIcon**，更彻底。

## 可选方案

### 方案 A：Qt 内置图标（QStyle.standardIcon）

| 优势 | 代价 |
|------|------|
| 零资源、系统原生风格 | Windows 上集合小且丑（Fusion 灰色单调） |
| — | 业务语义（账本/利润/密码门）无对应图标，导航三项全部无解 |

### 方案 B：系统字体图标（Segoe Fluent Icons / MDL2 字体）

| 优势 | 代价 |
|------|------|
| 与 emoji 相同的文本拼接路径，改动极小 | 码位不可读（`\uE74E` 需逐条注释） |
| 单色矢量、跟随文本色 | Win10（MDL2）与 Win11（Fluent）字体名不同，必须 fallback 链 |
| 零资源文件 | 选中态换色无解（QSS 只管文字颜色） |
| — | 非 Windows 平台无此字体（本项目 Windows-only，风险可接受但不为零） |

### 方案 C：SVG 矢量图标 + QIcon（本 ADR 采用）

| 优势 | 代价 |
|------|------|
| 颜色完全可控：随主题色、选中态双色（QIcon Normal/Selected 模式） | 需新增图标渲染模块 + 各落点改 setIcon 装配 |
| HiDPI：QPixmap 高 DPI 多分辨率 | SVG 数据需内嵌或打包（见下「实现约定」） |
| 图标风格统一（同一设计语言，无系统字体差异） | 测试断言需同步（按钮文本不再含 emoji） |
| 零运行时外部依赖（内嵌字符串，PyInstaller 零改动） | — |

## 最终选择

✅ **方案 C：SVG 矢量图标 + QIcon**

## 理由

- 颜色可控是决定性论据：本项目主题契约（C1）要求所有视觉随主题刷新，
  emoji/字体图标都无法做到图标级换色，SVG 可以（render 时注入颜色）。
- 选中态双色（导航 Normal=正文色 / Selected=accent 色）只有 QIcon 多模式能表达。
- 内嵌 SVG 字符串（模板 `{color}` 占位）→ `QSvgRenderer` → `QPixmap` → `QIcon`：
  零资源文件、零打包改动（PyInstaller spec 不动），规避 O-C4 先例
  （模板化资源因 PyInstaller 资源路径问题被关闭）。
- QtSvg 随 PySide6 wheel 提供（已验证 6.11.1 可用），requirements 零变更。

## 实现约定

### 图标模块 `app/icons.py`（新，深模块）

- `ICONS: dict[str, str]` — 图标名 → SVG 模板（24×24 viewBox，单色 fill，
  占位 `{color}`；风格统一为 Material 系填充路径，MIT/Apache 2.0 许可族）。
- `render_icon(name: str, color: str, size: int = 16) -> QIcon` —
  QSvgRenderer 渲染到 `size×2` pixmap + `setDevicePixelRatio(2)`（HiDPI），
  返回 QIcon。
- **颜色由调用方传入**（`get_color` 运行期解析），模块内零 `get_color` 调用
  ——C1 铁律「绝不在模块顶层调 get_color」自然遵守。
- `__all__ = ["ICONS", "render_icon"]`。

### 图标键集（9 键，语义不变）

| 键 | 语义 | 落点 |
|----|------|------|
| `ledger` | 记账页 | sidebar 导航 |
| `wrench` | 利润页 | sidebar 导航 |
| `key` | 密码门 | sidebar 导航 |
| `plus` | 新建账号 | sidebar new_account_btn |
| `pin` | 置顶 | sidebar pin_btn（active 态换色） |
| `moon` / `sun` | 主题切换目标 | main_window theme_btn |
| `refresh` | 刷新 | fetch_page_base refresh_btn |
| `save` | 导出 PNG | chart_widget 右键菜单 action |

### 边界（不做图标化）

- **`account_title`（👤 账号）去 emoji 化 → 纯文本「账号」**：标题处图标属
  装饰，删除即替代；不为一个标题引入图标装配。
- **状态标签（🔄 加载中 / ⚠️ 失败）去 emoji 变体 → 文本符号（⟳ / ⚠）**：
  去 FE0F 变体选择符后为 BMP 单色文本符号，随文字色、可复制；状态文本是
  「文案」不是「图标」，保持 QLabel 纯文本（测试断言面最小）。
- **`✓`（成功标记）保留**：BMP 文本符号非 emoji，`presentation.py` 业务层
  同款，属文案语义不属图标。

### 主题联动（C1-08 契约扩展）

- `sidebar.apply_theme` 扩展：重建导航 3 项 icon（Normal=`FG_LABEL` /
  Selected=`BTN_BG`）+ new_account_btn/pin_btn icon。
- `FetchPageBase` 新增 `apply_theme`（重建 refresh_btn icon）——实现后自动
  纳入 `_theme_refreshers` 树遍历（契约无例外）。
- `chart_widget.apply_theme` 扩展：重建 export action icon。
- `main_window._update_theme_btn_text` 扩展：同时设 theme_btn icon
  （light 主题 → moon，dark 主题 → sun），已挂 refresh_theme 链路。
- `theme.py`：`QWidget` font-family 移除 `"Segoe UI Emoji"`（不再需要）。

### 退役

- 删除 `app/ui_text.py`（`EMOJI` 表），4 处 import 同步清（sidebar /
  fetch_page_base / chart_widget / main_window）。
- U-05 守卫测试重写：`test_ui_smoke` 的 emoji 正则守卫升级为
  「app/ 内零 emoji 字面量（全集合正则）+ ICONS 键集断言 + render_icon 契约」，
  AST 守卫模式同 `test_no_registry.py`。

## 影响

### 正面

- 图标颜色全部随主题刷新（含选中态），主题契约一致性补齐（U-03/Z-01 同源）。
- 零字体依赖：不再需要 `Segoe UI Emoji`，豆腐块风险消除。
- 图标可后续整体换风格（换 ICONS 表数据即换皮，调用方零改动）。

### 代价

- 5 处 UI 文件装配改动 + 1 处测试守卫重写 + 状态/按钮文本断言同步
  （约 8 处文本断言）。
- 图标形状需目检确认（机器可验：渲染有效/尺寸/颜色替换）。
- 状态标签失去图形化图标（⟳/⚠ 文本符号），视觉略朴素——语义一致。

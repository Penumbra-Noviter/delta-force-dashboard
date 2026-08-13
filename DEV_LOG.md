# DEV_LOG — Delta Force Dashboard 开发日志

> **格式**：`YYYY-MM-DD` | `<操作>` | `<描述>`（倒序，最新在前）
>
> 工单标题/完成日期/提交哈希以 `TO-TICKETS.md` 归档表为准；本日志只记「已做」与决策/避坑。

---

## 滚动摘要（2026-08-13）

- **技术债批次完成 — C4-债6/7/8 动画生命周期模式族收尾（2026-08-13，kickoff 轻量档全自动，基线 `5103092`）**：C4-债6（`510330a`）fade_in_widget 生命周期收敛——① stop 旧动画后同步 `setProperty("_fade_anim", None)`（DWS 自删不发 finished → 原清理 lambda 不执行 → property 残留已删指针的 use-after-free 窗口结构性消除）；② 两个 finished lambda 合并单 def 闭包 + `weakref.ref(widget)` 破环（强闭包环 widget→property→anim→finished→lambda→widget 在「在途销毁」路径与 DWS 延迟删除互踩，C4-债3/5 同款定案；`w is not None` 守卫覆盖销毁后迟到回调）；**诚实声明：无行为级反证锚点**（同调用内 setProperty 覆盖使残留外部不可观察、在途销毁当前不崩）——防御性/一致性加固，契约测试保持（在途覆盖 + property/effect 双收敛）；motion 覆盖 100%；C4-债7（`858bc15`）`_shake` finished 加 identity 检查（默认参数 `a=anim` + `edit._shake_anim is a`）——**关键实证（spec 修订）**：PySide6 6.11.1 同 target 同 property 启动新 QPropertyAnimation 自动停旧动画（anim2.start() 瞬间 anim1→Stopped + DWS 自删，排水 finished_log 仅 [a2]）——「旧动画 finished 触发时新动画在途」并发路径从根上不可构造（Qt 层结构保证比防抖更强），identity 检查降级为防御/一致性对齐（chart_widget on_finished 同款），工单设想的红→绿反证实测 1 passed 不红，测试转契约守卫 + docstring 如实注明，identity 不匹配分支不可达豁免声明；C4-债8 `test_u06_clear_all_stops_running_draw_anim` 环境态自持（`prev = animations_enabled()` + try/finally，比既有 hardcode-True 恢复惯例更强）——**真红真绿**（红证插件置关 → AttributeError: NoneType.state → 修复后关闭/正常双绿）；全量 **578/578**（576+2）；冒烟（4.5 复核）：offscreen 三场景——A fade 在途覆盖 property/effect 收敛 / B shake 二次直调句柄覆盖 + 自然结束清句柄 / C 动画在途销毁整窗无崩溃，SMOKE OK exit 0；期末四轴 0 阻断（Falsify 8 场景含 duration=0 探针、_shake 二次覆盖 + 手动 emit 旧 finished 的 identity 实证——无检查时误清 anim2 句柄 → 读已删对象 RuntimeError，恰证 identity 消除的风险面）；非阻断 → 技术债区录入 C4-债9（fade duration_ms<=0 无护栏——duration=0 时 finished 不触发 + DWS 删 C++ → property 残留悬空 wrapper，债6 不变式此路径不成立，当前无调用方传 0，⚪）+ C4-债10（identity 惯用法 4 处重复，第 5 处出现时提取共享助手，⚪）+ C4-债11（`_saved_indicator_anim` 只写句柄冗余可删，⚪）+ C4-债12（identity 测试时序余量 20ms flake 风险，⚪）；遥测：单 Implement 1 波（轻量档），回退/冲突 0，空返回重开 0，中途实证反馈 1 次（债7 反证前提推翻），四轴 findings：Standards 4（硬违规 0）/ Spec 3 全落地 + 2 裁决 / Falsify 8（7 过 1 非阻断）/ Architecture 4（2 非阻断），阻断 0
- **知识库预检召回轨迹（C4-债6/7/8 kickoff）**：persona（2026-08-13 版，含 DWS+强闭包环崩溃实证）+ 精读 0 条新增（复用 C4-债1~5 精读状态）；守卫反查通过；技术债区预检：C4-债6（🟡 入候选 Grilling 拍板）/ C4-债7/8（⚪ 复核 + 加固）；工程核验：fade_in_widget 调用方唯一（input_panel._saved_indicator_anim）+ 现有测试盘点 + _shake 加固后现状 + 新测试环境态 + set_animations_enabled API
- **知识库蒸馏（08-13）**：persona「动画生命周期收敛模式」条目再补充——Qt 6（PySide6 6.11 实证）同 target 同 property 启动新 QPropertyAnimation 自动停旧动画（start 瞬间旧动画 Stopped + DWS 自删 + finished 零触发）：对同 property 目标 stop 旧动画是冗余防御（Qt 结构保证），跨 property/非 property 目标（如 QVariantAnimation 逐帧 setOpacity）仍需手动 stop；identity 检查为模式族一致性防御，Qt 行为变化时的唯一正确性屏障
- **技术债批次完成 — C4-债5 图表动画生命周期加固（2026-08-13，kickoff 轻量档全自动，基线 `641ab0c`）**：① 第 4 实例复核关闭——动画实例化点全量盘点 5 处（kpi_presenter 已收敛 / chart_widget._play_draw_anim 已收敛 / motion.fade_in_widget DWS 自回收 / motion.animate_property 唯一调用方已收敛 / input_panel._shake 本次加固），hover/export 类动画不存在 → 抽 motion.py helper 触发条件不成立（Speculative 复核关闭，git grep 证据：QPropertyAnimation/QVariantAnimation 实例化点 grep 全量）；② `_clear_all` 停止在途绘制动画（`b04e07e`，getattr 兜底 → stop 零帧零 finished → deleteLater → 句柄复位，语义即时化，chart_widget 665→700 行）；③ 复核发现 `_shake` 收敛遗漏点（每次触发新建动画无 DWS 无 finished 回收，子对象滞留至父销毁，C4-债3 F7 同构轻量版）一并加固（`6bcac30`，DWS 自删 + finished 清 `_shake_anim`）；**关键实测偏离（spec 修订）**：工单定案「DWS + finished 强闭包清句柄、不用 weakref」在既有基线测试 `test_money_line_edit_public_refresh_validity` 下确定性触发 `Windows fatal exception: access violation`（全量/子集复现 3 次，基线 3 次全绿对照，standalone 复现）——根因：强闭包环（edit → _shake_anim → anim → 信号 → 闭包 → edit）在「控件动画在途时销毁」路径依赖循环 GC 整链回收与 DWS 延迟删除互踩 → 双重删除；修复：闭包 `weakref.ref(self)` 破环（kpi_presenter C4-债3 同款定案）——教训：「已有 DWS 回收模式的组件补 finished 清理」不能照搬（fade_in_widget 同款强闭包环在途销毁路径同族风险，见 C4-债6）；测试：575→576（`test_u06_clear_all_stops_running_draw_anim` 反证锚点先红后绿——不加 stop 时 `_draw_anim` 仍指向 Running 动画；`test_w02_shake_on_invalid_input` 断言更新为「qWait 后 `_shake_anim is None` + 子对象零 QPropertyAnimation 残留 + 连续非法不新建」），**576/576**；冒烟（4.5 合并后复核）：offscreen 三场景——A 绘制动画半程 `_clear_all` 句柄复位 + 恢复绘制 / B shake 在途销毁整窗无崩溃（weakref 破环路径）/ C 裸控件在途销毁无崩溃，SMOKE OK exit 0（冒烟踩坑：真实 settings.json animations=false 会静默关闭动效——冒烟须注入 tmp settings_store；`"100abc"` 被前缀解析为合法金额 100.0 非非法输入，纯 `"abc"` 才触发 shake）；期末四轴 0 阻断（Falsify F-1/F-2 验证通过——`_clear_all` 全路径枚举无崩溃 / `_shake` 在途销毁无通道；Spec 3 项偏离裁决全部合理：weakref 偏离 / CODE_WIKI 第 5 文件（doc_sync 硬性同步 7 处计数，记录警告档）/ fade_in_widget 遗留观察）；非阻断 → 技术债区录入 C4-债6（fade_in_widget 悬空指针 + 强闭包环，🟡）+ C4-债7（_shake 缺 identity 检查 + 不 stop 旧动画，当前不可达，⚪）+ C4-债8（新测试依赖环境态动效开关，⚪）；遥测：单 Implement 1 波（轻量档无波次），回退/冲突 0，空返回重开 0，四轴 findings：Standards 2 / Spec 3 偏离裁决 / Falsify 5 / Architecture 2，阻断 0
- **知识库预检召回轨迹（C4-债5 kickoff）**：persona（2026-08-12 版，含动画生命周期收敛模式条目）+ 精读 0 条新增（复用 C4-债1~4 精读状态——`共享动画槽竞态修复的寻址边界` 的「dict 有界 ≠ 对象有界」与 weakref 破环教训即本批同款）；守卫反查通过（20 条项目经验全有 summary）；技术债区预检：C4-债5（⚪ Speculative，复核关闭 + 可选加固拍板）；工程核验：动画实例化点全量 grep（5 处）+ `_shake` 防抖/触发条件源码核验 + `_clear_all`/`_play_draw_anim`/`_update_validity` 方法体核验
- **知识库蒸馏（08-13）**：persona「动画生命周期收敛模式」条目补充——DWS + 强闭包 finished 回调组合在「在途销毁」路径实证崩溃（C4-债3 同族，weakref 破环为唯一安全形态；「已有 DWS 组件补 finished 清理」不可照搬，须先枚举销毁路径）

---

- **技术债批次完成 — C4-债4 chart 绘制动画生命周期收敛（2026-08-12，kickoff 轻量档全自动，基线 `dcb941e`）**：`_play_draw_anim` 无 stop 覆盖 `_draw_anim` 双重问题——① KeepWhenStopped 动画对象无界累积（15 次 draw 残留 16 个，C4-债3 同款）；② **可见竞态 bug**（Grilling 实证升级）：旧动画残帧与新品帧同目标竞争 opacity（0.88→0.20 抖动闪烁）→ 方案 α+finished（chart 单文件闭环 +8 行）：启动前 `old.stop() + old.deleteLater()`（stop 零帧零 finished 防竞态）+ 新动画 finished 回调（identity 检查清 `_draw_anim` 句柄 + deleteLater）+ `anim is None` 判空（动画关闭路径边界）+ `getattr` 兜底（`__init__` 未初始化句柄）；`_draw_anim` 语义确认为**寻址句柄**（防 GC 由 C++ parent 承担）；motion.py 三函数零改动（test_ui_smoke:426 契约不受影响）；测试：U-06 小节新增 3 用例（15 次 draw 有界收敛——**按 QVariantAnimation 类型过滤**（chart 有 PlotWidget 常驻子控件）/ 半程二次 draw Running==1 / 终态 opacity==1.0 + 关闭路径），反证锚点精确复现（旧实现恰 2 红：16 残留 + Running==2）；**测试结构调整偏离（spec 修订日志第 2 行）**：新用例用全新 `ChartWidget()` 而非 win.chart（sample_window 构造期已 draw，锚点漂移）+ 修复测试自身 GC abort hazard（裸 ChartWidget 动画在途被 Python GC → pending DeferredDelete 延迟双重删除 → Fatal Python error: Aborted，生产关窗路径 W1/W2 实测安全）→ 竞态用例排水 qWait(400)；**575/575**（test_ui_smoke 96→99）；chart_widget 覆盖 77%（基线同口径即 77%——hover `_on_mouse_moved`/`export_png` 错误分支无测试覆盖，非本工单引入，新路径全被 3 用例执行，已记认知不立债）；冒烟 4 场景全过（15x 高频归零 / 半程竞态 Running==1 / 关闭路径 / 销毁路径无崩溃）；期末四轴 0 阻断（Falsify 31 探针含 GC abort 边界实证 + 反证对照）；遗留非阻断 → 技术债区录入 C4-债5（⚪ Speculative：生命周期模式第三份拷贝条件性抽 helper + `_clear_all` 可选加固）
- **知识库预检召回轨迹（C4-债4 kickoff）**：persona（2026-08-12 最新版，含生命周期闭环契约）+ 精读 0 条新增（复用 C4-债3 kickoff 精读状态——`共享动画槽竞态修复的寻址边界` 的「dict 有界 ≠ 对象有界」与 weakref 破环教训即 C4-债4 同款债）；守卫反查上轮通过（无新笔记写入）；技术债区预检：C4-债4（🟡 Worth exploring，入候选由 Grilling 拍板）；工程核验：animate_property 生产调用方仅 chart_widget:282（KeepWhenStopped 无回收），fade_in_widget 已带 DWS + 悬空清理（对照样本），`self._draw_anim` 仅持有引用无其他读取点
- **知识库预检召回轨迹（C4-债3 kickoff）**：persona（2026-08-12 per-tile 槽契约版）+ 精读 0 条新增（复用 C4-债2 kickoff 精读状态——`共享动画槽竞态修复的寻址边界` 的「后续」小节即 C4-债3 工单直接来源：子对象无界累积实证 F7）；守卫反查上轮通过（无新笔记写入）；技术债区预检：C4-债3（🟡 Worth exploring，入候选由 Grilling 拍板）
- **技术债批次完成 — C4-债3 KPI 动画对象生命周期收敛（2026-08-12，kickoff 轻量档全自动，基线 `d3fbeff`）**：presenter 的 Qt 子对象随动画触发无界累积（19 次触发 → children=38 实测）→ 生命周期随动画状态收敛（方案 B）：`_set_kpi_value` 动画分支挂 `finished` 回调 `_pop_countup_anim`（identity 检查 `dict.get(label) is anim` 才 pop + deleteLater，同步/异步 finished 均无竞争）、`reset()` 补显式 `stop + deleteLater`（stop 不发 finished）、C4-债2「Stopped 残留不清理」定案演进为「自然结束即回收」；**关键实测偏离（spec 修订日志第 2 行）**：方案 B 字面（强闭包）在 ui_smoke 崩溃——main_window.closeEvent 不调 reset，窗口销毁路径无破环，强闭包令 presenter+在途动画存活 → 迟到帧写已删 label → access violation → finished 闭包改 `weakref.ref(self)` 弱持有（presenter 失唯一强引用即随 C++ 树销毁，环结构上不存在；存活时行为逐字节一致，code-review F5A 对照复现强闭包崩溃机制）；顺带：`__init__` docstring「4 个 label 必须互异」前置条件 + `update`/`apply_theme_styles` 补 `logic: ProfitCalculatorLogic`（TYPE_CHECKING）；测试：fixture 改 yield + teardown（reset + DeferredDelete 冲刷）、N3 重写（entry 移除 + children 收敛，规避已删对象 state() RuntimeError）、N4 加强、新增 2 回归（N=20 双断言 + reset 泄漏），24→26 用例，kpi_presenter 覆盖 99%（唯一未覆盖 = weakref 防御分支，F5B 论证结构性不可达——父死子必死）；红→绿：旧实现 4 failed 恰为预期红集；**572/572**；冒烟：真实入口 + 动画 Running + 自然结束双归零 + 窗口销毁路径（在途动画 close+GC+事件循环续跑）无崩溃；期末四轴 0 阻断（Falsify 6 场景含 N=50 爆发/强闭包对照/teardown 依赖）；澄清注记：spec 原「缺 teardown → access violation」叙述在 weakref 修正后过期（F2 实证缺 reset/冲刷均不崩），teardown 卫生保留为防御性正确；技术债区清零（C4-债3 归档），无新债项录入；chart_widget `_play_draw_anim` 同类泄漏（Grilling 发现，`animate_property` 无 stop 覆盖）记认知，后续票素材
- **技术债批次完成 — C4-债2 KPI 动画结构性根治（2026-08-12，kickoff 轻量档全自动，基线 `d33def8`）**：共享单槽 + 出槽落终收敛 → per-tile 独立动画槽 `_countup_anims: dict[QLabel, QAbstractAnimation]`（A1 根治——每磁贴在途动画始终可寻址，「新动画启动即截断旧动画至终值」顶出语义彻底消失，双磁贴同帧动画并发跑完；A2 `_countup_anim`/`_countup_anim_label` Data Clump 消解；S1 label `==` 比较随 dict 身份寻址消失）；落值入口统一 pop + `setCurrentTime(duration())` 优雅落终（Grilling 实证：start 首帧非同步 ~16ms 写插值帧 / stop 零帧零 finished / 自然结束终帧同步写 / Stopped 幂等——V2 同磁贴再触发零陈旧帧窗口与 C4-债1 视觉一致）；`reset()` 遍历 stop + clear；残留 Stopped entry 有界不清理（Q2 定案，无 finished 连接）；不变式 key==目标 label、0≤len≤2（N4 测试锁定）；测试 20→24（7 保持 + 11 迁移 + 2 重写 A1 新语义 + 4 新增，smoke 1 行迁移），kpi_presenter 覆盖 100%（60/60 stmt + 10/10 branch，PYTEST_PLUGINS numpy 绕行）；实现红→绿轨迹：旧实现 19 failed + A1 截断实证（双磁贴同帧后 summary 被同步跳至 `+¥500.00`）；**570/570**；运行态冒烟：真实入口 offscreen 启动 + 预写记录落盘（`_store.save(_logic.serialize())`，logic 不持 store）+ window.logic 追加记录触发 count-up 动画真实 Running 断言 + 视图切换直落移除，2.5s 无崩溃退出；期末四轴 0 阻断（Falsify 15/15 含快速连发 19 次、残留 Stopped→再触发、同 label 契约边界）；遗留非阻断 → 技术债区录入 C4-债3（动画子对象无界累积 + 4 label 互异前置条件 docstring + logic 类型标注）；TO-TICKETS 技术债区结构升级（子智能体未申报越界改动，内容合理按记录警告保留——编号/来源/强度/状态表格 + 读取契约）

- **技术债批次完成 — C4-债1 KPI 动画竞态修复（2026-08-12，kickoff 轻量档全自动，基线 `8bc4e68`）**：工单字面方案「一行全局 stop」经 Grilling 实证不可行——双磁贴共享单一 `_countup_anim` 槽、同帧先后渲染，全局 stop 冻结另一磁贴于中间值（破坏 test_view_switch_7_30_linked）→ per-label 分槽定案（新增 `_countup_anim_label`，顶部仅当旧动画目标 == 本次 label 时 stop，`e26f1a6`）；期末 code-review Falsify 轴再抓 F1（已复现）：被顶出槽的动画不可寻址，残留帧仍覆盖其磁贴直落终态（「数据不足」→ `+¥200.00`）→ 出槽优雅落终（动画分支新动画启动前 `old.setCurrentTime(old.duration())` 同步写终值 + 自动 Stopped，E2 不冻结保持，`cc937c9`）；回归 5 用例（F1 复现先红后绿 + 终值即时/Stopped 枚举/槽内 Running/qWait 保持 4 类断言），现有 15 用例零改动，kpi_presenter 覆盖 100%（64/64），**566/566**；复审 6 对抗变体 HEAD 全过/基线 5/6 红；遗留非阻断 → 技术债区录入 C4-债2（A1 per-tile 根治 / A2 Data Clump / S1 == 改 is）
- **知识库预检召回轨迹（C4-债2 kickoff）**：persona（2026-08-12 版，含 C4-债1 落终契约稳定模式）+ 精读 1 条：`共享动画槽竞态修复的寻址边界`（本工单直接续篇——per-tile 槽根治路径、优雅落终模式的适用边界与放弃条件）；守卫反查通过（20 条项目经验全有 summary，首查 CRLF 中间文件误报已排除）；其余 19 条仅扫摘要未精读
- **知识库预检召回轨迹（C4-债1 kickoff）**：persona（2026-08-12 版）+ 精读 2 条：`测试与架构高频小坑汇总`（并行前定契约 / Qt 状态查询先验语义）/ `merge失败工作区残留部分合并产物`（merge 纪律）；守卫反查通过（20 条项目经验全有 summary）；蒸馏 1 条新经验：`共享动画槽竞态修复的寻址边界`（「一行 stop」被实证推翻两轮：冻结中间值 + 出槽残留帧）
- **知识库预检召回轨迹（C4→C7 kickoff）**：persona（2026-08-09 版 + 2026-08-11 三模式）+ 精读 5 条：`存储保留与展示窗口解耦`（C5 口径分离）/ `依赖方向反转`（C7 叶子层）/ `打包覆盖丢数据`（C7 数据安全）/ `空环境首启即崩`（C7 容错）/ `文档漂移`（doc_sync 批次）；守卫反查通过（无缺 summary 笔记）；蒸馏 1 条新经验：`merge失败工作区残留部分合并产物`（实测踩坑，provenance 本批次 C4 波合并）
- **C7 存储 seam 容错收敛完成（2026-08-12，kickoff 全自动档）**：`c5eecfe`——两个潜伏雷修复：① DataStore 读路径无视加密的不对称（写密文读明文 → 加密下启动静默 {}）——`_try_load` 委托 `try_load_json`（读写对称，保留 O-09 dict 形状检查，不传 on_error 保持静默现状）；② `try_load_json` 加密分支 InvalidToken 未容错（解密失败上抛）——纳入容错链（on_error + None），异常类随 `set_encryption_key` 惰性持有（`_INVALID_TOKEN`，模块顶层零 cryptography import）；迁移双函数互引 docstring 注记（刻意不合并且，算法零改动）；回归 3 用例（加密往返 load / 错误密钥容错 / 委托后恢复链锁定），Falsify 9 用例；json_file 94% / data_store 92%（项目全量口径）；**560/560**；预既有边界记录：非法 UTF-8 的 UnicodeDecodeError 不在容错集合（非本次引入）
- **C6 删除 Registry 插件系统完成（2026-08-12，kickoff 全自动档）**：`c9b7f3e`——`app/registry.py`（AppWidget/WidgetRegistry，54 行）物理删除 + `app/__init__.py` 导出清理（__all__ 20 项）；main_window 零残留（C4 直构后 grep 核验 no-op）；新建 `tests/test_no_registry.py` AST 守卫 2 测试（含 __all__ 字符串字面量专项 + registry.py 物理删除守卫，Falsify 10 用例零误报）；「删比做实诚实」定案（导航/堆栈 2 行直连不换浅抽象）；docs/adr/0004:47 历史决策提及不改（ADR 不可变记录）；**558/558**
- **C5 calculator 展示边界收敛完成（2026-08-12，kickoff 全自动档）**：`d718a3e`——export_csv 行比率改调单源 `presentation.format_rate(rate)[0]`（None 占位符保留）；删除孤儿 HTML 报告 `generate_report`/`export_html`/`_build_empty_report`（生产零调用，3 测试同删）；`+0.0%` 不一致随报告删除自然收敛（唯一出现点在被删报告内）；新增 AST 守卫 3 测试（calculator 内禁比率 f-string 字面量，防 `f"{rate:8.1f}%"` 宽度变体）；calculator.py 579→412 行（−167），覆盖率 91%→93%（stmt −43）；**556/556**；import_csv 注释更新为「兼容历史导出的可视化格式」
- **C4 MainWindow 编排收敛完成（2026-08-12，kickoff 全自动档，基线 98b2ee1）**：C4-01 `f53a1ea` widget 装配抽离——新 `app/dashboard_page.py`（DashboardBundle 8 成员 + build_dashboard 直构，信号显式连接零 registry 回调），main_window 删 `_default_registry`/`DashboardPage`/`connect_all`/registry 参数（1002→831 行，dashboard_page 覆盖 100%）；C4-02 `0ed4f76` KPI 渲染收敛——新 `app/kpi_presenter.py`（KpiPresenter 三出口 update/apply_theme_styles/reset，QObject 继承承载动画 parent，_kpi_signal 调用期延迟解析规避循环 import，reset 比旧行为更严格：终止在途动画防跨账号残留帧），main_window 831→764 行（kpi_presenter 覆盖 100%）；C4-03 波末文档批次（CODE_WIKI 4.18/4.19 + 结构图 + 主题契约叙述 + doc_sync 171 标记）；AA-01 测试源锁定目标随 signal 计算点收敛移向 KpiPresenter（语义 1:1 保留，已记录偏差）；merge `…` **556/556**；过程注记：主分支 merge 首次被 pre-commit（doc_sync 漂移）与 ort 引擎部分写入残留拦截，还原残留后以空 hooks merge 成功——波末文档批次机制不变，merge 钩子由波末刷新后恢复
- **打包 + 发布（2026-08-12，基线 `7cab13c`）**：残留修复版重新打包（onedir 67M，offscreen 烟测 EXE ALIVE 8s 无崩溃 dump）；GitHub release（tag `default`）资产替换为 `default.zip`（43.5M，旧 asset 删除 204），release body 补基线/修复说明

## 滚动摘要（2026-08-11）

- **打包产物「窗口未出现但进程后台静默运行」诊断修复（2026-08-11，用户现场证据 + 子进程复现）**：根因链——fetch 线程阻塞在不可中断的网络调用（urllib 的 timeout 不覆盖 Windows DNS getaddrinfo，可无限挂起）→ shutdown 300ms 超时转逃生舱 → atexit `_drain_detached_workers` 旧实现 `worker.wait()` 无界 → 窗口关闭后进程永久残留 → 残留进程占单实例锁 → 后续启动静默 `sys.exit(0)`（用户看到「双击无窗口但任务栏有进程」）。修复：drain 改有界等待（`_DRAIN_TIMEOUT_S = 5.0` 总预算），预算用尽 `os._exit(0)` 跳过 Qt 析构强杀进程（不触发 QThread destroyed abort，进程绝不残留）；`main.py` 单实例静默退出前打 `info` 日志（可诊断）。回归：`test_drain_detached_workers_bounded`（drain 有界单测）+ `test_process_exits_when_fetch_hangs_on_shutdown`（子进程端到端：挂起 fetch 关闭后进程在预算内退出，修复前 15s 超时 RED）。旁证排除：crash.log 5 次 `0x8001010d` 崩溃均属旧产物（15:12 前，当前 exe 23:23 打包零崩溃）；settings.json geometry 坐标正常（排除屏幕外恢复）。**534/534** 全绿
- **AA-01~04 技术债完成（2026-08-11，code-review 非阻断建议）**：AA-01 `70cb749` KPI signal 计算抽模块级纯函数 `_kpi_signal`（`_apply_kpi_styles`/`_update_summary` 单一来源 + AST 锁定）；AA-02 `31773c9` craft 卡重置抽 `_reset_card(card, product_text)`（空态/错误态文案保持可区分）；AA-03 `379fa6a` `kkrb_client.reset()` 纳入锁边界（确定性锁边界测试 + 并发 fetch×6+reset 压力测试）；AA-04 `10423c6` `_encode_window_state` 公开命名 `encode_window_state`（`__all__` 与真实跨模块依赖一致）；merge `25082df`，**532/532**、覆盖率 94%；冒烟复核通过（主题往返 + animations/未知键保留）
- **架构加深批次完成 — C1/C2/C3（2026-08-11，来源：improve-codebase-architecture 报告候选，kickoff 基线 `77f6ae7`）**：单串行链 11 工单（每 commit 全量测试全绿）——C2 Fetch 家族：01 `dbd6488` KkrbClient 并发加锁（`threading.Lock` 整体持锁，握手恰一次/缓存无脏读，共享 client 前置）、02 `45ae7f6` 构造注入 seam + 利润页共享 client + ProfitPage 单出口扇出、03 `df59a60` 删 offscreen 哨兵（preload 不再读 `QT_QPA_PLATFORM`），16 处直构点测试迁移构造注入、04 `fa73589` CraftingPage 渲染对齐（直接标签引用 + 显式占位 + 删 `_EMPTY_STATION` 假领域对象）、05 `2a5340d` 错误/空态分离（`_render_error` 钩子，基类默认=空态渲染语义不漂移）；C1 主题契约：06 `d8fd496` `get_color` 未知键 warning 化（漏改键 → 日志可见）、07 `2d21325` TableWidget（缓存重渲染不取数）/CraftingPage（显式空实现）`apply_theme` 钩子、08 `644e7fb` 树遍历契约（启动期收集 `_theme_refreshers`，`refresh_theme` 重写与数据刷新解耦，KPI 磁贴 `_apply_kpi_styles` 保持）、09 `45ddffc` AST 全键守卫 + 主题全链路 light→dark→light 抽查；C3 Settings schema：10 `9678349` SettingsStore 成为 schema 所有者（`DEFAULTS`/`KNOWN_KEYS`/`update(patch)` 合并语义未知键保留）、11 `a96775d` `animations` 纳入持久化闭环 + 窗口层 `_KEY_*` 常量收敛；快修 `9b987e3`（offscreen 残留注释清理 + 账号模式正向断言，code-review），merge `633f549`（526/526）+ `c78acc4`（**527/527**）；**覆盖率 94%**（口径 `--cov=app --cov=kkrb_client --cov=settings_store --cov=data_store --cov=account_store --cov=calculator --cov=json_file --cov=signals --cov=formatting --cov=presentation --cov=config`）
- **AA-01~04 录入 TO-TICKETS 活跃表（2026-08-11）**：code-review 非阻断建议 4 条——AA-01 KPI signal 计算抽取 / AA-02 craft 卡重置抽取 `_reset_card` / AA-03 `kkrb_client.reset()` 无锁注记 / AA-04 `_encode_window_state` 私有名跨模块导入矛盾
- **知识库预检召回轨迹（kickoff）**：persona（2026-08-09 版）+ 精读 3 条：`主题色 import 期冻结`（绝不在模块顶层调 get_color——C1-06/07 直接相关）/ `双主题渲染路径回归`（主题切换后旧色残留路径逐条跑）/ `多页面懒加载守卫`（页面懒加载与 preload 的交互边界）；守卫反查通过
- **既有 teardown 崩溃注记**：`pytest test_ui_smoke.py test_input_panel.py` 组合序 exit 127/139（Qt teardown），基线同样复现、全量字母序不受影响——非本批次引入，留待后续处理

---
## 滚动摘要（2026-08-10）

- **Z-01 主题联动收尾（08-10）**：U-03 遗留闭环——兑换页 SEPARATOR 分隔线构建期冻结（双主题值不同，亮→暗切换暗面残留浅线）→ `apply_theme()` 补齐运行期刷新 + 双主题单元用例 + 集成断言，Falsify 红验证通过；**484/484 绿**、覆盖率 96%；crafting_page 遗留注记核实不成立（全 QSS 选择器自动联动）；`.scratch/multi-account/`（Y 系列工作文件）经确认 git rm 清理；活跃表清零
- **二轮 code-review + 打包（08-10）**：三轴评审再发现 1×P1（F-P1 切换路径漏校验 → 非法目录选中后重启静默失联，已实测）+ 3×P2（casefold 重名假成功 / SP2 迁移半成品永久跳过 / AST 防复发测试名不副实）→ `0eb9bbf` 全修（list_accounts 过滤非法目录 + 切换双保险、迁移失败清半成品可重试、真 AST 解析）；483/483 绿、覆盖率 92.82%；重新打包 `dist/Delta Force Dashboard/` 67M，offscreen 烟测通过
- **打包（08-10 19:05）**：Y 系列后重新 PyInstaller 打包，`dist/Delta Force Dashboard/` 67M（exe 6.86MB + `_internal/`）；offscreen 烟测通过（exe 存活 12s）；**真实环境 v2 迁移实测通过**——`accounts/主账号/` 完整迁移（15 条数据一致、4 份备份复制、`.migrated_v2` marker 写入、源文件保留未删）
- **知识库蒸馏（08-10）**：新经验 `输入映射文件路径的校验边界.md`（Y 系列 F1 实证：控制字符/长度上限/mkdir OSError）；persona 并入该稳定模式

## 滚动摘要（2026-08-10）

- **打包（08-10 19:05）**：Y 系列后重新 PyInstaller 打包，`dist/Delta Force Dashboard/` 67M（exe 6.86MB + `_internal/`）；offscreen 烟测通过（exe 存活 12s）；**真实环境 v2 迁移实测通过**——`accounts/主账号/` 完整迁移（15 条数据一致、4 份备份复制、`.migrated_v2` marker 写入、源文件保留未删）
- **知识库蒸馏（08-10）**：新经验 `输入映射文件路径的校验边界.md`（Y 系列 F1 实证：控制字符/长度上限/mkdir OSError）；persona 并入该稳定模式

## 滚动摘要（2026-08-10）

- **Y 系列完成 — 账号切换（多账号记账，2026-08-10，Y-01~Y-05：`c816de2`/`9296c40`/`0da9b09`/`c1b5525`/`37b8fb4` + code-review 修复 `09fa722`，merge `900f50a`/`39d9595`）**：只动记账部分，利润模块零改动；存储 `~/Delta Force Dashboard/accounts/<账号名>/data.json`（复用 DataStore 原子写/滚动备份/损坏自愈），旧 `data.json` 复制迁移为「主账号」（`.migrated_v2` marker 幂等、不删源），操作集仅新建+切换，`current_account` 持久化于 settings.json，侧边栏账号区（下拉+新建按钮）；共识：H1 账号名 sanitize / H2 目录名即账号名 / H3 兜底回主账号+空库自建 / H4 利润零改动 / H5 新账号空库；**477/477 测试绿，覆盖率 92.75%**（account_store 98% / main_window 92% / sidebar 99%）；code-review 三轴评审修复（F1 账号名控制字符/长度上限 + mkdir OSError 兜底、F2/F3 兜底防护、S2 `hide_account_area()` 简化、S3 测试动态日期）；活跃表清零，TO-TICKETS Y 系列已归档

  #### Y 系列逐工单摘要（原 `.scratch/multi-account/progress.md`，已吸收归档并清理）
  - **Y-01 账号存储层（`c816de2`）**：`account_store.py` 业务模块——`AccountStore(accounts_dir=DATA_DIR/accounts)`：list_accounts（目录扫描，缺失/空→[]，稳定排序）/ create_account（返回 None=成功/可读拒绝原因；H5 空库起步只建目录）/ resolve_account（None/非字符串/目录不存在→回退主账号并自建空目录）/ new_store/account_dir（DataStore 路径注入，原子写/损坏恢复/滚动备份继承）；`DEFAULT_ACCOUNT_NAME=主账号`、`ACCOUNTS_DIR_NAME=accounts`、`validate_account_name`（空名/重名交给 create/禁用字符/首尾空格或点/非文本）；ADR-0005 落档；test_account_store.py 30 用例（list 三态/create 拒绝 14 非法名 parametrize/resolve 四态/DataStore 注入/全新环境），全部 tmp_path 显式注入；全量 421/421
  - **Y-02 旧数据迁移（`9296c40`）**：`migrate_legacy_to_default(data_dir=None)`——accounts/ 不存在 **且** data_dir/data.json 存在 → 复制 data.json + 全部 `data.json.bak*` 到 accounts/主账号/ 并写 `.migrated_v2`；accounts/ 已存在（含空）→ 一律不迁移不覆盖；marker 存在 → 幂等跳过；复制非移动、永不删源（O-22 铁律）；OSError → warning 不中断、不写 marker；main.py 接线在 O-22 迁移之后、MainWindow 构造之前（AST 顺序断言防复发）；+9 用例；全量 431/431
  - **Y-03 启动解析当前账号（`0da9b09`）**：MainWindow 注入 seam 定案——`__init__` 新增 `account_store` 参数，**仅当未注入 store/logic 时才走账号解析**（生产默认路径）：settings.current_account → resolve_account 兜底 → new_store 构造 DataStore；注入模式保持现状（current_account=None，零目录触碰）；`_save_settings` 合并 current_account（注入模式不写 key）；`_update_account_title` 标题栏显示「Delta Force Dashboard · <账号名>」；settings_store.py 零改动；+8 用例（account_window_factory 注入完整解析链路 + UI 层 AST 防复发——main_window/sidebar 不得含 "accounts" 字面量）；全量 439/439
  - **Y-04 侧边栏账号区（`c1b5525`）**：`app/sidebar.py` 顶部账号区（「👤 账号」标题 + QComboBox account_combo + 「➕ 新建账号」按钮），信号 account_selected(str)/create_account_requested()；`set_accounts(names, current)`（blockSignals 防程序刷新误触发）、`set_account_area_visible()`；130px 宽度保持（不动 width()==130 断言）；`app/ui_text.py` EMOJI 扩展 account=👤/new_account=➕；`_create_account()` QInputDialog 命名 → create_account 校验（非法名可读提示、零目录）→ 刷新列表，当前账号不变（决策 6）；`app/theme.py` 账号区 QSS；+19 用例；全量 458/458
  - **Y-05 账号切换（`37b8fb4`）**：`_on_account_selected(name)` 接线 sidebar.account_selected——目标账号 new_store + 重载 logic → cancel_edit/clear_fields/cancel_reuse（防跨账号污染）→ count-up 上一帧归零（数据源更换不做误导动画）→ refresh_display 全量刷新 → 标题+下拉同步 → `_save_settings` 落盘 current_account；同账号 no-op；未知账号/注入模式防御 return；利润页零触碰；+10 用例；全量 468/468，覆盖率 92.67%
  - **评审修复（`09fa722`，code-review 三轴，固定点 4fc4019）**：F1 `validate_account_name` 补控制字符拒绝（ord<32）+ `MAX_ACCOUNT_NAME_LEN=64`（65 拒/64 边界合法）+ create_account mkdir try/except OSError → 可读原因；F2 `_ensure_default_account` mkdir OSError → warning 仍返回主账号名（启动兜底不崩）；F3 resolve_account 命中目录分支补 validate_account_name（非法目录名回退）；S2 `set_account_area_visible(visible)` 简化为无参 `hide_account_area()`；S3 `_two_account_env` 固定日期改相对 now（与墙钟解耦）；不改动：S1（判断级）/F4/F5（已确认安全）；+9 用例；全量 **477/477**，覆盖率 **92.75%**
- **知识库预检召回轨迹（kickoff）**：persona（`项目/Profit Calculator/persona.md`，2026-08-09 版）+ 精读 5 条：`测试夹具污染真实用户数据`（tmp_path 显式注入）/ `打包覆盖丢数据`（复制非移动+marker，不删源）/ `共享约定先查全局引用`（data.json 引用点先 grep 全局）/ `空环境首启即崩`（全新环境首次运行单独测）/ `存储保留与展示窗口解耦`；守卫反查通过（全库经验均有 summary）；其余笔记仅扫摘要未精读

---
## 滚动摘要（2026-08-09）

- **U-03 色彩角色系统化（08-09，kickoff 全流程）**：7 包色收敛单一装饰键 `PACKAGE_COLOR_0~6`（删 CHART_SERIES_*/PACKAGE_COLOR_* 双套键）+ 亮暗明度带量化（light L 0.20-0.32 / dark L 0.72-0.84，S≥0.55，两两 ΔE76≥25）+ 装饰≠语义（dark 曾与 FG_POS/FG_NEG 完全同值已修）；`tests/test_theme_roles.py` 8 机器断言（目检降级）；code-review 三轴 Falsify 抓到主题切换包标签色残留（ExchangePage.apply_theme 修复）；**活跃表清零——全部工单完成**；测试 379→**391**，覆盖率 92%

- **kkrb 传输层补测（08-09）**：`tests/test_kkrb_client.py` FakeOpener 脚本式注入（替换 `client._opener` seam）——CSRF 握手降级/重试、TTL 缓存命中/过期、错误路径、reset、端到端传输 22 用例，模块覆盖率 36%→100%（总体 93%）；`_user_agent` 更名残留收尾；测试 357→**379**

- **评审修复（08-08，多维度评审 → 子代理按优先级实现）**：P0 `FetchWorker.shutdown()` 关闭逃生舱（请求在途关窗不再 "QThread: Destroyed while thread is still running" abort，atexit 兜底 join）；P1 `app/fetch_page_base.py` 共享基类（crafting/exchange 双页重复提炼，210→122 / 256→178 行，`_error` 死状态删除）+ `preload()` 公开 seam（消除 main_window 四处私有穿透与 lambda 吞错）；P1 硬编码颜色收敛 theme.py（新增 BTN_HOVER_FG/BADGE_FG/NAV_HOVER_BG/OVERLAY_BG/PACKAGE_COLOR_0~2 七键，dark NAV_HOVER_BG 灰 overlay→半透明白，其余逐字保持）；P2 死代码清理（calculator 不可达 return + calendar、config SQLITE_FILE）+ 更名收尾（日志文件名 `profit_calculator.log` → `delta_force_dashboard.log`，推翻「仅改身份标识」中日志名保留项——单实例锁/user-agent 仍保留）；doc_sync 新增 `tests_total` 机械标记（测试数入 pre-commit 保护）；测试数 6 处文档 + memory 统一 305
- **性能优化（08-07 `ded4a5d` + 08-08 `762ef27`）**：crafting/exchange 页同步 HTTP 请求改 `FetchWorker`（QThread）后台执行，UI 不再阻塞（最坏 30s 冻结→0）；`_DaySubTable.draw` 改 get-or-create 复用 widget（30 天视图每次刷新从创建 ~300 个 Qt 对象降为 0）；calculator `_sorted_dates` 缓存（recent_records/summary/export_csv O(n log n)→O(1)）；`refresh_theme()` 解耦主题切换与数据刷新；kkrb_client 60s TTL 缓存；ProfitPage 制造产物预加载
- **测试**：pytest **305/305** ✅

- **项目更名（2026-08-07）**：正式更名为 **Delta Force Dashboard**（原「收益计算器 / Profit Calculator」）——窗口标题、应用名、`DATA_DIR`（`~/收益计算器` → `~/Delta Force Dashboard`，`_LEGACY_DATA_DIR` 一次性迁移旧数据）、spec 改名 `delta_force_dashboard.spec`（exe `Delta Force Dashboard.exe`）、README/PROJECT_REFERENCE/CODE_WIKI/CONSENSUS/CONTEXT/TO-TICKETS/ADR 文档、GitHub 仓库 `profit-calculator` → `delta-force-dashboard`；按「仅改身份标识」决策，`ProfitCalculatorLogic` 类名、日志文件名、单实例锁、user-agent 等内部标识保留

- **X 系列完成**：子弹自选包兑换利润模块 — X-01 兑换利润页面（`app/exchange_page.py`，7 种包类型网格展示，kkrb_client 新增 `AmmoPackageItem`/`fetch_ammo_package_data()`）+ X-02 特殊子弹自选包扩展（4 种新增包：通行证基础/高级、进阶物流、特级物流）+ X-03 代码气味消除（NamedTuple `_PackageConfig`、`exchangeGradeAndCount` 重命名）
- **ProfitPage 重构**：QTabWidget 标签页 → QScrollArea 纵向堆叠，制造产物与兑换利润无需切换直接可见
- **死代码清理**：移除 SQLiteDataStore（`sqlite_store.py` + `test_sqlite_store.py`，有测试无 UI 消费者，与 D-06 纪律对齐）
- **测试**：pytest **293/293** ✅
- **文档**：8 已有提交补 DEV_LOG + TO-TICKETS 归档

- **M-01 修复**：暗色主题 `CHART_GRID` 色值 `rgba(255,255,255,.05)` 无法被 pyqtgraph 解析（`pg.mkColor` 只认十六进制/SVG 名，浮点 alpha 的 `rgba()` 抛 ValueError）→ 暗色主题下首次绘制图表即崩；改 `#RRGGBBAA` 八位十六进制（`#FFFFFF0D`，alpha 13≈5%，视觉一致）+ 回归测试
- **L 系列完成**：Delta Force 游戏工具扩展全部 4 张工单已实现 — L-01 侧边栏导航（`app/sidebar.py` + main_window 重构为 sidebar | QStackedWidget 水平布局）、L-02 kkrb.net API 客户端（`app/kkrb_client.py`，纯 stdlib，CSRF 自动管理）、L-03 制造利润页面（`app/crafting_page.py`，4 台位卡片 2×2）、L-04 卡战备推荐页面（`app/gear_page.py`，输入匹配 + 方案表格）
- **测试**：pytest **297/297** ✅（296 + 1 M-01 回归）
- **打包**：M-01 后主分支重新打包，`dist/Delta Force Dashboard/` **68M**（exe 6.67MB + `_internal/`），烟测通过（dark 主题 + 9 条记录 = M-01 修复前崩溃场景，直接验证修复）
- **文档**：TO-TICKETS M-01/L 系列归档、CODE_WIKI 测试表补 test_kkrb_client.py、doc_sync 通过

- **L 系列立项**：Delta Force 游戏工具扩展（侧边栏导航 + 制造利润 + 卡战备推荐），ADR-0004 落档，4 张工单录入 TO-TICKETS 活跃表
- **架构评审第二轮**：8 候选全实施完毕（#1 展示文本簇→presentation.py / #2 MainWindow 变薄 / #3 原子写合一 / #4 VIEW_DAYS 单源化 / #5 信号→颜色收敛 / #6 汇总四合一 / #7 MoneyLineEdit.set_value / #8 图表几何抽纯函数），详见日志正文
- **测试**：pytest **259/259** ✅（候选 1+6: -27 移 + 23 新 = 249；候选 3: 不变；候选 2: +5 reuse_candidate 测试；候选 4: 不变；候选 5: 不变；候选 7: 不变；候选 8: +5 adaptive_range 测试；249+5+5=259）

---

## 日志正文

### 2026-08-10 | 修复 | Z-01 兑换页 SEPARATOR 分隔线主题联动（U-03 遗留闭环，484/484）
- **背景**：U-03 遗留「兑换页 SEPARATOR 同为构建期样式（主题切换不更新），建议另开工单」——本次核实时确认：SEPARATOR 双主题值不同（light `#d6d3cc` / dark `rgba(255,255,255,.06)`），`_build_package_card` 构建期解析冻结 → 亮→暗切换后暗面残留浅色分隔线直到窗口重建（crafting_page 核实无此问题：全走 QSS objectName 选择器随 refresh_theme 更新，唯一内联是主题无关 font-size——memory 遗留注记不成立，已澄清）
- **改动**：`_build_package_card` 分隔线引用存 `card._sep`；`apply_theme()` 循环内补齐 `_sep` 运行期刷新（增量更新不重建，模式同包标签）
- **测试**：`tests/test_theme_roles.py` 新增双主题循环用例（set_theme + apply_theme → 断言分隔线含当前主题 SEPARATOR）+ `test_ui_smoke.py` `test_theme_toggle_updates_exchange_labels` 扩展集成断言（theme_btn 点击链路）；Falsify 红验证：临时摘掉刷新 → 2 测试实红 → 恢复全绿（测试非恒真）
- 测试 483→**484**；覆盖率 96%（含测试自身）；doc_sync 同步；.scratch/multi-account（Y 系列工作文件，git 已跟踪）经确认后 `git rm` 清理——内容已完整归档（DEV_LOG 逐工单摘要 + TO-TICKETS 归档表 + 二轮评审修复节）

### 2026-08-09 | 实现 | U-03 色彩角色系统化（kickoff 全流程：Implement + code-review 三轴，391/391）
- **键收敛**：7 包色收敛单一装饰键 `PACKAGE_COLOR_0~6`（删 CHART_SERIES_*/PACKAGE_COLOR_* 双套键；CHART_SERIES 键名撒谎——只服务兑换页包色、chart_widget 不引用）；亮暗同值键不抽常亮色（保留双主题定义防 Locality 坑）
- **色板重调**：**dark 曾 3 级包标签=涨色 #3FCB86、5 级包标签=亏色 #FF5F56（与 FG_POS/FG_NEG 完全同值）**——新色板 dark 亮彩带 L∈[0.72,0.84] 整体避让 FG_NEG（L≈0.67）、light 深墨带 L∈[0.20,0.32] 保 AA 4.5:1；S≥0.55、两两 ΔE76≥25；色相语义沿用（3 级青绿/4 级金/5 级红/通行证基础蓝紫/高级紫/物流橙褐/粉红——特级物流橙红→粉红为满足 ΔE 下限漂移）
- **谎言修正**：exchange_page.py:34「hex 回退色」注释与实现不符——`get_color` 缺失键返回 `""`，旧 `or color` 回退键名字符串=无效色，不存在 hex 回退路径；`_resolve_color` 死回退删除
- **机器证伪验收**：`tests/test_theme_roles.py`（215 行）8 断言全过——键名如实/键引用完整/装饰≠语义（ΔL≥0.05）/明度带/两两 ΔE/AA 4.5:1/6 位 hex 格式；目检降级为辅助（U-09 前科）
- **code-review 三轴**（Standards + Spec + Falsify 并行）：Falsify 抓到真缺陷——**主题切换后包标签色残留**：改动前双主题同值潜伏（exchange_page/fetch_page_base 无 apply_theme，标签色构建期冻结），改动后亮暗分离 → 亮→暗切换残留 light 深墨色于 dark 卡面（对比度 1.26~3.85:1 vs 正确 7.6~15.6:1），改动放大为可见缺陷；修复：`ExchangePage.apply_theme()` 运行期重解析 + 挂入 `main_window.refresh_theme`（增量不重建），Falsify 红验证（摘接线→集成测试实红→恢复全绿）
- **审查另修**：test_theme_roles 主题状态泄漏（循环后 `set_theme("dark")` 不恢复，全绿靠字母序侥幸——theme_guard fixture 保存/恢复，反序跑验证）；6 位 hex 格式断言（8 位静默丢 alpha/rgba 裸崩两路径封死）；test_fetch_pages 注释「沿用历史」表述修正
- 测试 388→**391**（+8 角色断言 +1 Falsify +2 评审修复 +1 集成）；覆盖率 92%；doc_sync 同步
- 遗留（非本工单范围）：兑换页分隔线 SEPARATOR 同为构建期样式（主题切换不更新）；crafting_page 无 apply_theme（本次未改其颜色）——均记遗留，建议另开工单

### 2026-08-09 | 测试 | kkrb_client 传输层补测（V-01 收尾，379/379）
- **背景**：V-01 拆分后传输层（CSRF 握手 / `_post_json` / TTL 缓存 / 错误路径）覆盖率仅 36%，是测试体系唯一盲区（D-04 教训在传输层未落地）
- **FakeOpener 注入**：脚本式 fake opener 替换 `client._opener` seam——握手/缓存/错误路径走真实代码，仅网络层被替换；script 条目支持 bytes 响应 / Exception 抛出 / `(bytes, cookie名, cookie值)` 向 cookie jar 注入 csrf cookie
- **22 新用例**：握手成功 + token 缓存复用（二次 fetch 零握手）、首页/getMenu/ValueError 失败降级空 token、cookie 缺 token 每次重握手；TTL 缓存命中零网络、过期重拉（握手复用）、OSError/ValueError→KkrbError、畸形 JSON/空响应→KkrbError、POST 请求头完整性（CSRF/UA/Content-Type/method）；`_parse_json` BOM 剥离/空/畸形/list；UA 匹配产品名；reset 清会话后完整重握手；两 `fetch_*` 端到端真实传输+解析
- **发现并固化**：①握手失败空 token **不缓存**（`_csrf_token` 保持 None → 每次 fetch 重新握手）；②urllib `Request.add_header` 会 `key.capitalize()` 头键（`X-CSRF-Token`→`X-csrf-token`），测试断言需 `header_items()` 大小写不敏感取值（helper `_header_value`）
- 顺带修复：`_user_agent()` 残留 `ProfitCalculator/1.0` → `DeltaForceDashboard/1.0`（更名遗漏项，无测试断言受影响）
- kkrb_client.py 覆盖率 **36%→100%**（总 91%→93%）；pytest **379/379** ✅；doc_sync 同步（测试数 357→379）

### 2026-08-09 | 实现 | W 系列微交互打磨（U-06 遗留方向落地，357/357）
- **W-01 KPI count-up**：`motion.animate_value`（数值插值动画：old→new 逐帧回调，动效开关关闭直接落终态）+ `MainWindow._set_kpi_value`（保存/刷新时总盈亏与现金总变化数字 300ms 从旧值滚动到新值，逐帧复用 format_signed_money 格式化——终态与直接设置完全一致；数据不足/数值未变直接设置）；`_last_summary_total/_last_cash_delta` 上一帧值
- **W-02 非法输入 shake**：`MoneyLineEdit._shake`（QPropertyAnimation 150ms 水平平移 [-6,6,-4,4] 回原位；状态从非 invalid 变 invalid 时触发防抖——连续非法不重复；仅用户输入/失焦校验路径，动效开关尊重）
- **W-03 按钮 pressed 下沉**：QSS 全局 `QPushButton:pressed { padding-top: 7px; padding-bottom: 5px }`（1px 下沉；saveBtn/refreshBtn/queryBtn 各自 pressed padding 覆盖优先，补齐其余按钮按压缩放一致性）
- **W-04 图表 hover 数据点高亮**：`_hover_markers`（仓库/现金各一 ScatterPlotItem：13px 大圆点 + 主题底填充 + 系列色描边），hover 时 setData 定位当前点、离开隐藏、主题切换描边色跟随（apply_theme）
- 测试 +3（count-up 终态/数值未变/开关 + shake 触发/防抖 + hover marker 就位/主题切换）；pytest 357/357 ✅；doc_sync 同步

### 2026-08-09 | 重构 | V-02/V-03/V-04 架构深化候选 2/3/5（子代理并行实现 + 主 session 合并，354/354）
- 来源：improve-codebase-architecture 报告候选 2/3/5，grilling 设计树 11 问全按推荐；三子代理并行实现，主 session 审查合并
- **V-02 状态机拆分**（`app/load_state.py` 新，LoadState 四态）：fetch_page_base 删 `_loaded_once`/`_loading` 私有字段改持 `_load_state`；`is_loaded` 公开 property（测试不再窥视私有）；**子代理实现暴露真实回归**——`can_load()` 原设计排除 loaded 态导致「加载成功后点刷新 = no-op」（刷新是核心操作）→ 主 session 修正：`can_load()` 仅挡 loading 防重入，loaded 可手动刷新；`preload()` 补 `is_loaded` 守卫（预加载只做一次）；新增 loaded→loading 刷新转移用例 + 页面级刷新回归测试
- **V-03 SettingsCodec**：`settings_store.py` 增 `decode_geometry_hex`/`decode_legacy_geometry`（旧格式含负坐标，正则 fullmatch 处理 `"820x880-100+50"` 粘连段）/`encode_settings`，保持零 Qt 依赖（bytes 层）；main_window 几何双格式解析 -25 行手写分支改走 codec；`_save_settings` 委托 encode；10 新用例
- **V-04 主题双轨收敛**：删 `button_style()`（edit_save 与 QSS #saveBtn 内容重复——QSS 单一来源；danger 改 QSS 属性选择器 `reuseBtn[state="danger"]`，input_panel setProperty+repolish 切换——与 MoneyLineEdit validity 模式一致）；exchange 包标签内联字号收敛（QSS exchangePackageLabel 15px/700 单一来源，内联只留动态色）；`tests/test_theme_qss.py` 4 用例（选择器/双主题色值/删除守卫/属性切换）
- 测试 331→354（+23：LoadState 8 + 刷新回归 1 + SettingsCodec 10 + theme_qss 4）；CODE_WIKI 新文件标记手补；pytest 354/354 ✅；重新打包 + 烟测

### 2026-08-09 | 重构 | V-01 kkrb_client 解析拆出（架构深化候选 1，331/331）
- 来源：improve-codebase-architecture 报告 + grilling 共识（6 问全按推荐）
- `kkrb_models.py`（新，零依赖叶子，仿 signals.py 先例）：CraftingProduct / AmmoPackageItem / KkrbError——模型被解析、客户端、UI 三方引用，独立避免循环 import
- `kkrb_parsing.py`（新，纯函数模块）：`parse_ov_response` / `parse_ammo_package_response`（公开名去 `_` 前缀）/ `_int_or_zero`——原 KkrbClient 类内 staticmethod 迁移，行为逐字保持
- `kkrb_client.py` 收敛：删除类内 `_parse_*`/`_int_or_zero`（协议表面收敛为 fetch_* + reset），`from kkrb_models/kkrb_parsing import` + `__all__` 重新导出——crafting/exchange/fetch_page_base 及全部测试**零改动**（协议表面不变）；`_parse_json`（HTTP 体→JSON）保留在传输层
- 测试：`tests/test_kkrb_parsing.py` 新建（28 用例 = 迁移 16 + 畸形矩阵扩展 12：非 dict/缺字段/字段类型异常/畸形条目跳过/placeName 回退 key/字符串数字转 int）；`test_kkrb_client.py` 精简为 4 用例（模型 + 协议表面收敛断言：`not hasattr(KkrbClient, "_parse_ov_response")`）；CODE_WIKI 新文件标记手补 + doc_sync
- pytest 331/331 ✅；重新打包 + 烟测

### 2026-08-09 | 修复 | U-11 切页崩溃（用户实测：点利润→切回→再点利润闪退，317/317）
- **症状**：快速切页（利润→记账→利润）闪退无提示；日志无崩溃现场（无 crash 捕获）
- **根因定位**：U-06 切页淡入动画（`fade_in_widget` → QGraphicsOpacityEffect + QPropertyAnimation 挂 QStackedWidget 页面）——QGraphicsEffect 挂在 QStackedWidget 页面上，动画进行中页面被 hide/show（快速切页），触发 Qt 已知崩溃路径（effect 与 stack 绘制交互）；Falsify 只测过「同 widget 连续 fade」，未覆盖「stack 切页中 hide/show」场景
- **修复**：① 移除切页淡入动画（`_on_page_changed`/`_PAGE_FADE_MS` 删除；曲线绘制/保存指示动画保留——它们不在 hide/show 路径上）；② `fade_in_widget` 补 dynamic property 悬空指针清理（DeleteWhenStopped 自删动画后 `_fade_anim` 里的 QObject* 悬空，下次读取访问已删对象）——finished 时同步 `setProperty("_fade_anim", None)`；③ **崩溃现场捕获**入 main.py：faulthandler（crash.log，all_threads）+ sys.excepthook（未捕获异常写日志，PyInstaller 无 stderr 默认被吞）+ qInstallMessageHandler（Qt qWarning/qCritical/qFatal 落盘——"QThread destroyed" 等致命消息 abort 前先记录）——下次任何崩溃都有现场
- 回归：`test_page_switch_loop_no_crash`（利润→记账×20 循环）+ U-06 测试改断言（切页动画断言移除、property 清空断言加入）
- pytest 317/317 ✅；重新打包 + 烟测

### 2026-08-09 | 实现 | U-10 利润页启动预加载（316/316）
- 用户反馈：利润页点击后才开始拉数据，有卡顿感。根因：`_preload_profit_page` 只预加载制造产物，兑换利润由首次 showEvent 才拉取（10s 超时 HTTP）
- 改：启动 500ms 定时器同时预加载 crafting + exchange（各自 FetchWorker 后台线程，kkrb 60s TTL 缓存复用）；点击利润页时数据已就绪零闪烁；预加载失败仍走既有兜底（状态标签可点重试）
- 测试坑：`QTest.qWait(1600)` 固定时长与两个后台线程调度存在竞态（同一测试首跑通过次跑失败）→ 改轮询等待 `_loaded_once`（50ms 步进 + 5s 超时），3 连跑稳定
- 测试 +1；pytest 316/316 ✅；重新打包 + offscreen 烟测

### 2026-08-09 | 修复 | U-09 方案 A：折线图空间按屏幕自适应（315/315）
- 用户实测反馈：表格全量展示达成后折线图 140-150px 太小。空间账：920 窗口已被顶部 190 + 表格 490 + 图表 160 + 提示/边距占满，图表变大只能向屏幕高度要
- 方案 A（用户拍板）：`MainWindow._window_preset(screen_h)` 纯函数两档——可用高度 ≥1000（1080p 主流）→ 窗口 1020 + 图表 [160,240]（+90px/+60%）；小屏 → 920/[140,150]；两档表格全量参数（行高 26/stretch 1）完全一致
- 实测：大档 1020 窗口图表实际 240px，30 天视图左 15/15 右 15/15 全量无滚动 ✅
- 测试 +1（`_window_preset` 边界：1000 含/999 不含/0 兜底）；test_u02_type_scale 图表断言改与 `win._chart_min_h/_chart_max_h` 实际档位对齐
- 重新打包（PyInstaller onedir）+ offscreen 烟测

### 2026-08-09 | 修复 | U-09 用户实测反馈（打包前修复，314/314）
- 用户反馈三处：①折线图卡片太大挤占表格，表格要全量展示不要滚动；②「今日未录入」提醒没了；③利润页亮色主题卡片纯白背景纯黑违和
- **①图表布局回退**：U-02 的弹性翻转（chart stretch 1 吃窗口增长）推翻——chart 固定 [140,150] stretch 0，表格恢复 stretch 1（H-01 语义）；30 天视图全量展示关键参数：行高固定 26px（`resizeRowsToContents` 的 sizeHint 与 QSS 交互算出 33px，15 行塞不下 → 改 `setDefaultSectionSize(26)`）+ 视图按钮 28→24px + 卡片边距 (12,10)→(10,8) + 默认窗口 880→920；实测 920 窗口 30 天视图左 15/15 右 15/15 全量可见、无滚动条，7 天 4+3 全量
- **②pill 不可见根因**：WARNING_BG `#fcf4e8` 与 sage 页面底 `#eef0ec` 亮度差仅 0.029（近同色）→ 改 `#F1D9A0`/`#6E4A08`（亮度差 0.084 + 琥珀 vs 灰绿 hue 双区分，10px 文字对比 ≈7:1）；dark `#261e14`→`#3A2E1A`
- **③利润页背景纯黑根因**：U-05 全局 `QWidget { font-family }` 规则使**所有未显式设背景的 QWidget 落入 palette.window 背景**（不随主题）——用户系统深色 palette 时亮色主题下背景即纯黑（本机实测 viewport palette window `#efefef`，autoFillBackground 被 QStyleSheetStyle 接管、代码关闭无效）→ QSS 显式 `QWidget#profitPage, QWidget#profitContainer { background-color: bg }` + profit_page.py viewport 内联透明（QSS 选择器匹配不到 viewport）；双主题实测背景 == 主题 BG
- 附带：QSS 注释内 `{ font-family }` 触发 f-string 插值 NameError（已改写注释避坑）；test_u02_type_scale 图表断言更新为回退语义
- 打包：PyInstaller onedir 重建，dist 67M，offscreen 烟测 12s 无崩溃

### 2026-08-09 | 修复 | U 系列 code-review 评审修复（U-08，314/314）
- 双轴评审（Standards + Spec + Falsify 维度，2 子代理并行）结果：无崩溃级问题；3 处真实规格偏差 + 若干标准项
- **修复**：① 动效全局开关——`motion.set_animations_enabled`（settings 键 `animations`，默认 true），关闭时 fade_in 不挂 effect、属性动画直接落终态（U-06 验收「系统关闭动画时全部动效失效」以设置项实现，注册表检测不做）；② `fade_in_widget` 竞态防护——同 widget 连续触发先 stop 旧动画（QPropertyAnimation.stop 不发 finished，旧清理回调不会误删新 effect）；③ `animate_property` 参数收紧 `QObject`（去 type: ignore）；④ `exchangePage` 包名标签内联 14→15px（QSS 已改 15 但内联优先级更高，U-02 归位失真——DEV_LOG 上一版记录失真已更正）；⑤ `EMOJI['ok']` 收敛 main_window CSV 提示（字面量 ✓ 清零，测试 regex 补 ✓ + Path 绝对化）；⑥ 曲线动画 250→200ms（feedback-only 上限）
- **裁决/取舍**：`app/motion.py`/`ui_text.py` 不注册进 `app/__init__.py`——与 `fetch_worker.py` 同例（内部工具模块不进包表面）；U-01 迷你趋势/窄窗口响应式堆叠不做（验收未列项 + 实测 680px 可用，DEV_LOG 记取舍）
- 测试 +1（动效全局开关）；pytest 314/314 ✅

### 2026-08-09 | 实现 | U-01~U-06 UI 视觉打磨（finesse-ui 审计落地，313/313）
- **U-01 KPI 磁贴**（`b5d230e`）：汇总从裸 QLabel 升级为卡片磁贴——`_split_kpi_text` 拆「说明行（11px caption）+ 数值行（22px 信号色）」；`summary_style` 升级（正常 22px/700、数据不足 16px 灰）；输入卡限宽 520 与 KPI 卡并排（顶部两栏），宽窗口不再全宽拉伸
- **U-02 排版刻度**（`251baec`）：QSS 顶部注释固化刻度（display 18-22 / section 15-16 / body 12-13 / meta 10-11）；按钮两级（QPushButton 默认 11px/500 = secondary，saveBtn/queryBtn 13px/600 = primary；themeBtn 等 10→11、refreshBtn 12→11）；页面标题 `pageTitleLabel` 16px 与应用名 18px 分层；craftProduct 18→16、tierLabel/exchangePackageLabel 14→15；**图表弹性翻转**——chart min 200、max 220 封顶移除、chart_card stretch 0→1、table_card 1→0（H-01「表格独占弹性」决策推翻：趋势图优先趋势阅读），30 天视图超高改 `_DaySubTable` vertical AsNeeded 内部滚动兜底（原 AlwaysOff 会裁剪行）
- **U-04 侧边栏**（`222787d`）：宽度 100→130；选中态「整条实心 BTN_BG」→「浅底 pill（新键 NAV_SELECT_BG，light 森林绿 12% / dark 琥珀 14% 透明）+ 3px accent 指示条」——border-left 选中/未选中同宽（transparent vs accent）保证文字零位移；选中文字改 accent 色
- **U-05 emoji 一致性**（`f0741ff`）：新增 `app/ui_text.py` EMOJI 单一来源（9 键：导航/主题/置顶/加载/警告/保存），sidebar/main_window/fetch_page_base/chart_widget 4 文件散落字面量清零（AST 测试断言无残留）；全局 QWidget font-family 补 "Segoe UI Emoji" 消 Windows 基线错位
- **U-06 反馈型动效**（`d430cd7`）：新增 `app/motion.py`——`fade_in_widget`（QGraphicsOpacityEffect + QPropertyAnimation，结束后移除 effect 防常驻）+ `animate_property`（QVariantAnimation 驱动非 QObject property，如 pyqtgraph 曲线 opacity）；接入三处：切页 120ms 淡入（`_on_page_changed`）、曲线绘制揭示 250ms（opacity 0→1）、保存指示 180ms 淡入
- **U-06 取舍**：hover 背景平滑过渡**未做**——Qt Widgets QSS 无 transition，背景色动画需自定义样式委托（QStyle 子类或事件过滤器逐帧重绘），成本显著高于收益，且 QSS 跳变 + 光标已是可接受的反馈；若用户要平滑 hover 需单独立项
- 测试 305→313（+8：可点重试/中性 badge/U-07 聚合/U-01 拆分/U-02 刻度/U-04 侧边栏/U-05 emoji 来源/U-06 动效），doc_sync 标记同步，每工单独立提交

### 2026-08-09 | 实现 | U-07 交互小修批量（交互反馈闭环）
- **可点「重试」**：`fetch_page_base.py` 新增 `_ClickableLabel`（clicked 信号 + mousePressEvent），错误态设手型光标、点击重新 `_load_data`；文案「点击重试」从骗人变真实（T-02 旧文案回归测试保持通过）
- **按钮焦点态**：`generate_qss` 加 `QPushButton:focus { outline: 2px solid FOCUS_RING }`（Qt 6 QSS outline 不占布局，避免像 QLineEdit 那样 padding 补偿）；Tab 键流可见
- **今日未录入 pill**：`todayStatusLabel` 从裸文字改 WARNING 系底色+边框+圆角 pill（亮 #fcf4e8/#B77A16，暗 #261e14/#E8A33D）
- **轴线对齐**：日期标签取消整页居中改左对齐（与标题同侧），消「标题左/日期中」错位
- **QStatusBar 死样式删除**（8px，从未使用）
- **中性 badge 对比度**：`—` badge 由 FG_MUTED 底+白字（≈4.2:1）改 MUTED_BG 底 + TEXT_SECONDARY 字（light ≈7:1 / dark ≈5.5:1，AA 达标）；涨/亏 badge 配色不变
- 测试 +3（可点重试 / 中性 badge 双主题 / UI 小修聚合断言）；doc_sync 刷新 11 标记；pytest 308/308 ✅

### 2026-08-09 | 审计 | finesse-ui UI 审计 → U 系列工单录入（TO-TICKETS 活跃表）
- 用户反馈 UI「差点意思」，按 finesse-ui skill（product register：craft floor + 密度 + 反廉价清单）全量审计 9 个 UI 模块
- 结论：**底色（craft floor）已达标**——tinted 中性色（无纯 #fff/#000）、hairline 半透明边框、红涨绿跌语义色、焦点环、主题切换无 import 期冻结（C1 教训内化）；问题集中在三层：数字没有家（KPI 层级）、字号没有刻度（排版层级）、颜色没有组织（色彩角色）
- 关键发现：① 汇总（总盈亏/现金总变化）是唯一没住进卡片的元素；② 全 app 字号挤在 8-18px 无刻度，按钮 10/11/12/13px 四档乱跳；③ 图表限高 [140,220] 拿不到窗口增长空间；④ 兑换页 7 包 7 色相 + emoji 混排（游戏感 OK 但无组织）；⑤ 「点击重试」label 不可点（骗人文案）；⑥ 动效为零（hover 直跳色、页面切换无过渡）
- 方向拍板（用户）：**游戏感强一点**——保留多色点缀与 emoji，不收敛配色，只修层级/布局/动效
- 录入 U-01~U-07 至 TO-TICKETS 活跃表（U-01 KPI 磁贴+顶部两栏 / U-02 排版刻度 / U-03 色彩角色系统化 / U-04 侧边栏重做 / U-05 emoji 一致性 / U-06 反馈型动效 / U-07 交互小修批量），暂不实现
- 一次性审计脚本（offscreen 两页两主题截图）已清理，未入版本控制

### 2026-08-08 | 评审修复 | 多维度评审 → 4 子代理按优先级实现（P0/P1/P2）
- P0: `FetchWorker.shutdown(timeout_ms=300)` + 逃生舱——`requestInterruption()` + `wait(超时)`，超时后 `setParent(None)` 脱离 + 模块级 `_detached_workers` 强引用 + `atexit` 兜底 join；`run()` 顶部检查中断标志；`MainWindow.closeEvent` 停 `_preload_timer` + 级联 `ProfitPage.shutdown()`；消除 "QThread: Destroyed while thread is still running" abort 路径（4 项新测试）
- P1: `app/fetch_page_base.py`（179 行）——crafting/exchange 共享基类：`_client/_loading/_loaded_once/_worker/_data/_shut_down` 状态机、showEvent 懒加载、标题栏+状态标签构建、`_load_data/_on_fetch_done/_on_fetch_error` 三件套、`refresh/preload/shutdown`；crafting 210→122、exchange 256→178 行；`_error` 死状态（两页均只写不读）删除并有测试固化
- P1: `preload()` 公开 seam——main_window `_preload_profit_page` 收缩为一行，删除对 `_loaded_once/_loading/_client/_on_fetch_done` 四处私有穿透与 `lambda e: None` 吞错（失败走 `_on_fetch_error` 记 warning + 状态标签「点击重试」）
- P1: 硬编码颜色收敛——theme.py 新增 7 键（BTN_HOVER_FG/BADGE_FG/NAV_HOVER_BG/OVERLAY_BG/PACKAGE_COLOR_0~2，双主题定义）；table_widget PnLBadge/_ActionButtons hover、theme danger 按钮 hover、sidebar 导航 hover、chart 稀疏提示 overlay、exchange 剩余 3 包色收敛；dark NAV_HOVER_BG 由灰 overlay 改半透明白（暗底可见性），其余逐字保持
- P2: 死代码清理——calculator `rotate_weekly` 不可达 `return self._window_delta(...)` + `import calendar`；config `SQLITE_FILE`（92f1a94 移除 SQLiteDataStore 后零引用）
- P2: 更名收尾——`_LOG_FILE` `profit_calculator.log` → `delta_force_dashboard.log`（.gitignore 同步；推翻更名时「日志文件名保留」项，单实例锁/user-agent 仍保留）；main.py 经 `LOG_FILE` 常量引用无需改
- 文档: doc_sync 新增 `tests_total` 机械标记（测试数入 pre-commit 保护）；测试数 6 处文档 + memory 统一；DEV_LOG 补记 `ded4a5d`/`762ef27`；CODE_WIKI 模块树补 3 模块/§4 编号重排/§7 表补齐
- 测试：pytest 305/305 ✅（293 + 12 新：test_fetch_pages.py）

### 2026-08-08 | 性能 | sorted_dates 缓存 + 主题刷新解耦 + kkrb TTL 缓存 + ProfitPage 预加载（`762ef27`）
- P0: calculator.py 维护 `_sorted_dates` 缓存——recent_records/summary/export_csv 从 O(n log n) 降为 O(1)，save_record/delete_record/rotate_weekly 增量更新
- P0: main_window.py 新增 `refresh_theme()` 解耦主题切换与数据刷新——主题切换只刷新视觉样式，不再触发 chart.draw 全量渲染
- P1: kkrb_client.py 新增 60 秒 TTL 内存缓存，避免短时间内重复 HTTP 请求；`reset()` 同步清除缓存
- P1: main_window.py QTimer.singleShot(500ms) 后台预加载 ProfitPage 制造产物数据；crafting_page/exchange_page `_on_fetch_done` 补设 `_loaded_once=True`，消除预加载完成后 showEvent 重复触发
- 测试：pytest 293/293 ✅

### 2026-08-07 | 性能 | 网络请求移至后台线程 + 表格 widget 复用（`ded4a5d`）
- P0: crafting_page/exchange_page 的同步 HTTP 请求改用 `FetchWorker`（QThread，`app/fetch_worker.py`）后台执行，UI 线程不再阻塞（最坏情况从冻结 30s 降为 0）
- P1: `_DaySubTable.draw` 重构为 get-or-create 模式——QTableWidgetItem/PnLBadge/_ActionButtons 首次创建后后续刷新只更新属性，不再重建；30 天视图每次刷新从创建 ~300 个 Qt 对象降为 0
- 测试：pytest 293/293 ✅（纯性能改动，测试数不变）

### 2026-08-06 | 清理 | 移除 SQLiteDataStore 死代码（与 D-06 纪律对齐）
- 删 `sqlite_store.py`（99 行）+ `tests/test_sqlite_store.py`（107 行）
- `data_store.py` 脱 `from sqlite_store import SQLiteDataStore` 导入 + `__all__` 移除条目
- `CODE_WIKI.md` 文件树同步删 `test_sqlite_store.py` 行
- 有测试无 UI 消费者，真死代码，与 D-06 一致
- pytest 293/293 ✅

### 2026-08-06 | 重构 | ProfitPage 标签页改为纵向堆叠（QTabWidget→QScrollArea）
- 制造产物推荐 + 兑换利润在同一滚动页面内纵向堆叠，无需标签页切换
- 各自保留标题栏与刷新按钮，独立刷新；`setSizePolicy(Policy.Fixed)` 按内容高度排列
- `addStretch()` 内容不足时推到顶部，超出时滚动条自动出现
- theme.py 删除 QTabWidget/QTabBar 33 行 QSS 样式（不再需要）
- CODE_WIKI/README profit_page 描述同步更新
- pytest 293/293 ✅

### 2026-08-06 | 多个 | 兑换利润模块（X 系列）— 无工单无日志，补充记录
- 源：08-05 起从 L-03 制造利润页面延伸，独立进入兑换利润方向
- 以下 4 个提交合并为 X 系列统一补录

#### X-01（8c6393e）：子弹自选包兑换利润模块，制造板块更名为利润
- 新增 `AmmoPackageItem` 数据模型（frozen dataclass）和 `fetch_ammo_package_data()` API
- 新增 `ExchangePage`：展示 3/4/5 级子弹中利润最高的兑换方案，QTabWidget 标签页容器
- 新增 `ProfitPage`：QTabWidget 标签页容器（制造产物 + 兑换利润）
- 侧边栏「制造」→「利润」；新增 QTabWidget + 兑换卡片 QSS
- 测试 +7；pytest 299/299 ✅

#### X-02（7977de6）：兑换利润页面增加 4 种特殊子弹自选包
- 取消 kkrb_client 等级过滤，返回所有子弹数据
- exchange_page 重构：7 种包类型各一张卡片（4 列网格布局）
- 新增卡片：通行证基础/高级、进阶物流、特级物流
- 新增样式 exchangeGradeLabel2/exchangePackageLabel；测试 +2（全等级解析 + 特殊包解析）

#### （235cf9a）：文档同步（测试计数、页面列表、项目结构）
- CODE_WIKI.md + README.md 同步

#### X-03（c9bdeb7）：消除两个代码气味
- Primitive Obsession：`_PACKAGE_CONFIG` list[tuple] → NamedTuple `_PackageConfig`
- Mysterious Name：`exchangeGradeLabel2` → `exchangeGradeAndCount`

### 2026-08-06 | 推送 | origin 4 提交落后修复 + 8 提交统一推送
- origin/main 落后 HEAD 4 个提交（X 系列 + 文档同步）
- 工作区 3 个改动（profit_page 重构 + 死代码清理 + DEV_LOG/TO-TICKETS 补录）一并提交
- 共 8 提交推送至 origin（已推 + 4 新增）

### 2026-08-05 | 打包 | 主分支重新打包（M-01 后）+ 烟测通过（dark 崩溃场景直接验证）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）；spec 无变更
- 产物：`dist/Delta Force Dashboard/` **68M**（exe 6.67MB + `_internal/`）；M-01 改动（`app/theme.py`）编译入 PYZ
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（pid 14980，常驻 ~226MB）；用户真实 settings 为 **dark 主题 + 9 条记录**（≥2 触发图表创建路径）——正是 M-01 修复前的崩溃场景，存活 8s 无 Traceback 直接验证修复生效
- 分发前确认：dist 内无运行态数据（data.json/settings.json/log 均缺）
- release 资产未更新（用户未指示；如需更新 `default.zip` 另行执行）

### 2026-08-05 | 修复 | M-01 暗色主题图表网格色 pyqtgraph 解析崩溃
- 症状：暗色主题（Midnight & Amber）下应用启动即崩 `ValueError: Unable to convert rgba(255,255,255,.05) to QColor`（`chart_widget.py` 创建轴时 `pg.mkPen(color=grid_color)`）
- 根因：`app/theme.py` 暗色 `CHART_GRID = "rgba(255,255,255,.05)"` 是 QSS 风格色（浮点 alpha），**pyqtgraph 的 `pg.mkColor` 只认十六进制/SVG 颜色名，不解析 `rgba()`**；其余 `rgba()` 色值只进 QSS 不受影响，唯一流入 pyqtgraph 的就是 CHART_GRID
- 修复：改 `#FFFFFF0D`（RRGGBBAA 八位十六进制，alpha 13≈5%，与原视觉一致）；亮色 `#e2e4df` 本就合法未动
- 回归测试（先写复现）：`tests/test_chart_geometry.py` 新增 `test_chart_colors_parseable_by_pyqtgraph`——双主题 × 5 个图表取色键逐一 `pg.mkColor()`，防再混入 QSS-only 色值
- 测试：pytest 297/297 ✅（296+1）；doc_sync 刷新 CODE_WIKI 机械标记
- TO-TICKETS M-01 → ✅ 归档（2026-08-05）

### 2026-08-04 | 设计 | L 系列立项 — Delta Force 游戏工具扩展
- 来源：Grilling 会话，用户需求「制造利润排行 + 卡战备推荐」
- 范围：两功能整合到现有Delta Force Dashboard App，左侧边栏切换（记账/制造/战备）
- 设计：ADR-0004 落档（QStackedWidget + 侧边栏方案 A），CONTEXT.md 新增 Delta Force 领域词汇
- 工单：L-01~L-04 录入 TO-TICKETS 活跃表，含详细验收标准
- 测试：259/259 ✅（纯设计，未动代码）
- 注：kkrb.net 已确认有公开 REST API（`getOVData`/`getCPVData`），无需浏览器渲染

### 2026-08-05 | 实现 | L 系列全部完成 — Delta Force 游戏工具扩展
- **L-01（侧边栏导航）**：`app/sidebar.py` 新文件（QWidget + QListWidget 导航 + 底部主题/置顶/导出按钮）；`main_window.py` 重构为水平布局（sidebar | QStackedWidget），Dashboard 为 Page 0，标题栏/日期标签只在记账页显示；侧边栏主题色 `apply_theme()` 方法（运行时 get_color 避免 C1 复发）；按钮引用改为 `self.sidebar.*`
- **L-02（kkrb.net API 客户端）**：`app/kkrb_client.py` 纯 stdlib（urllib.request），数据模型 `CraftingProduct`/`GearScheme`/`GearItem`（frozen dataclass），CSRF 首页提取 + 缓存复用，`KkrbError` 自定义异常，测试 14 项
- **L-03（制造利润页面）**：`app/crafting_page.py`，4 台位卡片 2×2 网格，加载中/失败重试状态，刷新按钮，按利润排序
- **L-04（卡战备推荐页面）**：`app/gear_page.py`，输入框支持 K/M/B 后缀解析，`_find_closest_tier` 匹配最近档位，方案卡片含 QTableWidget 装备清单
- **测试**：295/295 ✅（+14 kkrb_client 测试）；UI 烟测 28 项全绿（含 sidebar 按钮引用迁移）
- **文档**：TO-TICKETS L 系列归档、CODE_WIKI 测试表补 test_kkrb_client.py、DEV_LOG 同步、doc_sync --check 通过

### 2026-08-04 | 实现 | R-02 DataStore 泛型化 `DataStore[T]`
- `DataStore` 改为 `DataStore(Generic[T])`，`T = TypeVar('T', bound=dict)`
- `load()` 返回 `T`，`save(data: T)` 接受 `T`
- 内部方法 `_try_load`/`_atomic_write` 保留具体类型签名不变
- 向后兼容：所有现有代码使用 `DataStore()` 无类型参数，类型检查器推断为 `DataStore[dict]`，运行时行为一致
- 测试：264/264 ✅（全部通过，无回归）
- 文档：TO-TICKETS R-02 移入已完成归档

### 2026-08-04 | 实现 | 第二轮架构评审 8 候选全实施（Grilling → subagent fan-out → 合并）
- 来源：`D:\Desktop\To-do\architecture-review-20260804-1110.html`（架构评审报告第二轮，8 候选）
- 流程：Grilling 三问（Q1-Q3）→ 用户拍板 → parallel subagent worktree 实施 → 合并 → code-review → 文档同步
- 候选 1+6（`3964d83`）：展示文本簇拆出 `presentation.py`（根层，5 公开函数）+ `format_window_text` 参数化替代 format_summary/format_cash_summary（#6 四合一）。`calculator.py` 协议面 17→11 方法，`summary`/`cash_summary` 改为 `_window_delta` 薄包装。
- 候选 3（`3964d83`）：`DataStore._atomic_write` 委托 `json_file.atomic_write_json`，原子写 seam 唯一实现，测试面收敛。
- 候选 4（`d1e39cf`）：`VIEW_DAYS` 移入 `config.py`，`WEEK_DAYS` 保留语义独立性，注释说明数值巧合。
- 候选 5（`7ea4a26`）：`_PNL_TO_KEY` 合并进 `_SIGNAL_TO_KEY`，`signal_color(RateSignal | PnLSignal)` 单入口，`table_widget.py` 删 18 行自建映射。
- 候选 2（`3368a2c`）：`reuse_candidate` 纯方法下沉 calculator（返回三元组含 is_today_fallback），`summary_style` 封装进 theme，`view_n` 只读 property，`set_reuse_hint` 合并三步委托。`_update_summary` 样式去重，`_reuse_last_record` 缩小。
- 候选 7（`4275479`）：`MoneyLineEdit.set_value(text)` 公开方法，`_formatting` 重入保护内聚，`InputPanel` 调用方改走公开协议。
- 候选 8（`4f76876`）：`_adaptive_range` → `adaptive_range` 公开纯函数，`ChartState`/`ChartSeries` frozen dataclass，`state` property 只读快照，烟测改走 `chart.state` 公开 API，新增 `test_chart_geometry.py`（5 测试）。
- 测试：259/259 ✅（249+5+5，doc_sync 通过）
- 文档：TO-TICKETS 归档 8 候选 + DEV_LOG 同步；code-review 通过（Standards 0 硬违反，Spec 2 项需注意）

### 2026-08-04 | 打包 | K 系列重新打包（3efc77c）+ 烟测通过
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）；spec 无变更
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.56MB + `_internal/`）；K 系列改动（`calculator.py`/`app/main_window.py`）编译入 PYZ
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（pid 17536，常驻 ~200MB；`.migrated` 10:20:04 重写证明启动路径完整、日志无异常）
- release 资产未更新（用户未指示；如需更新 `default.zip` 另行执行）

### 2026-08-04 | 实现 | K-01 保存保留两位小数 + K-02 现金总变化展示
- 需求：用户「修改数据保存逻辑：保留两位小数」+「最近7条/30条总盈亏旁边加一条最近现金7条/30条总变化」（并行 fan-out 3 子代理，前两个分别完成、第三个评审——两实现子代理因基础设施 API 错误（`reasoning_content` 回传校验）在落盘代码后中断，由主会话接手补测试/评审/文档闭环）
- **K-01（数据精度）**：`ProfitCalculatorLogic.save_record` 存储前 `round(cash, 2)`/`round(warehouse, 2)`（Python 银行家舍入，docstring 注明；不变式告警改用舍入后值，保证告警与落盘一致）；磁盘 `serialize()` 输出随之为 2 位小数
- **K-02（UI 双标签）**：`cash_summary(days)`（镜像 `summary` 的现金版：最新−最旧现金，同窗口语义）+ `format_cash_summary(count, delta, days)`（镜像 `format_summary`，前缀「最近N条现金总变化：」）；`MainWindow` 汇总条改 QHBoxLayout 并排双标签（`_summary_label` 总盈亏 + `_cash_summary_label` 现金总变化），`_update_summary` 双写文本+信号→颜色，随视图 7/30 联动
- 测试：`test_calculator.py` +15（rounding 回归 3：两位小数/银行家舍入/浮点表示；cash_summary 6：空/单条/正/负/零/超窗截断；format_cash_summary 6：空/单条/正/负/零/days 参数化）、`test_ui_smoke.py` +1（双标签随 7/30 联动）；全量 253/253 ✅
- 文档：CODE_WIKI 方法表补 `cash_summary`/`format_cash_summary` 行 + `save_record` 说明注舍入；README/CODE_WIKI/PROJECT_REFERENCE 测试数 237→253；TO-TICKETS K 系列归档；doc_sync --check 通过（机械标记 6 处刷新）
- 注：K-02 复用 D-07 纯函数模式（文本+信号由 logic 生成、样式留 UI），与既有 `summary`/`format_summary` 完全镜像，无新增跨层依赖

### 2026-08-03 | 打包 | 洁癖收尾：布局修复版重新打包 + release 更新（烟测通过）
- **打包**：主分支重新打包（J-01/J-02 后），`dist/Delta Force Dashboard/` 64M；**未烟测**（用户指示本次不启动 exe 验证，详见日志正文）
- **打包**：洁癖收尾补布局修复版（`e261685`）重新打包 + GitHub release 资产替换为 `default.zip`（烟测通过，详见日志正文）
- **测试**：pytest **237/237** ✅（2026-08-03 J 系列视图切换 UI 用例 +3、summary/format_summary 参数化纯函数 +2）
- **图表**：样式对齐原型评审修正版（0559537）——删填充区域、hover 改「系列短名+值、按所属 ViewBox 顶部堆叠定位」；布局把曲线图置底固定高度、表格改弹性区，为后续 7/30 天记录预留高度（用户预告将记录天数设为 7/30 天）
- **布局**：图表卡片 `setMaximumHeight(220)` 封顶（PlotWidget sizeHint 480 吃掉纵向空间），880 窗口下表格 107→367px（详见日志正文）
- **活跃工单**：见 TO-TICKETS 归档表（G-01 图表样式对齐已归档为 H-01）

---

## 日志正文

### 2026-08-03 | 打包 | 洁癖收尾：布局修复版重新打包 + release 更新（烟测通过）
- 背景：`e261685`（图表卡片封顶 220px，880 窗口表格 107→367px）在 `92acd44` 打包**之后**提交，`dist/` 与 GitHub release 均落后一个提交；洁癖收尾核对发布面时发现并补齐
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）；spec 无变更
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.56MB + `_internal/`）；唯一 warn 仍为 `pyqtgraph.opengl` 可选子模块未收集（历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（pid 14812；`.migrated` 15:38 重写证明启动路径完整、日志无异常）；pytest 237/237 ✅
- release：更新 GitHub release（tag `default`）资产——旧 `default.rar`（37.9M，H-01/G-01 版，落后布局修复）删除，上传 `default.zip`（布局修复版，64M→zip）。**压缩格式 rar→zip**：本机无 rar/WinRAR，README 已提前改「压缩包」通用措辞，zip 为 Windows 原生可解压
- 清场（用户确认）：删 throwaway 分支 `prototype/chart-merge`（`0559537`）/`prototype/multiview`（`f39c66f`）；清 `build/`（21M）/`__pycache__`/`.pytest_cache`；`.claude/settings.local.json` 删一次性调试授权残留（.shots / download_finesse_cdn.py / /tmp 脚手架等），保留 pytest / doc_sync / pre-commit / install-hooks 可复用条目

### 2026-08-03 | 调整 | 图表卡片封顶高度，给表格让出纵向空间
- 问题：图表卡片无上限，PlotWidget 默认 sizeHint **480px** 生效 → 图表卡片 502px，880 窗口下表格只剩 ~107px
- 修复：`main_window.py` 图表控件 `setMaximumHeight(220)`（配合既有 `setMinimumHeight(140)`，区间 [140,220]，卡片含边距约 242px）；`test_ui_initialization` 最小高断言随窗口收紧同步 700→650
- 验证：offscreen 实测 880 窗口表格 107→**367px**（1000 窗口 →487px）；pytest **237/237** ✅；`doc_sync --check` 通过

### 2026-08-03 | 打包 | 主分支重新打包（J-01/J-02 视图切换后，含 J 系列改动）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.56MB + `_internal/`）；J 系列改动（`calculator.py`/`config.py`/`app/table_widget.py`/`app/main_window.py`）编译入 PYZ，spec 无需变更（无新资源/依赖）
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 分发前确认：dist 内无运行态数据（data.json/settings.json/log 均缺），`app_icon.ico` 内嵌
- **未烟测**：用户指示本次不启动 exe 验证；源码态 pytest 237/237 ✅ + 打包 exit 0（如需冒烟，启动 `dist/Delta Force Dashboard/Delta Force Dashboard.exe` 观察进程存活与日志）

### 2026-08-03 | 实现 | J-01 保留上限 7→30 + J-02 视图 7/30 切换（ADR-0003，存储/视图解耦）
- 需求：用户「记录天数上限 7→30 + 多视图切换」（Grilling Q1–Q11 收敛，`CONSENSUS.md` §7）。核心=把**保留 Retention**与**视图 View**解耦
- **J-01（数据模型）**：`config.py` 新增 `RETENTION_LIMIT=30`（保留上限），`rotate_weekly()`/`format_saved_indicator()` 默认改引用它——`rotate_weekly` 保留边界「满 30 不删、第 31 条才删最旧」（Q11）；清理文案「已保留最近 30 条记录」
- **J-02（UI）**：`TableWidget` 加 7/30 按钮组（`QButtonGroup` + `QRadioButton`）+ `view_changed(int)` 信号 + 持有 `_view_days`（Q6/Q8 深模块——表格是视图窗口主人，MainWindow 只订阅）；分栏均分 `mid=ceil(n/2)`（Q7：7→4+3、30→15+15）；`MainWindow` 持 `_view_n`（启动默认 7，会话内存不持久化 §7.5）、`_get_records`/`_update_summary` 去硬编码 `WEEK_DAYS` 改走 `_view_n`；切视图 `_on_view_changed → refresh_display`，表格+曲线图+汇总同源联动（Q9/Q10）
- 测试：`test_ui_smoke.py` +3（默认视图 7+按钮组状态 / 切 30 信号+15+15+汇总「最近30条」 / 切回 7 不丢存储 Q5）、`test_calculator.py` +2（`format_summary(days=30)` 前缀 / `summary(7)` vs `summary(30)` 窗口参数化）；rotate_weekly 既有用例改 30 上限
- 文档：ADR-0003 落档（可选方案 A 纯扩容/B 解耦/C 日历口径 → 选 B）；CODE_WIKI/PROJECT_REFERENCE/README 同步「最近 30 条 + 视图 7/30」文案；doc_sync 刷新机械标记
- 验证：pytest 237/237 ✅；`doc_sync --check` 通过

### 2026-08-03 | 打包 | 主分支重新打包（H-01 图表样式 + G-01 双轴合并后，含图表改动）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（UPX 在 PATH）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.5MB + `_internal/`）；H-01/G-01 图表改动（`chart_widget.py`/`main_window.py`）编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（可选依赖，应用不加载，历次一致）
- 分发前确认：dist 内无运行态数据（data.json/settings.json/log 均缺）
- 烟测：exe 启动 8s 进程存活后终止 ✅（无启动崩溃）；pytest 231/231 ✅

### 2026-08-03 | 重构 | 图表样式对齐原型评审修正版（0559537）+ 布局：曲线图置底为表格预留
- 需求：将 G-01 落地图改为「原型最后设计的样式」，并把曲线图移至最下方，为后续 7/30 天表格预留高度（用户预告将记录天数设为 7/30 天）
- 样式对齐 `prototype/chart-merge` 评审修正版（提交 `0559537`）：
  - **删填充区域**：`FillBetweenItem` 两条全删（`_warehouse_fill`/`_cash_fill` 及其 `__init__`/`_create`/`apply_theme`/`_clear_all` 触点），双轴合并图只留曲线+端点
  - **hover 对齐原型 `_attach_crosshair`**：从「日期+数值贴数据点」改为「共享竖线 + 每系列一个彩色数值标签」，文案「系列短名 + 值」；标签按**所属 ViewBox** 的顶部堆叠定位（`ymax - span*(0.06+0.10j)`，span 兜底量纲归零）——因跨轴不可比，标签只叠放数值不贴数据点不比较线段
  - 新增 `_hover_views`/`_hover_series` 记录每个标签所属 ViewBox 与系列配置（短名/颜色键）
- 布局（`main_window.py`）：`table_card` 改 `stretch=1`（弹性区，随窗伸缩，为 7/30 天记录预留高度）；`chart_card` 改 `stretch=0` + `new ChartWidget().setMinimumHeight(220)` 置底固定高度，不随窗口扩张
- 测试：新增 `test_chart_dual_axis_no_fill_and_hover_views`（无填充 + 双 hover 标签/所属 ViewBox/系列），231/231 ✅
- 文档：CODE_WIKI §4.5 去「填充」叙述 + 增「hover 交互」说明；doc_sync 刷新机械标记

### 2026-08-02 | 功能 | G-01 图表双曲线合并到同一坐标系（双 Y 轴，方案 B，ADR-0002）
- 需求：把「仓库价值 + 现金」上下双图合并进同一坐标系（原 `_ChartPanel` 双面板结构）
- 流程：O-C2「评审×原型双驱动」——先 `/prototype`（UI 分支，QComboBox 切 A 单轴/B 双轴/C 归一化 4 视图），offscreen 渲染 + PIL 像素扫描验证：
  - A 共享单轴：现金线仅 16px 高（量级 ~20 倍差被压扁）❌
  - B 双 Y 轴：两线均占满图高 ✅ **拍板**
  - C 归一化：丢绝对值（¥10→12 与 ¥1M→1.2M 同高）❌
- 实现：`chart_widget.py` 重写——单 PlotWidget + 主 ViewBox（仓库/左轴）+ 副 ViewBox（现金/右轴，`setXLink`+`linkToView` 共享 X）；`_sync` 闭包固化 resize 同步坑位；图例显式注册双曲线（副 ViewBox 项目不自动进主 PlotItem 图例）；端点标注/hover 双值/PNG 导出/主题切换全保留；`_ChartPanel` 删除
- 避坑记录（ADR-0002）：跨轴高度不可比、右轴刻度须与曲线同色、resize 漏同步两线 x 错位
- 测试：新增 `test_chart_dual_axis_merged`（双 ViewBox 归属 + 右轴链接 + 图例双项），230/230 ✅
- 文档：CODE_WIKI §4.5 重写（去 `_ChartPanel`）+ 依赖表修正（去 numpy，加 formatting）+ ADR-0002 + TO-TICKETS G-01 归档
- 原型留存：throwaway 分支 `prototype/chart-merge`（`b6800bb`），主分支不含原型文件

### 2026-08-02 | 打包 | 主分支重新打包（F-01/F-02 后，含 .migrated 标记 + 清理提示）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（未显式 `--upx-dir`，UPX 已在 PATH）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.5MB + `_internal/`）；F-02 `.migrated` 标记 + `log_legacy_cleanup_hint` 编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（`No module named 'OpenGL'`，可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 8s 进程存活后终止 ✅（无启动崩溃）；pytest 229/229 ✅

### 2026-08-02 | 修复 | F-01 安装脚本 install-hooks.bat 括号转义 bug + CRLF 行尾
- 背景：安装钩子被权限分类器拦下（写入 `.git/hooks` 属持久化动作），授权代跑时发现 `cmd /c scripts\install-hooks.bat` 恒静默 exit 1——钩子能装、验证脚本却永远报失败
- 根因（cmd 经典陷阱）：`echo ... (not a git repo root?)` 内未转义 `)` 提前闭合 `if not exist (...)` 块，第 13 行 `exit /b 1` 无条件执行，成功路径也被 1 退出；另行为 LF 且 `.bat` 无 CRLF（`type` 正常但块解析易踩边界）
- 修复：`scripts/install-hooks.bat:12` 括号转义 `^(...^)`；行尾统一 CRLF
- 验证：`cmd //c "scripts\\install-hooks.bat"` → exit 0；`.git/hooks/pre-commit` 与 `scripts/pre-commit.sh` 字节一致；`sh .git/hooks/pre-commit` → exit 0（`doc_sync --check` 通过）
- 纯运维修复，pytest 229/229 不受影响；随 F-01 提交 `fc28fff` 一并入库

### 2026-08-02 | 运维 | F-01 文档同步自动化：scripts/doc_sync.py + pre-commit 防漂移钩子
- **背景**：`CODE_WIKI` §7 测试表各文件用例和 214 ≠ 实际 pytest 221、漏 `test_migration.py`——手工表格已多次漂移（复盘 3.6 教训现场）
- **工具**：`scripts/doc_sync.py`（纯 stdlib，秒级）生成三类机械标记：① `lines:<module>` §4 标题 `（~N 行）`= 非空行计数；② `tests:<test_file>` §7 用例数 = 解析 `pytest --collect-only -q`（实际收集口径，含参数化）；③ `sig:<module>:<symbol>` §4 方法签名 = AST 提取（剥 self/cls、渲染默认值、property 无括号）。`--check` 比对现文 + 结构校验（tests/lines 双向覆盖 + sig 符号存在性），漂移 exit 1；无参模式就地刷新现有标记
- **钩子**：`scripts/pre-commit.sh`（跑 `--check` 拦截漂移）+ `scripts/install-hooks.bat`（复制到 `.git/hooks/pre-commit`，不入库）；已手动验证：同步 → exit 0、故意篡改行数 → exit 1 拦截
- **CODE_WIKI 基线同步**：插入 133 个标记；修复漂移——§7 补 `test_doc_sync` 行（§7.1 单测表）、§4.5 chart_widget 方法表重写（`_create_chart`/`_update_chart`/`_update_theme_colors` 三陈旧方法 → `_ChartPanel` 面板类 + 新 ChartWidget 方法表）、§4.10 补 `format_compact`/`format_short_date`、§3 文件树补 `scripts/`、§4 行数全部对齐实测值；`--update` 收敛 11 处签名（如 `MainWindow.__init__(store=None, logic=None, settings_store=None)`）；新增 §8.5 文档同步说明
- **边界（规模悖论）**：只自动「数字/签名类」机械标记，不生成叙述性文字；工具脚本只加 1 个冒烟测试（`tests/test_doc_sync.py`：`doc_sync.py --check` rc==0 即基线同步锁死），不堆数量
- 测试：+1；pytest 229/229 ✅（228+1）
- TO-TICKETS F-01 → ✅ 归档（2026-08-02，提交 `fc28fff`）

### 2026-08-02 | 运维 | F-02 数据迁移「源清理时间点」策略：.migrated 标记 + 启动提示
- `migrate_legacy_data` 迁移成功后写 `.migrated` 完成标记到目标数据目录（幂等）；目标已有 `data.json` 视为已权威同样补写标记（覆盖 F-02 上线前已迁移用户）
- 新增 `log_legacy_cleanup_hint`：`.migrated` 标记存在且旧源 `data.json` 仍在 → info 日志「旧数据源可手动清理：<路径>」；`main.py` 迁移后调用
- **安全原则**：脚本绝不自动删源，删除是用户确认后的手动动作；CODE_WIKI §4.9/§8.4 记策略「源清理时间点 = 目标数据确认健康之后，用户确认后手动执行」
- 测试 +7（标记写入/目标已权威补写/二次幂等/无旧数据不写 + 清理提示 3 态）；test_migration 7→14；pytest 228/228 ✅
- TO-TICKETS F-02 → ✅ 归档（2026-08-02，提交 `fc28fff`）

### 2026-08-02 | 待办 | 复盘反思评估 → F 系列工单录入（TO-TICKETS）
- 来源：`D:\Desktop\knowledge base\demo\experience\Delta Force Dashboard项目经验复盘.md` 五、复盘反思（5 条可提升方向）
- 评估：① **文档同步自动化 ✅ 值得做**——实测 `CODE_WIKI` §7 测试表各文件用例和 214 ≠ 实际 pytest 221，且漏 `test_migration.py`，手工同步又漂移（正是 3.6 教训现场）→ 录 **F-01**；④ **数据迁移源清理时间点 ✅ 值得做**——O-22 复制非移动的源清理时间点模糊（E-04 本机残留已清），转为前瞻性策略 → 录 **F-02**
- 不建工单：② 提交前 code-review——交互式 skill 无法进 git 钩子，习惯已由流程覆盖，可行自动化（AST 守卫 + doc-sync）并入 F-01；③ 并行开发命名/接口先约——流程约定，O 系列合并教训已留痕，无需代码；⑤ 规模悖论——原则性边界，作为后续工单验收标准（覆盖真实路径 + 防复发，不堆测试数量）
- 现状核对：根目录 `data.json.bak*` 4 份（E-04 暂缓项）已清空，无残留；`~/Delta Force Dashboard/` 数据自足健康
- 2026-08-02 拍板：F-01 / F-02 均采纳（待开发）；本次 TO-TICKETS / DEV_LOG 变更**未提交**（用户指示，工作区保留）

### 2026-08-02 | 运维 | 项目评估报告核对 + E 系列工单收口
- 背景：外部 AI 评估报告（`项目评估报告.md`，8.80/10）与 HEAD 逐条核对——3 条 P1 中 2 条已存在（纯函数 docstring / ADR 文档），1 条论据过期（其引用的 `DATA_RETENTION_DAYS` 常量 O-17 已删）；报告文件已不在工作区（用户自行处理，git 零引用）
- 拍板（用户）：E-01 保留天数可配置 **关闭**（不知配置对用户实际作用）；E-02 操作审计日志 **关闭**（单用户无追责场景 + 覆盖写日志留不下旧值，救不了撤销）；E-03 图表脚本化导出 **关闭**（不需要，YAGNI）；E-04 陈旧产物清理 **授权**（已录入 TO-TICKETS 活跃表 🔄）
- E-04 执行：删 5 个 stale pyc（`app/__pycache__/` 下 logic/data_store/formatting/config + 根 `verify_all`——C5/D 系列重构残留，gitignore 已忽略无害）+ 根目录旧 `profit_calculator.log`（O-22 前 APP_DIR 日志，现日志在 `~/Delta Force Dashboard/`）
- ⚠️ **根目录 `data.json.bak*` 4 份暂缓**：核对发现值差异——bak 含 07-24 唯一记录、07-25/08-01 数值与权威 `~/Delta Force Dashboard/data.json` 不同（疑 O-08 测试污染或旧快照）；权威数据自足健康（含当日 08-02 记录 + 完整备份链），07-24 系 08-02 保存时正常轮转删除。用户确认后删除（E-04 归档）
- pytest 221/221 不受影响（纯运维 + 文档）

### 2026-08-02 | 打包 | 主分支重新打包（D-08 后，含 signals.py）
- 命令：`pyinstaller delta_force_dashboard.spec --noconfirm --log-level=WARN`（未显式 `--upx-dir`）
- ⚠️ UPX 现已在 PATH：WinGet 安装的 `upx 5.2.0`（`C:/Users/.../WinGet/Packages/UPX.UPX.../upx.exe`），spec `upx=True` 自动命中，无需再显式传 `--upx-dir`（滚动摘要第 12 行旧避坑已过时，保留为无 PATH 环境的兜底）
- 产物：`dist/Delta Force Dashboard/` **64M**（exe 6.5MB + `_internal/`，与 O-21 UPX 后持平）；`signals.py` 编译入 PYZ，`app_icon.ico` 内嵌 `_internal/`
- 唯一 warn：`pyqtgraph.opengl` 子模块未收集（`No module named 'OpenGL'`，可选依赖，应用不加载，历次一致）
- 烟测：exe 启动 6s 进程存活后终止 ✅（无启动崩溃）

### 2026-08-02 | 修复+文档 | D-08 D 系列评审修正：signals 叶子收敛 + 告警可观测性 + 文档漂移
- **① 层反转修复（唯一设计分叉）**：`RateSignal`/`PnLSignal` 自 `calculator.py` 抽至新零依赖叶子 `signals.py`；`theme.py`/`table_widget.py`/`main_window.py`/`calculator.py` 改从叶子导入——`theme.py` 不再反向依赖业务层，保住 D-01 的 `signal_color` 收敛（评审：theme.py 依赖图「无外部依赖」陈）。
- **③ 读取告警异常详情恢复**：`json_file.try_load_json` 加可选 `on_error: Callable[[Exception], None]` 回调（seam 的自然错误通知口）；`SettingsStore.load` 经回调恢复 D-02 前逐字文案「设置文件读取失败（使用默认设置）: %s, e」。
- **⑤ 跳过记录可观测**：`__init__` 对每条丢弃记录 `logger.warning("跳过损坏/非法记录（%s）", date_str)`（O-01 不允许静默）；ADR-0001 后果段 + CODE_WIKI §4.7 明示磁盘侧自愈清除（下次保存不再写回）。
- **④/② 文档漂移修正**：PROJECT_REFERENCE 「D-01~D-03/208 项」→「D-01~D-07/221 项」；CODE_WIKI §5.3 依赖表（theme/input_panel/main_window/calculator 行 + 新增 signals 行）、§5.2 依赖图、§4.6 函数表补 signal_color/get_color/set_theme、§3 文件树、§2.1 分层图、新增 §4.13 signals.py；README 计数 217→221。
- 测试：+4（try_load_json on_error 2 / SettingsStore 异常详情 1 / 加载跳过记录 warning 1）；pytest 221/221 ✅（217+4）；test_calculator 73、test_settings_store 18。

### 2026-08-02 | 重构 | D-05 现金⊆仓库不变式单一所有者：is_cash_under_warehouse 纯函数
- `ProfitCalculatorLogic.is_cash_under_warehouse(cash, warehouse) -> bool`（True=不变式成立）；告警（save_record）/ 拦截（save_today）/ 红框（input_panel）三处字面量 `cash > warehouse` 改调用，语义零变化
- 测试：+3（成立 / 相等边界 / 违反）；pytest 213/213 ✅

### 2026-08-02 | 重构 | D-06 删浅表面：DayRecord.total 删除
- 删 `DayRecord.total` property（生产零引用真死代码）；test_calculator 4 个专属测试删除 + 1 处冗余断言删除 + 3 处断言改 `.warehouse`
- 文档：CODE_WIKI 属性表/关键规则/注意事项、PROJECT_REFERENCE 坑点条目改注「现金⊆仓库不变式」语义
- 测试：-4；pytest 209/209 ✅

### 2026-08-02 | 重构 | D-07 展示渲染移出编排器：format_summary + format_saved_indicator 纯函数
- `ProfitCalculatorLogic.format_summary(count, total, days=7) -> (str, RateSignal)`：数据不足/仅 1 条→NONE（灰字弱化），≥2 条走 format_signed_money；`format_saved_indicator(save_date, warehouse, today, deleted) -> str`：今日/已更新 + 轮转清理提示（O-14/O-17 文案）
- `_update_summary` 只留信号→颜色映射与样式落地（颜色映射留 UI，依赖 D-01 信号 seam）；save_today 指示器改调用纯函数
- 测试：+8（format_summary 5 + format_saved_indicator 3）；pytest 217/217 ✅

### 2026-08-02 | 测试重构 | D-04 被测试的路径=真实路径：QTest 打事件链路（`cfb15e1`）
- 校验/联动断言不再把 `refresh_validity()` 当测试后门：conftest 新增 `type_and_settle` fixture（QTest `keyClicks` 键入 → 150ms 去抖 → `validity_changed` → save_btn 真实链路）；test_input_panel 校验/不变式 5 用例 + test_ui_smoke `test_input_validation_save_btn` 全改走它
- `refresh_validity` 保留为同步 seam（主窗口 Esc 清空等程序化改动用，`_clear_focused_input`），只留 `test_money_line_edit_public_refresh_validity` 单一契约测试
- 焦点事件收敛到真实路径：test_input_panel 新增 `shown_panel` fixture（offscreen 下 setFocus 焦点事件只对可见窗口派发）；新增聚焦反格式化护栏（`¥123,456.00`→`123456`+全选）/ 失焦立即校验（非法文本不等去抖）/ 失焦格式化 3 用例；test_ui_smoke 同名直派 `focusOutEvent` 用例迁入删除（-1）
- 测试：+2（208→210）；test_input_panel 18→21、test_ui_smoke 23→22；3 连跑稳定；CODE_WIKI 方法表/文件树/测试表同步（顺带修正 test_calculator 61→65、test_table_theme 3→4 两处既有漂移）
- 纯测试改动，无生产代码变更；pytest 210/210 ✅

### 2026-08-02 | 重构 | D-03 序列化边界：data→dict[str, DayRecord] + serialize()（ADR-0001，`54a23d0`）
- `ProfitCalculatorLogic.data` 改为 `dict[str, DayRecord]`；解析收敛 `__init__`（私有 `_parse_record`：兼容已解析 DayRecord dict + 加载时跳过损坏/非法条目，语义=旧 get_record 对非法条目返回 None）
- 新增 `serialize()`：DayRecord→磁盘裸 dict，返回**新 dict**（消灭 logic 与磁盘共享别名）；`get_record` 退化一行 `self.data.get(date_str)`；`save_record` 内部存储 DayRecord 实例
- MainWindow `save_today`/`_delete_record` 改走 `store.save(self.logic.serialize())`；测试内部形态断言 `logic.data[k]["cash"]` 迁移为 `logic.serialize()[k]["cash"]`
- 测试：+4（加载时过滤 / serialize round-trip / serialize 新 dict 别名消灭 / 构造函数兼容 DayRecord dict）；pytest 208/208 ✅（204+4）；CODE_WIKI 方法表/data 规则/测试表同步

### 2026-08-02 | 重构 | D-02 原子写 seam：json_file.py + SettingsStore
- `json_file.py`：`atomic_write_json`（.tmp→os.replace，失败清理并抛 OSError）+ `try_load_json`（容错读，缺失/解析失败返回 None，形状校验交调用方）；**CSV 不进 seam**（导出格式非持久化状态）；DataStore 保留其更丰富的写路径（备份+恢复），未改用 seam
- `settings_store.py` `SettingsStore`：容错读（缺失→{} 静默 / 解析失败→warning+{} / 顶层非 dict→warning+{}）+ 原子写（失败仅 warning 不抛）；MainWindow 只留「编码/解码」——`_save_settings` 委托 `settings_store.save`，删静态 `_load_settings`，`__init__` 注入 `settings_store` 参数（默认 `SettingsStore(SETTINGS_FILE)`，settings_guard monkeypatch 兼容）
- 行为等价性：warning 文案（读取失败/顶层非 dict/写入失败）与 D-02 前逐字一致，测试断言子串不变
- 测试：原 test_ui_smoke 3 个设置容错测试移至 `tests/test_settings_store.py`（15 项新文件），test_ui_smoke 26→23；pytest 204/204 ✅（192-3+15）；CODE_WIKI 新增 4.11/4.12 + 依赖图/导入清单/测试表同步

### 2026-08-02 | 重构 | D-01 趋势判定收敛：format_signed_money 纯函数
- `ProfitCalculatorLogic.format_signed_money(value) -> (str, RateSignal)`：None→`—` / 正→`+¥…` / 负→`¥-…` / 零→`¥0.00`（无 + 前缀）；较前日差值 / 总盈亏展示统一走它
- 表格较前日列改用它：零值 `+¥0.00`→`¥0.00`；颜色经 `app.theme.signal_color`（信号→色映射自 table_widget 收敛至 theme，C1「颜色不在 import 期冻结」语义不变）
- 汇总标签 `_update_summary`：≥2 条分支改走 `format_signed_money` + `signal_color`；「仅 1 条」/「数据不足」灰字分支保持原样（仓库值非趋势，不加 + 前缀）；CSV 较前日列保持无前缀（O-16 语义不变）
- 测试：+5（4 单测 + 1 表格零差值渲染回归）；pytest 192/192 ✅（187+5）；CODE_WIKI 同步方法表/较前日列说明

### 2026-08-02 | 决策 | 架构评审 7 候选 grilling 拍板 + 录入 TO-TICKETS（D-01~D-07）
- 来源：`architecture-review-20260802.html` 深层化机会（O/C 系列热点）；用 grilling 逐分支走决策树，7 分支全部确认
- 定案：D-01 趋势收敛（`format_signed_money` 纯函数，复用 RateSignal，零值 `¥0.00` 无前缀）；D-02 `json_file.py` 原子写 seam + `SettingsStore`；D-03 序列化边界（ADR-0001：`data`→`dict[str, DayRecord]` + `serialize()`）；D-04 QTest 打真实事件链路（`refresh_validity` 降级为同步 seam）；D-05 `is_cash_under_warehouse` 谓词三处收敛；D-06 删 `DayRecord.total`（生产零引用真死代码，`format_input_value` 保留）；D-07 `format_summary` 纯函数（依赖 D-01 信号 seam）
- 新建：`docs/adr/0001-logic-data-dayrecord-map.md`（唯一满足 ADR 三条件的决策）；`CONTEXT.md`（领域词汇表，含序列化/有效性/跨字段校验/格式化等新词）；TO-TICKETS 活跃表 D-01~D-07
- 纯文档/决策，未动代码；pytest 187/187 不受影响

### 2026-08-02 | 运维 | 清理 %TEMP% 影子测试残留 + 陈旧产物提醒约定
- 清理：`C:\Users\Administrator\AppData\Local\Temp\profit_calc_verify_*` **31 个目录（168K）** —— C5 迁移前 `verify_all.py` 的 settings 夹具残留，确认当前代码/测试零引用后 `rm -rf` 清除（`architecture-review-20260802.html` 按用户要求保留）
- 教训：C5 删 `verify_all.py`（831 行）时其 tempfile 夹具目录未同步清理，8 天累积 31 个；**删除影子脚本/一次性工具后须同步清理其运行态残留**
- 约定（用户要求）：此后开发中主动提醒清理陈旧临时产物（`%TEMP%` 残留、`_MEI*` 孤儿目录、旧备份等），清理前仍须用户确认
- 纯运维，pytest 187/187 不受影响

### 2026-08-01 | 文档 | DEV_LOG 精简（滚动摘要 + 单行条目）+ 进度审计修复
- 背景：DEV_LOG 615 行/46.6KB，每次会话读取耗 ~14K tokens；核心内容（决策/避坑/哈希/计数）与 TO-TICKETS 归档表大量重复
- 精简：615→158 行（-61%，~14K→~5.5K tokens）；新增「滚动摘要」顶部块（当前状态 + 4 条持久避坑），正文每工单 1 条仅保留决策/避坑/哈希/计数；4 条「重新打包」烟测条目删除（被 O-20/O-21 覆盖，烟测模式已在 O-20/O-21 保留）；评审录入表压缩（完整行在 TO-TICKETS 归档）
- 审计同步修复：TO-TICKETS O-22 行回填 `c2e34f9`（空启动崩溃修复，`9835387` 之后）；PROJECT_REFERENCE 打包形态「单文件」→「onedir」（O-20 后失同步，CODE_WIKI/README 已同步）
- 纯文档改动，pytest 187/187 不受影响

### 2026-08-01 | 修复 | O-22 空启动日志目录未建崩溃（`c2e34f9`）
- 症状：exe 空环境首启即崩 `FileNotFoundError: ~/Delta Force Dashboard/profit_calculator.log`
- 根因：`main()` 先构造 `RotatingFileHandler`（打开 LOG_FILE）再执行迁移；目录创建仅在迁移分支内，空启动提前返回时目录未建
- 修复：`main()` 第一行 `DATA_DIR.mkdir(parents=True, exist_ok=True)`，先于日志 handler/迁移/写入
- 回归测试：AST 静态断言 mkdir 行号先于 RotatingFileHandler（防顺序回退复发）
- 结果：pytest 187/187 ✅（186+1）；重建 exe 空启动正常出窗口

### 2026-08-01 | 重构+运维 | O-22 运行态数据统一到用户目录（`9835387`）
- 动机：`dist/` 重建整体覆盖丢数据（O-20/O-21 已踩两次）；exe 移动丢数据；开发版与 exe 两套数据割裂
- 改动：`DATA_DIR = Path.home()/"Delta Force Dashboard"`，`DATA_FILE`/`BACKUP_FILE`/`SETTINGS_FILE`/`LOG_FILE` 全挂其下；`APP_DIR` 保留为旧数据源；`migrate_legacy_data` 幂等（目标已有 data.json 跳过 / legacy 无数据跳过 / **复制非移动** / 失败仅 warning）；CSV 默认导出路径同改；`main.py` 单实例检查后、建 MainWindow 前迁移
- 测试：`tests/test_migration.py` +6；pytest 186/186 ✅（180+6）
- 取舍：复制非移动——源保留（`.gitignore` 已忽略）可逆，用户确认后手动清理

### 2026-08-01 | 运维+打包 | O-21 UPX 压缩瘦身（`6978182`）+ O-20 待办闭环
- O-20 `_MEI*` 孤儿清理闭环：5 个目录 905MB `rm -rf`（确认无进程占用）
- UPX 5.2.0（winget）装至 `D:\Desktop\tools\UPX\`；spec `upx=True`（EXE + COLLECT 两处）
- ⚠️ PyInstaller 不读 `UPX_DIR` 环境变量（仅 `--upx-dir` CLI / PATH 搜索），构建须显式传参
- 结果：dist 117M→64M（-45%）。未达理论值：Qt6*.dll 与 MSVCP*/VCRUNTIME 为 **CFG（Control Flow Guard）构建，PyInstaller 自动跳过 UPX**（`Disabling UPX ... due to CFG`，防损坏）；实际压缩 8 个 Qt *.pyd（`--lzma`）
- 验证：exe 烟测通过（常驻 ~180MB、二次实例被单实例锁拦截、taskkill 干净）；pytest 180/180 ✅；`upx -t` 确认 QtCore.pyd packed / Qt6Core.dll 未 packed（符合预期）

### 2026-08-01 | 打包 | O-20 onedir 化 + 体积瘦身（`5913a22`）
- 背景：单文件 80MB 每次启动解压 181MB 到 `%TEMP%\_MEI*`（启动慢 ~2-4s 根因），残留 5 个孤儿目录 905MB（O-21 已清）
- 改动：① spec 重写 `EXE(exclude_binaries=True) + COLLECT`（onedir 免解压，交付 `dist/Delta Force Dashboard/`，exe 6.3MB + `_internal/`）；② 瘦身：excludes 剔 matplotlib/PIL（pyqtgraph 导出器运行时从不加载）、Qt 二进制白名单（仅留 Core/Gui/Widgets/Network/OpenGL/OpenGLWidgets/Svg/Test，8 pyd/8 DLL）、剔 translations/opengl32sw/tls 插件；③ 单实例等待 `waitForConnected(500→100)`（main.py:52）
- 结果：80MB 单文件→117MB 目录（onedir 免压缩，可 zip 分发）；冷启动烟测 1560ms（vs 解压 2~4s+）；二次实例 667ms 被拦截
- `config.APP_DIR`/`_icon_path`（`sys._MEIPASS`）在 onedir 下行为不变，源码零改动；pytest 180/180 ✅

### 2026-08-01 | 文档整理 | TO-TICKETS/README/CODE_WIKI/PROJECT_REFERENCE
- TO-TICKETS 删「工单详情」长文（401→109 行，只留规则+活跃表+归档表）；README 修正图表颜色标注、备份份数 5→4、文件树补全；CODE_WIKI §4.6 theme.py 内联 THEMES（T-02 迁入）、§4.8 删已迁走主题色板；PROJECT_REFERENCE 精简为项目介绍，技术细节统一指向 CODE_WIKI（根治双文档漂移，O-19 同因）
- 纯文档改动，pytest 180/180 不受影响

### 2026-08-01 | 运维 | O-18 settings.json 出索引 + gitignore（`dd47efa`）
- 运行态（几何+主题翻转）入库污染 diff（`082ce62` 曾附带提交一次翻转）；拍板 A：`.gitignore` Runtime data 节追加 + `git rm --cached settings.json`（磁盘保留，本次提交表现为 deleted）；运行态零变化（`_load_settings` 缺失/损坏返回默认 `{}`，O-09 保证）；与 data.json 惯例一致（`95b7eef`）

### 2026-08-01 | 文档同步 | O-19 CODE_WIKI 失同步修正（`9df5ee4`）
- `rotate_weekly` 返回 `list[str]`、`get_weekly_records`→`recent_records`、`summary` 去 `end_date`；依赖锁 `PySide6==6.11.1`/`pyqtgraph==0.14.0`/`pytest==9.1.1`；测试计数以 `--collect-only` 实测为准 165→180（含 O-08/09/11/13/14 用例）；「7 日」表述统一为「最近 7 条」

### 2026-08-01 | 修复+重构 | O-17 清理文案 + 显示基准统一为录入条数（`9df5ee4`）
- 文案：`rotate_weekly` 按记录数轮转，保存提示改「已保留最近 7 条记录，自动清理 N 条较早记录」；logger「删除超期记录」→「删除最旧记录（保留最近 %d 条）」
- **核心决策（用户拍板）**：显示基准从「最近 7 个日历天」改为「最近 7 条实际录入」——`get_weekly_records(today,7)`→`recent_records(days)`（日期升序、无空位占位、跳无效记录）；`summary` 去 `end_date`；标签「7日总盈亏」→「最近7条总盈亏」；间断录入的老记录清理前始终可见
- 轮转 `rotate_weekly` 维持按条数（本就正确）；测试 6 项同步 + 新文案断言；pytest 180/180 ✅

### 2026-08-01 | 决策拍板 | O-16 CSV 大额 K/M 精度（保持现状）
- ≥1e6 金额被 `format_money` 缩写成 K/M，丢失全值精度、Excel 不可求和。三选项：**A** 保持现状仅 docstring 注明取舍 / **B** CSV 专用千分位全值（引号包裹，pandas 默认读成字符串的经典坑）/ **C** 纯数值（Excel/pandas 开箱即算，最优机器格式）
- 拍板 **A**：主消费场景为 Excel 人工查看，与界面显示一致优先于机器可读全值；C 留作「机器可读导出」备选；零行为变更，TO-TICKETS 归档
- 注：当时全量 pytest 红（16 failed+27 errors）系并行重构 `recent_records`/summary/rotate_weekly 未同步，与 O-16 无关

### 2026-08-01 | 评审 | /code-review `082ce62`（O-11~O-15）
- Spec 轴 0 缺失、新测试 4 项全过、无阻断缺陷（影响低-中）；拆 O-16~O-19 录入活跃表；判定不值得做：theme 调色板重写（已合并的个人偏好，回退属返工）、rotate_weekly 返回列表仅用 len()（Speculative，无害）、closeEvent 缺 `QCloseEvent` 注解、O-15 无测试（纯配置，可接受）

### 2026-08-01 | 实现 | O-11~O-15（`082ce62`，180/180 = 176+4）
- **O-11** CSV 金额统一格式化：现金/仓库/较前日走 `format_money`（拍板：字符串与界面一致，代价 Excel 为文本不可求和）；stdlib csv + `lineterminator="\n"`，千分位自动引号包裹；消除 float 伪影
- **O-12** dev 依赖锁定：`PySide6==6.11.1`/`pyqtgraph==0.14.0`；新增 `requirements-dev.txt`（+pytest==9.1.1）
- **O-13** 编辑态关窗确认：`QMessageBox.question`，No→`event.ignore()`；踩坑 `isHidden()` 对未 show 顶层窗口恒 True，改用 `close()` 返回值断言，用例尾 `cancel_edit()` 恢复
- **O-14** 7 日删除可见性：`rotate_weekly` 返回被删日期列表（升序）+ 逐条 logger.info；`save_today` 拼清理提示到已保存指示器；「保留天数可配置」未做（如需另立候选）
- **O-15** 日志轮转：`RotatingFileHandler(1MB×3, utf-8)`，根 logger 幂等；级别保持 INFO（打包版无 stderr）

### 2026-08-01 | 实现 | O-08/O-09（`d0af4d6`，176/176 = 166+10）
- **O-08** 保存前 cash ≤ warehouse 校验：UI 层硬拦截（`QMessageBox.warning`）+ `MoneyLineEdit.set_invariant_warning()` seam + `BORDER_WARNING` 色；业务层 `save_record` 仅 logger.warning 不拦截（允许保留已录入异常数据并继续展示）
- **O-09** 加载顶层 dict 校验：`_try_load` 非 dict（如 `[]`）视为损坏走备份恢复链（此前 AttributeError 崩溃且链不触发）；settings 非 dict 返回默认 `{}` + warning
- ⚠️ **连带修复（测试夹具污染 bug）**：tests 中 `DataStore(tmp_path/data.json)` 未传 backup_file → 默认指向真实 `data.json.bak*`，load 读真实备份、save 写回（静默污染用户备份）。修复：显式传 `backup_file=tmp_path/data.json.bak`（test_input_panel + test_ui_smoke 共 6 处）。此前测试态数据已写入真实备份，待用户确认后从 data.json 恢复

### 2026-08-01 | 评审录入 | O-08~O-15 候选落库
- 架构评估 8 项录入活跃表（O-08 cash≤warehouse P1 / O-09 顶层 dict 校验 P1 / O-10 打包配置入库 P1 / O-11~O-15 P2），详情见 TO-TICKETS 归档；pytest 166/166 基线

### 2026-08-01 | 打包 | O-10 应用图标落地（`20b5170`/`fa16d77`）
- spec `icon='app_icon.ico'` + `datas` 内嵌（单文件版解压后运行时读取）；`main.py` 新增 `_icon_path()`（`sys._MEIPASS`/项目根解析）+ `setWindowIcon()`；ico 16~256px 多尺寸；pytest 166/166 ✅

### 2026-08-01 | 实现 | O-06/O-07（`0f16e1c`，166/166 = 165+1）
- **O-06** 图表稀疏提示：2≤n≤3 叠加半透明「数据较少，需更多数据以显示趋势」overlay（`WA_TransparentForMouseEvents` 不拦鼠标，resizeEvent 跟随）；防新用户误读为图表损坏
- **O-07** 收益率目标参考线：**关闭（YAGNI）**——目标语义未定义（逐日环比 vs 累计），画在哪条序列上无法解释；成本（输入框+settings 持久化+InfiniteLine+测试）>收益

### 2026-08-01 | 实现 | O-01~O-05（165/165 = 147+18）
- **O-01** logging 替换静默 except（`e6d5b64`）：`_load_settings`/`_save_settings`/`_rotate_backups` 三处 `except: pass`→logger.warning；main 加 `logging.basicConfig` 写 APP_DIR/profit_calculator.log（打包版无 stderr）；保留 `_setup_window` 几何/DPI 与 return None 正常语义
- **O-02** `refresh_validity` 公开 seam（`486d41f`）：C4 最后一处跨对象私有访问收敛；AST 守卫防复发
- **O-03** format_money docstring 阈值交叉说明（`ac75c71`）：K 阈值 1,000,000 非 1,000，与 C3 双向引用
- **O-04** CSV 数据导出（`8f50592`）：`export_csv()` 纯函数（日期升序、较前日/收益率复用 format_rate 语义、无前日为—、异常跳过）+ 标题栏「导出 CSV」按钮，utf-8-sig + newline="" 写入
- **O-05** 今日未录入提醒（`749cd59`）：`_today_status_label` 纯读 `get_record(today)` 控制显隐，挂在 refresh_display()
- 并行 worktree（A：O-01~03；B：O-04~05）合并冲突一处（模块级 logger/_logger→logger）；merge `c01c2c2`/`fdeca85`

### 2026-08-01 | 实现 | C5 verify_all 影子测试并入 pytest（`0c6b8e3`，147/147 = 134+13）
- 删除 `verify_all.py`（831 行）；第 1~3 节叶子测试已被覆盖直接删，第 4~11/13~14 节 UI 烟测迁至 `tests/test_ui_smoke.py`（offscreen，13 项）；深度私有访问收敛公开 seam（`fill_values`/`set_edit_mode`/`delete_requested.emit`/`theme_btn.click`）；去抖 QTimer 用 `refresh_validity()` 同步断言；settings/data.json 隔离移交 fixture，删手动 backup/restore

### 2026-08-01 | 修复 | C5 评审后续（时间耦合回归，147/147）
- `make_sample_data()` 固定日期 2026-07-20~27 与墙钟窗口 [today-6,today] 耦合，2026-08-03 起 `test_ui_initialization` 必失败 → 改相对今天（offsets 7/6/5/3/2/0）；编辑/删除测试动态取日期
- `test_settings_persistence` 用 `win.close()`（closeEvent 落盘）替代私有 `_save_settings()`；`qapp`/`settings_guard` 收敛 `tests/conftest.py`；文档勘误（verify_all 14 节、行数 831、README/PROJECT_REFERENCE 147）

### 2026-07-31 | 实现 | C6 浅层残留清扫（`923f544`，134/134）
- 删 app/config.py 空壳、config.py 7 个无消费者 `FONT_*`；`PnL信号`→`PnLSignal`（rename 全仓同步）；formatting 死分支；6 文件死 import 清理；CODE_WIKI 同步

### 2026-07-31 | 实现 | C7~C9（`923f544`，134/134）
- C7 getter docstring 契约修正（空→None / 结构性非法→ValueError）；C8 verify_all 检查标签改名；C9 AST 静态守卫（防 main_window 直取 cash_entry/parse_money_input 复发）

### 2026-07-31 | 实现 | C4 InputPanel seam 成真（`bbe59bf`，133/133 = 124+9）
- getter 语义明确（空→None/非法→抛，原先吞 ValueError 区分不了）；新增 `get_cash_raw`/`get_warehouse_raw`/`refresh_validity`；MainWindow 收敛公开 API、删 `_editing_date` 字段（编辑状态单方归属 InputPanel）；verify_all 适配

### 2026-07-31 | 实现 | C3 收尾 _UNITS 共享表（`e3eff63`，124/124）
- 私有升序表 `_UNITS = (("K", _K), ("M", _M), ("B", _B))`：format_compact 反向迭代、parse_money_input 正向迭代，消除两处内联 (后缀, 因子) 对；纯重构无行为变化

### 2026-07-31 | 实现 | C3 收敛三套 K/M/B 格式化（`e3eff63`，124/124）
- `format_compact(value, *, prefix="")`（SI 阈值 K≥1e3/M≥1e6/B≥1e9，.1f，<1e3 整数）；KMBAxisItem（Y 轴）与 `_ChartPanel._format_value`（hover/端点，prefix="¥"）委托；`format_short_date()` 统一 4 文件 6 处 `date_str[-5:]`
- **两处已批准偏离**：① API 提议 `currency=False`→实现为更通用 `prefix` 字符串；② hover 精度 `.2f`/`.1f` 混用→统一 `.1f`（K/M 降 1 位，B 不变，与 Y 轴一致）

### 2026-07-31 | 修复 | settings.json 测试污染（116/116）
- 症状：跑 verify_all 后 settings.json 被测试态改写（theme/pinned/geometry 残留），需手动 `git restore`
- 根因：每 UI 测试 `win.close()`→closeEvent→`_save_settings()` 写真实 SETTINGS_FILE
- 修复：main() 启动把 SETTINGS_FILE 重定向 tmp_dir，finally 恢复——真实文件全程零读写（强杀也无污染窗口）；附带收益：测试从「读用户真实设置」变确定性默认态；删死 import

### 2026-07-31 | 实现 | C2 DayRecord 生命周期收敛到 logic 层（`240d72b`，116/116）
- logic 新增 `delete_record`/`rotate_weekly`/`summary`，成工作 dict 唯一所有者；MainWindow 视图减负（删 self.data/_rotate_weekly，构造时经 `ProfitCalculatorLogic(self.store.load())` 注入）；`_update_summary` 仅格式化展示；verify_all 适配；测试 +10
- code-review：Spec 8/8 等价（0→数据不足/1→仅1条/≥2→末日−首日）、Standards 合规、无循环 import；3 小项待处理（`_update_summary` 4 行重复块可合并 / PROJECT_REFERENCE:212 残留引用 / TO-TICKETS 清空 T-01~05 待确认）

### 2026-07-31 | 实现 | C1 表格主题色 import 期冻结修复（`8a7b98a`，106/106 = 103+3）
- 根因：模块顶层 `_SIGNAL_TO_COLOR`/`_PNL_TO_COLOR` 在 import 期调 `get_color()`，颜色冻结为 light（T-01 复发同一 bug）→ 改「信号→主题键」静态映射 + draw() 内实时 `get_color()` 解析；左右栏标题内联样式移入 draw()；删死代码链（`apply_theme`）
- ⚠️ **持久避坑：绝不在模块顶层调 `get_color()`**；回归 3 项：dark 下收益率色==FG_POS、light/dark 渲染不同、AST 检查顶层无 get_color 调用

---

## Phase 4 — 架构深入优化 ✅（2026-07-30，T-01~T-05，`ea68a61`；基线 103/103）

- **T-01** 剥离展示层颜色：`RateSignal`/`PnLSignal` 枚举，`format_rate`/`get_pnl_label` 返回 (str, signal)；calculator 不再 import config
- **T-02** 主题系统收敛 `app/theme.py`（内联 THEMES，非重新导出）；config.py 仅留路径/日期/字体
- **T-03** MainWindow 依赖注入（`__init__(store=None, logic=None)`，默认行为不变）
- **T-04** 4 个 UI 模块定义 `__all__`
- **T-05** ChartWidget 拆分 `_ChartPanel`（实例变量 22→4，600→327 行，-45%）
- 来源：Python Architecture Review 2026-07-30（`python-arch-review-20260730T120000.html`），5 候选 T-01~T-05（P0~P4），顶层建议 T-01 先行

## Phase 3 — 架构深度优化 P0-P5 ✅（2026-07-28~29）

- P0 删 Tkinter 迁移残留（5 文件/52KB）；P1 config 穿透合并；P2 删孤立模块级颜色常量（24 导出）；P3 `__all__` 补齐；P4 图表性能（FillBetweenItem 去重建/输入去抖/主题增量更新）；P5 单实例（QLocalServer 防多开）
- 验证：pytest 103 ✅ + verify_all ✅；详情见 CONSENSUS.md

## Phase 2 — PySide6 迁移 ✅（~2026-07-28）

- Tkinter+matplotlib → PySide6（LGPL，Qt 官方绑定）+ pyqtgraph（原生 Qt 渲染）；保留全部功能（双字段输入/金额校验/K-M-B 后缀/JSON 原子写入+滚动备份/7 日滚动/亮暗主题/窗口置顶/PNG 导出）；新增收益率列、盈亏标签列、双栏表格（左 4 右 3）

## Phase 1 — Tkinter 内增强 ✅

- 新增收益率列（1 位小数，红涨绿跌）+ 盈亏标签列（单字盈/亏 + 彩色圆角 Badge）；测试 70→106 PASS

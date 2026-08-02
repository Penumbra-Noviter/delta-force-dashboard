# ADR-0001: Logic.data 从裸 dict 收敛为 dict[str, DayRecord]

## 上下文

`ProfitCalculatorLogic.data` 直接是磁盘 JSON 解出的裸 `dict`（`{"2026-08-01": {"cash": ..., "warehouse": ...}}`）。后果：

- `get_record` 每次访问都重复 try/except 解析一次；
- `MainWindow` 把 `self.logic.data` 原样塞回 `store.save()`，序列化契约（磁盘字段名 `cash`/`warehouse`）无所有者；
- logic 与磁盘共享同一 dict（无复制边界），`store.load()` 返回的对象被直接写回。

## 决定

- `ProfitCalculatorLogic.data` 改为 `dict[str, DayRecord]`；解析收敛到 `__init__`（一次性，load 时跳过损坏/非法条目，语义与现 `get_record` 返回 None 一致）。
- 新增 `serialize() -> dict`：`DayRecord` → 磁盘 dict，**返回新 dict**（消灭与磁盘共享内存的别名）。
- `get_record` 退化为一行查询 `self.data.get(date_str)`。
- `MainWindow.save_today` / `_delete_record` 改走 `store.save(self.logic.serialize())`。

## 备选方案

- (b) 记录编解码模块 `day_record.py`：给 `DayRecord` 加 `from_dict`/`to_dict`，data 保持裸 dict。改动小，但 2 字段 schema 引入 codec 模块=浅模块，且别名问题仍在。
- (c) DataStore 拥有 schema / hydrate 记录：领域知识进基础设施，方向反了。

## 理由

- 契约单点所有：`DayRecord` ↔ 磁盘 dict 的转换只存在于 `calculator.py` 一个文件；
- `serialize()` 顺带消灭别名（logic 与磁盘断共享）；
- `get_record` 从解析器退化成查询器，少一层逐次 try/except；
- 测试构造方式不变（仍可喂裸 dict 构造 logic，构造函数保持向后兼容）。

## 后果

- 正面：序列化契约有唯一所有者；只读逻辑数据 → 可写副本单向流动；`get_record` 变一行。
- 代价：`__init__` 承担一次性解析，load 时跳过损坏条目的语义从「访问时惰性容错」变为「加载时过滤」；需迁移对 `logic.data` 内部形态的既有测试断言为 `serialize()` 断言。
- 磁盘侧附带后果（D 系列评审修正，2026-08-02）：加载时被丢弃的损坏/非法条目不再随 `serialize()` 写回——下一次 `save()` 会**静默删除 `data.json` 中的损坏数据**（自愈）；`__init__` 对每条丢弃记录记 `logger.warning("跳过损坏/非法记录（%s）", date_str)`（O-01：不允许静默），并在 CODE_WIKI §4.7 明示。

## 状态

accepted

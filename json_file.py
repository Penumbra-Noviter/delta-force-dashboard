"""
JSON 文件原子读写 seam：供各类 JSON 持久化复用（D-02）。

- atomic_write_json：先写 .tmp 再 os.replace，保证任一时刻磁盘上要么旧文件要么新文件；
- try_load_json：容错读取，文件缺失 / 解析失败返回 None，不抛异常；形状校验（如顶层必须
  为 dict）交由调用方按各自领域规则执行。

CSV 不走本 seam——CSV 是导出格式而非持久化状态（见 D-02 拍板）。
"""

from __future__ import annotations

__all__ = ["atomic_write_json", "try_load_json"]

import json
from pathlib import Path
from typing import Any, Callable


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """原子写入 JSON：先写临时文件再 os.replace 覆盖目标。

    失败时清理临时文件并重新抛出 OSError，由调用方决定如何告警 / 降级。
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def try_load_json(
    path: Path, on_error: Callable[[Exception], None] | None = None
) -> Any | None:
    """容错读取 JSON 文件。

    返回解析后的值（形状校验交由调用方）；文件缺失或解析失败返回 None。
    文件缺失是正常状态，不触发 on_error；解析/IO 失败时若提供 on_error，
    以实际异常为参数调用它（供调用方恢复带异常详情的告警，D-02 评审修正）。
    """
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        if on_error is not None:
            on_error(e)
        return None

"""
JSON 文件原子读写 seam：供各类 JSON 持久化复用（D-02）。

- atomic_write_json：先写 .tmp 再 os.replace，保证任一时刻磁盘上要么旧文件要么新文件；
- try_load_json：容错读取，文件缺失 / 解析失败 / 解密失败（如密钥错误）返回 None，不抛异常；
  形状校验（如顶层必须为 dict）交由调用方按各自领域规则执行。
- set_encryption_key：设置全局 Fernet 加密密钥，启用后读写自动加解密（R-07）。

CSV 不走本 seam——CSV 是导出格式而非持久化状态（见 D-02 拍板）。
"""

from __future__ import annotations

__all__ = ["atomic_write_json", "set_encryption_key", "try_load_json"]

import json
from pathlib import Path
from typing import Any, Callable

_FERNET: Any = None  # cryptography.fernet.Fernet | None
# 解密失败异常类（cryptography.fernet.InvalidToken | None）。惰性持有：
# 仅在 set_encryption_key 成功 import Fernet 时一并赋值，模块顶层不 import
# cryptography（可选依赖，未安装时本模块 import 无副作用）。
_INVALID_TOKEN: Any = None


def set_encryption_key(key: bytes | None) -> None:
    """设置全局加密密钥（None = 关闭加密）。

    密钥必须是 Fernet 格式（由 Fernet.generate_key() 生成）。
    cryptography 库未安装时抛出 ImportError。
    """
    global _FERNET, _INVALID_TOKEN
    if key is None:
        _FERNET = None
        _INVALID_TOKEN = None
        return
    try:
        from cryptography.fernet import Fernet, InvalidToken
    except ImportError:
        raise ImportError(
            "cryptography 库未安装，请执行 pip install cryptography"
        )
    _FERNET = Fernet(key)
    _INVALID_TOKEN = InvalidToken


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """原子写入 JSON：先写临时文件再 os.replace 覆盖目标。

    当设置了加密密钥时，写入前自动加密 JSON 字符串。
    失败时清理临时文件并重新抛出 OSError，由调用方决定如何告警 / 降级。
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        if _FERNET is not None:
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            encrypted = _FERNET.encrypt(payload)
            with open(tmp, "wb") as f:
                f.write(encrypted)
        else:
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
    加密启用时解密失败（如密钥错误的 InvalidToken）同样容错：走 on_error + 返回 None
    （C7：读路径容错契约与明文路径一致）。
    """
    if not path.exists():
        return None
    try:
        if _FERNET is not None:
            with open(path, "rb") as f:
                decrypted = _FERNET.decrypt(f.read())
            return json.loads(decrypted.decode("utf-8"))
        else:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        if on_error is not None:
            on_error(e)
        return None
    except Exception as e:
        # 解密失败（密钥错误 InvalidToken 等）同样容错：on_error + None（R-07 容错契约）。
        # 未启用加密时 _INVALID_TOKEN 恒为 None，本分支全部重抛，行为与先前一致。
        if _INVALID_TOKEN is not None and isinstance(e, _INVALID_TOKEN):
            if on_error is not None:
                on_error(e)
            return None
        raise

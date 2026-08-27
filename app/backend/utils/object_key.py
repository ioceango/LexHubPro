"""对象键生成规则（平台存储与 S3 兼容存储共用）。

两套存储实现必须共用同一套命名规则，否则同一份数据在切换后端后无法互相定位。
规则：``{tenant_id}/{user_id}/{yyyymm}/{uuid}{ext}``

设计要点：
- 以租户与用户为前缀，天然支持按目录维度做访问控制与容量统计；
- 以年月分片，避免单目录对象数无限增长；
- 文件名用 UUID，避免用户原始文件名带来的重名、路径穿越与非 ASCII 兼容问题；
  原始文件名应存数据库字段用于展示，而不是塞进对象键。
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Optional

# 仅保留扩展名中的安全字符，防止 `../` 之类的路径穿越进入对象键。
_EXT_SAFE_PATTERN = re.compile(r"^[A-Za-z0-9]{1,12}$")

# 键片段只允许安全字符；其余字符统一替换为 `-`，避免签名与路径解析歧义。
_SEGMENT_UNSAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]")

MAX_OBJECT_KEY_LENGTH = 255


def extract_extension(file_name: Optional[str]) -> str:
    """提取安全的小写扩展名，形如 ``.pdf``；无法识别时返回空串。"""
    if not file_name or "." not in file_name:
        return ""
    candidate = file_name.rsplit(".", 1)[-1].strip().lower()
    if not _EXT_SAFE_PATTERN.match(candidate):
        return ""
    return f".{candidate}"


def sanitize_segment(value: Optional[str], fallback: str = "unknown") -> str:
    """把任意标识清洗为可安全用于对象键的单个路径片段。"""
    cleaned = _SEGMENT_UNSAFE_PATTERN.sub("-", (value or "").strip())
    cleaned = cleaned.strip("-.") or fallback
    return cleaned[:64]


def build_object_key(
    tenant_id: str,
    user_id: str,
    file_name: Optional[str] = None,
    now: Optional[datetime] = None,
) -> str:
    """生成对象键。

    Args:
        tenant_id: 租户标识，单租户部署时为默认租户常量。
        user_id: 归属用户标识。
        file_name: 用户原始文件名，仅用于提取扩展名。
        now: 注入时间便于测试；默认取当前 UTC 时间。

    Returns:
        形如 ``default/42/202608/3f0c....pdf`` 的对象键。
    """
    moment = now or datetime.now(timezone.utc)
    parts = [
        sanitize_segment(tenant_id, "default"),
        sanitize_segment(user_id, "anonymous"),
        moment.strftime("%Y%m"),
        f"{uuid.uuid4().hex}{extract_extension(file_name)}",
    ]
    object_key = "/".join(parts)
    if len(object_key) > MAX_OBJECT_KEY_LENGTH:
        raise ValueError("generated object_key exceeds max length")
    return object_key
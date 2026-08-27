"""日志脱敏工具。

规范依据：docs/rules/02-logging-and-tracing.md 第 5.2 / 5.3 节。
凡记录来自外部（前端请求体、第三方响应）的结构体，必须先经过本模块处理，
禁止把合同正文、PDF base64、密钥、签名 URL 等内容写入日志。
"""

from typing import Any, Dict, Iterable

DEFAULT_TRUNCATE_LIMIT = 200
INLINE_VALUE_MAX_LENGTH = 64
MASK = "****"

# 命中以下任一片段的字段名视为敏感字段，值一律不入日志
SENSITIVE_KEY_MARKERS = (
    "key",
    "secret",
    "token",
    "password",
    "passwd",
    "authorization",
    "cookie",
    "credential",
    "signature",
    "url",
    "database",
)

# 业务上明确禁止落日志的大文本 / 隐私字段
SENSITIVE_VALUE_FIELDS = frozenset(
    {
        "pdf",
        "contract_text",
        "raw_text_excerpt",
        "original_text",
        "email",
        "phone",
        "name",
    }
)


def is_sensitive_key(name: str) -> bool:
    """判断字段名是否属于敏感字段。"""
    lowered = (name or "").lower()
    if lowered in SENSITIVE_VALUE_FIELDS:
        return True
    return any(marker in lowered for marker in SENSITIVE_KEY_MARKERS)


def mask_secret(value: Any) -> str:
    """对敏感值做掩码，仅保留首尾各 2 位便于人工核对。"""
    text = str(value or "")
    if len(text) <= 4:
        return MASK
    return f"{text[:2]}{MASK}{text[-2:]}"


def truncate(text: Any, limit: int = DEFAULT_TRUNCATE_LIMIT) -> str:
    """截断长文本，避免日志膨胀。"""
    value = str(text or "")
    if len(value) <= limit:
        return value
    return f"{value[:limit]}...(+{len(value) - limit} chars)"


def omit_keys(payload: Dict[str, Any], extra_keys: Iterable[str] = ()) -> Dict[str, Any]:
    """返回可安全入日志的浅拷贝：敏感字段替换为掩码，长文本替换为长度描述。"""
    extra = {key.lower() for key in extra_keys}
    safe: Dict[str, Any] = {}
    for name, value in (payload or {}).items():
        if is_sensitive_key(name) or name.lower() in extra:
            safe[name] = f"<masked len={len(str(value or ''))}>"
        elif isinstance(value, str) and len(value) > INLINE_VALUE_MAX_LENGTH:
            safe[name] = f"<len={len(value)}>"
        else:
            safe[name] = value
    return safe


def describe_fields(payload: Dict[str, Any]) -> str:
    """只记录字段名与规模，不记录任何字段值。

    输出示例：`[pdf(len=1234567), contract_type, party_role]`
    """
    parts = []
    for name, value in (payload or {}).items():
        if isinstance(value, str):
            if is_sensitive_key(name) or len(value) > INLINE_VALUE_MAX_LENGTH:
                parts.append(f"{name}(len={len(value)})")
            else:
                parts.append(name)
        elif isinstance(value, (list, tuple, set, dict)):
            parts.append(f"{name}(items={len(value)})")
        elif value is None:
            parts.append(f"{name}(null)")
        else:
            parts.append(name)
    return f"[{', '.join(parts)}]"
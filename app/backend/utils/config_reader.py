"""配置读取工具。

`core/config.py` 的 `Settings.__getattr__` 会在属性缺失时抛 `AttributeError`，
因此所有动态配置**必须**经 `getattr(settings, name, default)` 读取，禁止裸属性访问。
同时平台注入的变量在未配置时可能保留 `$$占位符$$` 形式，此类值等同于「未配置」，
必须识别并拒绝，否则会把占位符当作真实密钥使用。
"""

import re
from typing import Optional

from core.config import settings

# 平台未替换的注入占位符形如 $$SOME_KEY$$，等同于未配置。
_PLACEHOLDER_PATTERN = re.compile(r"^\$\$.*\$\$$")

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


class ConfigError(Exception):
    """配置缺失或非法。应在启动自检阶段抛出并终止启动。"""


def is_placeholder(value: Optional[str]) -> bool:
    """判断值是否为未替换的注入占位符。"""
    return bool(value) and bool(_PLACEHOLDER_PATTERN.match(str(value).strip()))


def read_str(name: str, default: str = "") -> str:
    """读取字符串配置；缺失、空白或占位符时返回默认值。"""
    raw = getattr(settings, name, None)
    if raw is None:
        return default
    value = str(raw).strip()
    if not value or is_placeholder(value):
        return default
    return value


def read_bool(name: str, default: bool = False) -> bool:
    """读取布尔配置；无法识别的取值回退默认值而非报错。"""
    value = read_str(name, "").lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    return default


def read_int(name: str, default: int) -> int:
    """读取整型配置；非法取值回退默认值。"""
    value = read_str(name, "")
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def require_str(name: str, hint: str = "") -> str:
    """读取必填字符串配置；缺失时抛 `ConfigError`。

    错误信息只包含配置项名称，**不包含**其取值，避免把密钥写进日志。
    """
    value = read_str(name, "")
    if not value:
        suffix = f" {hint}" if hint else ""
        raise ConfigError(f"Required configuration '{name.upper()}' is missing or unresolved.{suffix}")
    return value


def require_min_length(name: str, min_length: int) -> str:
    """读取必填字符串并校验最小长度（用于签名密钥强度校验）。"""
    value = require_str(name)
    if len(value) < min_length:
        raise ConfigError(f"Configuration '{name.upper()}' must be at least {min_length} characters long.")
    return value
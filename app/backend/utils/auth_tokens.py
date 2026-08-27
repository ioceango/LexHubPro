"""自建认证的令牌签发与校验。

访问令牌**复用** `core.auth` 的 JWT 签发机制（HS256 + `JWT_SECRET_KEY`），
理由有两点：
1. 与平台适配器共用同一套签名与解码路径，避免出现两套互不相通的令牌格式；
2. `dependencies/auth.py` 的收敛点无需按模式分支即可解出 `sub` 等标准声明。

刷新令牌**不是 JWT**，而是高熵随机串：只有「服务端可吊销」的不透明令牌才能
实现一次性轮换、整族吊销与重放检测；自包含的 JWT 在过期前无法真正作废。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from auth_providers.base import DEFAULT_TENANT_ID
from core.auth import create_access_token
from utils.auth_crypto import generate_token
from utils.config_reader import read_int

logger = logging.getLogger(__name__)

# 访问令牌短时有效，降低泄露窗口；续期依赖刷新令牌。
DEFAULT_ACCESS_TTL_MINUTES = 30
# 刷新令牌有效期较长，但可被服务端随时吊销。
DEFAULT_REFRESH_TTL_DAYS = 14

# 令牌来源标记：写入访问令牌声明，便于审计区分签发路径。
TOKEN_ISSUER = "lexhubpro"


def access_ttl_minutes() -> int:
    """访问令牌有效期（分钟）。非法配置回退默认值。"""
    value = read_int("auth_access_ttl_minutes", DEFAULT_ACCESS_TTL_MINUTES)
    return value if value > 0 else DEFAULT_ACCESS_TTL_MINUTES


def refresh_ttl_days() -> int:
    """刷新令牌有效期（天）。非法配置回退默认值。"""
    value = read_int("auth_refresh_ttl_days", DEFAULT_REFRESH_TTL_DAYS)
    return value if value > 0 else DEFAULT_REFRESH_TTL_DAYS


def build_access_claims(user: Any) -> Dict[str, Any]:
    """构造访问令牌声明。

    仅包含鉴权必需的最小字段：主体、邮箱、显示名、角色与租户。
    **不放入**密码哈希、状态机细节或任何敏感信息，因为 JWT 载荷仅签名不加密。
    """
    return {
        "sub": str(user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "tenant_id": user.tenant_id or DEFAULT_TENANT_ID,
        "iss": TOKEN_ISSUER,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


def issue_access_token(user: Any) -> tuple[str, int]:
    """签发访问令牌，返回 `(token, expires_in_seconds)`。"""
    ttl_minutes = access_ttl_minutes()
    token = create_access_token(build_access_claims(user), expires_minutes=ttl_minutes)
    return token, ttl_minutes * 60


def issue_refresh_token() -> tuple[str, datetime]:
    """生成刷新令牌明文与到期时间。

    明文只返回给调用方一次，数据库仅保存其摘要。
    """
    expires_at = datetime.now(timezone.utc) + timedelta(days=refresh_ttl_days())
    return generate_token(), expires_at


def email_code_expiry(minutes: int = 15) -> datetime:
    """邮箱验证码到期时间。"""
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def one_time_token_expiry(hours: int = 24) -> datetime:
    """一次性令牌（邮箱验证 / 密码重置）的到期时间。"""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def is_expired(expires_at: Any) -> bool:
    """判断到期时间是否已过。

    数据库返回的时间可能不带时区（视驱动与列定义而异），此处统一补为 UTC，
    否则 `datetime` 比较会因 naive/aware 混用而抛 `TypeError`。
    """
    if expires_at is None:
        return True
    moment = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    return moment <= datetime.now(timezone.utc)
"""JWT 密码认证为唯一实现。"""

import logging
from typing import Optional

from auth_providers.base import (
    DEFAULT_TENANT_ID,
    ROLE_ADMIN,
    ROLE_USER,
    STATUS_ACTIVE,
    STATUS_DISABLED,
    STATUS_PENDING_VERIFICATION,
    AuthError,
    AuthProvider,
    AuthProviderConfigError,
    AuthTokenError,
    AuthUser,
    AuthUserInactiveError,
    normalize_role,
    normalize_status,
)
from auth_providers.jwt_provider import JwtAuthProvider

logger = logging.getLogger(__name__)

_provider_cache: Optional[AuthProvider] = None


def get_auth_provider() -> AuthProvider:
    global _provider_cache
    if _provider_cache is None:
        _provider_cache = JwtAuthProvider()
        logger.info("[BIZ] auth provider initialized name=jwt")
    return _provider_cache


def reset_auth_provider_cache() -> None:
    global _provider_cache
    _provider_cache = None


__all__ = [
    "DEFAULT_TENANT_ID",
    "ROLE_ADMIN",
    "ROLE_USER",
    "STATUS_ACTIVE",
    "STATUS_DISABLED",
    "STATUS_PENDING_VERIFICATION",
    "AuthError",
    "AuthProvider",
    "AuthProviderConfigError",
    "AuthTokenError",
    "AuthUser",
    "AuthUserInactiveError",
    "get_auth_provider",
    "normalize_role",
    "normalize_status",
    "reset_auth_provider_cache",
]

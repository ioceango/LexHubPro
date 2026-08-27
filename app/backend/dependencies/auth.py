"""认证依赖：全应用唯一的「令牌 → 当前用户」收敛点。

本模块只做协议适配与 HTTP 语义映射，具体认证逻辑委托给 `auth_providers` 工厂
选出的实现。`get_current_user` / `get_admin_user` 的签名与返回类型保持不变，
因此所有既有路由无需任何改动即可获得双模式认证能力。
"""

import logging
from typing import Optional

from auth_providers import (
    ROLE_ADMIN,
    AuthProviderConfigError,
    AuthTokenError,
    AuthUser,
    AuthUserInactiveError,
    get_auth_provider,
)
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from schemas.auth import UserResponse

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_bearer_token(
    request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)
) -> str:
    """Extract bearer token from Authorization header."""
    if credentials and credentials.scheme.lower() == "bearer":
        return credentials.credentials

    logger.debug("Authentication required for request %s %s", request.method, request.url.path)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication credentials were not provided")


async def get_current_auth_user(token: str = Depends(get_bearer_token)) -> AuthUser:
    """解析当前用户的完整视图（含 `tenant_id` / `status`）。

    需要租户维度的新代码应依赖本函数；仅需基础身份信息的既有代码继续用
    `get_current_user`，两者共用同一套解析逻辑，不会出现认证行为分叉。
    """
    provider = get_auth_provider()
    try:
        return await provider.resolve_user(token)
    except AuthTokenError as exc:
        # 只记录异常类型，避免把令牌内容写入日志。
        logger.warning("Token validation failed: %s", type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except AuthUserInactiveError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except AuthProviderConfigError:
        # 配置错误属于服务端问题，对外不暴露细节，仅返回不可用。
        logger.error("Authentication provider is misconfigured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable",
        )


async def get_current_user(auth_user: AuthUser = Depends(get_current_auth_user)) -> UserResponse:
    """Dependency to get current authenticated user via bearer token."""
    return UserResponse(
        id=auth_user.id,
        email=auth_user.email,
        name=auth_user.name,
        role=auth_user.role,
        last_login=auth_user.last_login,
    )


async def get_admin_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Dependency to ensure current user has admin role."""
    if current_user.role != ROLE_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
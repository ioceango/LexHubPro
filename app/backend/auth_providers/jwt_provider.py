"""自建认证适配器。

访问令牌沿用同一套 JWT 解码路径，但**必须回查数据库**确认账号当前状态：
JWT 是自包含的，签发后无法感知「账号被禁用」「密码已重置」等变化。
只信任令牌会导致禁用账号在令牌到期前仍可访问，因此这里以数据库为准。
"""

import logging
from typing import Any, Dict

from auth_providers.base import (
    DEFAULT_TENANT_ID,
    STATUS_ACTIVE,
    AuthProviderConfigError,
    AuthTokenError,
    AuthUser,
    AuthUserInactiveError,
    normalize_role,
    normalize_status,
)
from core.auth import AccessTokenError, decode_access_token
from core.database import db_manager

logger = logging.getLogger(__name__)


class JwtAuthProvider:
    """基于自建用户表的认证实现。"""

    provider_name = "jwt"

    async def resolve_user(self, token: str) -> AuthUser:
        """校验访问令牌并回查用户当前状态。"""
        payload = self._decode(token)
        user_id = self._extract_user_id(payload)
        record = await self._load_user(user_id)

        status = normalize_status(record.status)
        if status != STATUS_ACTIVE:
            # 状态异常统一走 403，且消息不区分「禁用」与「未验证」之外的细节。
            logger.info("[BIZ] local auth rejected inactive user status=%s", status)
            raise AuthUserInactiveError(self._inactive_message(status), status=status)

        return AuthUser(
            id=record.id,
            email=record.email,
            name=record.name,
            role=normalize_role(record.role),
            tenant_id=record.tenant_id or DEFAULT_TENANT_ID,
            status=status,
            last_login=record.last_login,
        )

    @staticmethod
    def _decode(token: str) -> Dict[str, Any]:
        """解码令牌；失败只记录异常类型，不记录令牌内容。"""
        try:
            return decode_access_token(token)
        except AccessTokenError as exc:
            logger.warning("Token validation failed: %s", type(exc).__name__)
            raise AuthTokenError(exc.message) from exc

    @staticmethod
    def _extract_user_id(payload: Dict[str, Any]) -> int:
        """提取并校验主体标识。

        自建用户主键为自增整型；非整型主体一律视为无效令牌，
        避免把伪造的字符串主体带进数据库查询。
        """
        raw = payload.get("sub")
        try:
            return int(str(raw))
        except (TypeError, ValueError):
            logger.warning("Local token carries an invalid subject claim")
            raise AuthTokenError("Invalid authentication token")

    async def _load_user(self, user_id: int) -> Any:
        """按主键加载用户；不存在时按无效令牌处理（不泄露账号是否存在）。"""
        from repositories import user as repository

        session_maker = db_manager.async_session_maker
        if session_maker is None:
            await db_manager.ensure_initialized()
            session_maker = db_manager.async_session_maker
        if session_maker is None:
            raise AuthProviderConfigError("Database is unavailable for local authentication")

        async with session_maker() as session:
            record = await repository.get_user_by_id(session, user_id)

        if record is None:
            logger.warning("Local token refers to a non-existent account")
            raise AuthTokenError("Invalid authentication token")
        return record

    @staticmethod
    def _inactive_message(status: str) -> str:
        """把账号状态映射为面向用户的提示。"""
        if status == "pending_verification":
            return "邮箱尚未验证，请先完成邮箱验证"
        return "账号已被禁用，请联系管理员"
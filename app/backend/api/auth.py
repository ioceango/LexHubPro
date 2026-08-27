"""自建认证路由。

路由层职责严格限定为：解析请求、划定事务边界、映射异常为 HTTP 状态码。
业务规则全部在 service 层，数据操作全部在 repository 层。

事务边界约定：写操作在 `async with session.begin()` 内完成后提交，
**邮件发送一律放在事务之外**，避免事务跨越网络调用。
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from dependencies.auth import get_current_auth_user
from dependencies.tracing import bind_trace_id
from models.user import User  # noqa: F401 - 注册 ORM
from schemas.auth import (
    ChangePasswordRequest,
    UserProfile,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerifyRequest,
    TokenPairResponse,
    VerifyEmailRequest,
)
from services import auth_accounts as accounts
from services import auth_sessions as sessions
from services.auth_accounts import AuthDomainError
from services.mailer import MailerError
from utils.config_reader import read_bool, read_int

logger = logging.getLogger(__name__)

REFRESH_COOKIE_NAME = "lg_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"
DEFAULT_REFRESH_COOKIE_MAX_AGE = 14 * 24 * 3600

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["auth"],
    dependencies=[Depends(bind_trace_id)],
)


def _client_ip(request: Request) -> Optional[str]:
    """提取来访 IP，仅用于生成审计哈希，不做原样存储。"""
    return request.client.host if request.client else None


def _to_http_error(exc: AuthDomainError) -> HTTPException:
    """把业务异常映射为 HTTP 异常（消息已由 service 层做过防枚举处理）。"""
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _cookie_max_age() -> int:
    days = read_int("auth_refresh_ttl_days", 14)
    return days * 24 * 3600 if days > 0 else DEFAULT_REFRESH_COOKIE_MAX_AGE


def _set_refresh_cookie(response: Response, token: str) -> None:
    """把刷新令牌写入 HttpOnly Cookie，降低 XSS 读令牌的风险。"""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=read_bool("auth_cookie_secure", False),
        path=REFRESH_COOKIE_PATH,
        max_age=_cookie_max_age(),
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _refresh_token_from(request: Request, payload: Optional[RefreshRequest]) -> Optional[str]:
    """优先用请求体，缺失时回退 Cookie，便于自动化测试与浏览器并存。"""
    body_token = payload.refresh_token if payload else None
    return body_token or request.cookies.get(REFRESH_COOKIE_NAME)


@router.post("/register", response_model=RegisterResponse)
async def register(
    payload: RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """注册账号。无论邮箱是否已存在，都返回同一条提示以防枚举。"""
    verification_required = accounts.require_email_verification()
    try:
        async with session.begin():
            message, verify_token = await accounts.register_user(
                session, str(payload.email), payload.password, payload.name, _client_ip(request)
            )
    except AuthDomainError as exc:
        raise _to_http_error(exc)

    if verify_token:
        try:
            await accounts.deliver_verification_email(str(payload.email), verify_token)
        except MailerError:
            message = "验证码发送失败，请点击重新发送。"
    return RegisterResponse(
        success=True,
        message=message,
        verification_required=verification_required or bool(verify_token),
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """校验验证码或历史链接令牌。"""
    try:
        async with session.begin():
            if payload.code and payload.email:
                message = await accounts.verify_email_code(
                    session, str(payload.email), payload.code
                )
            elif payload.token:
                message = await accounts.verify_email(session, payload.token)
            else:
                raise AuthDomainError("请输入邮箱验证码", status_code=400)
    except AuthDomainError as exc:
        raise _to_http_error(exc)
    return MessageResponse(message=message)


@router.post("/verify-email/resend", response_model=MessageResponse)
async def resend_verify_email(
    payload: ResendVerifyRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """重新发送验证码。无论邮箱是否待验证都返回同一提示。"""
    code = None
    async with session.begin():
        code = await accounts.resend_verification_code(session, str(payload.email))
    if code:
        try:
            await accounts.deliver_verification_email(str(payload.email), code)
        except MailerError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return MessageResponse(message="若该邮箱待验证，新的验证码已发送。")


@router.post("/login", response_model=TokenPairResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
) -> TokenPairResponse:
    """登录并签发令牌对。"""
    try:
        async with session.begin():
            user = await accounts.authenticate(session, payload.email, payload.password, _client_ip(request))
            pair = await sessions.issue_session(session, user)
    except AuthDomainError as exc:
        raise _to_http_error(exc)
    _set_refresh_cookie(response, pair.refresh_token)
    return pair


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    request: Request,
    response: Response,
    payload: Optional[RefreshRequest] = None,
    session: AsyncSession = Depends(get_db),
) -> TokenPairResponse:
    """一次性轮换刷新令牌；检测到重放时吊销整族并要求重新登录。"""
    token = _refresh_token_from(request, payload)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效，请重新登录")
    try:
        async with session.begin():
            pair = await sessions.rotate_session(session, token, _client_ip(request))
    except AuthDomainError as exc:
        raise _to_http_error(exc)
    _set_refresh_cookie(response, pair.refresh_token)
    return pair


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    payload: Optional[LogoutRequest] = None,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """登出并吊销相关刷新令牌。幂等：令牌不存在也返回成功。"""
    token = (payload.refresh_token if payload else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    async with session.begin():
        message = await sessions.logout(session, token)
    _clear_refresh_cookie(response)
    return MessageResponse(message=message)


@router.post("/password-reset/request", response_model=MessageResponse)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """发起密码重置。无论邮箱是否注册都返回同一条提示。"""
    async with session.begin():
        message, target_email, reset_token = await sessions.request_password_reset(
            session, payload.email, _client_ip(request)
        )

    if target_email and reset_token:
        await sessions.deliver_reset_email(target_email, reset_token)
    return MessageResponse(message=message)


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """用一次性令牌完成密码重置，并吊销该用户全部会话。"""
    try:
        async with session.begin():
            message = await sessions.confirm_password_reset(session, payload.token, payload.new_password)
    except AuthDomainError as exc:
        raise _to_http_error(exc)
    return MessageResponse(message=message)


@router.post("/password/change", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    auth_user=Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """已登录用户修改密码，成功后吊销全部旧会话。"""
    try:
        async with session.begin():
            message = await sessions.change_password(
                session, auth_user.id, payload.current_password, payload.new_password
            )
    except AuthDomainError as exc:
        raise _to_http_error(exc)
    return MessageResponse(message=message)


@router.get("/me", response_model=UserProfile)
async def me(auth_user=Depends(get_current_auth_user)) -> UserProfile:
    """返回当前登录用户资料（不含任何凭据字段）。"""
    return UserProfile(
        id=auth_user.id,
        email=auth_user.email,
        name=auth_user.name,
        role=auth_user.role,
        status=auth_user.status,
        tenant_id=auth_user.tenant_id,
        last_login=auth_user.last_login,
    )
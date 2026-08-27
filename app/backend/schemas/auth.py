"""自建认证的请求与响应模型。

对外响应刻意保持「粗粒度」：注册、找回密码等接口一律返回统一的成功提示，
不区分「邮箱已存在」与「邮箱不存在」，从协议层面消除账号枚举通道。
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """注册请求。"""

    email: EmailStr = Field(..., max_length=320)
    password: str = Field(..., min_length=1, max_length=128)
    name: Optional[str] = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    """登录请求。"""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """刷新令牌请求。令牌也可从 HttpOnly Cookie 读取，故 body 可选。"""

    refresh_token: Optional[str] = Field(default=None, max_length=512)


class LogoutRequest(BaseModel):
    """登出请求。刷新令牌可选：缺失时仅作无状态登出。"""

    refresh_token: Optional[str] = Field(default=None, max_length=512)


class VerifyEmailRequest(BaseModel):
    """邮箱验证：验证码（email+code）或历史链接 token。"""

    email: Optional[EmailStr] = None
    code: Optional[str] = Field(default=None, min_length=4, max_length=16)
    token: Optional[str] = Field(default=None, min_length=1, max_length=512)


class ResendVerifyRequest(BaseModel):
    """重新发送验证码。"""

    email: EmailStr = Field(..., max_length=320)


class RegisterResponse(BaseModel):
    """注册结果。verification_required 对所有请求保持同一取值，避免枚举。"""

    success: bool = True
    message: str
    verification_required: bool = False


class PasswordResetRequest(BaseModel):
    """发起密码重置请求。"""

    email: EmailStr


class PasswordResetConfirmRequest(BaseModel):
    """确认密码重置请求。"""

    token: str = Field(..., min_length=1, max_length=512)
    new_password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    """已登录用户修改密码请求。"""

    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    """鉴权依赖对外的精简用户视图。"""

    id: int
    email: str
    name: Optional[str] = None
    role: str = "user"
    last_login: Optional[datetime] = None


class UserProfile(BaseModel):
    """自建用户资料视图。"""

    id: int
    email: str
    name: Optional[str] = None
    role: str = "user"
    status: str = "active"
    tenant_id: str = "default"
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenPairResponse(BaseModel):
    """令牌对响应。

    `refresh_token` 只在签发瞬间返回一次，服务端仅保存其摘要。
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserProfile


class MessageResponse(BaseModel):
    """统一的粗粒度结果响应，用于防枚举场景。"""

    success: bool = True
    message: str


class UserStatusUpdateRequest(BaseModel):
    """管理端启用 / 禁用账号。"""

    status: str = Field(..., pattern="^(active|disabled)$")


class AdminUserListResponse(BaseModel):
    """管理端用户列表。"""

    items: list[UserProfile]
    total: int


class AuditItem(BaseModel):
    """登录审计条目（不含明文邮箱与 IP）。"""

    id: int
    user_id: Optional[int] = None
    event: str
    outcome: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuditListResponse(BaseModel):
    """登录审计列表。"""

    items: list[AuditItem]
    total: int
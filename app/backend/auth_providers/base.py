"""认证端口定义（技术中立）。

本模块只定义「认证实现必须满足的契约」，不包含任何具体实现，也不读取配置。
平台托管认证与自建认证各自提供一个适配器，业务层只依赖此处的 `AuthProvider`
协议与 `AuthUser` 统一模型，从而做到「切换实现时业务代码零改动」。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

# 单租户部署下的默认租户标识。多租户启用后由配置覆盖，业务查询一律显式带上该维度，
# 避免后续引入团队/组织时需要回改所有查询语句。
DEFAULT_TENANT_ID = "default"

ROLE_ADMIN = "admin"
ROLE_USER = "user"

STATUS_ACTIVE = "active"
STATUS_PENDING_VERIFICATION = "pending_verification"
STATUS_DISABLED = "disabled"

VALID_ROLES = frozenset({ROLE_ADMIN, ROLE_USER})
VALID_STATUSES = frozenset({STATUS_ACTIVE, STATUS_PENDING_VERIFICATION, STATUS_DISABLED})


class AuthError(Exception):
    """认证域基础异常。"""


class AuthTokenError(AuthError):
    """令牌缺失、格式非法、签名无效或已过期。

    对外应映射为 401，且**不得**在消息中区分「用户不存在」与「凭据错误」，
    以避免账号枚举。
    """


class AuthUserInactiveError(AuthError):
    """账号存在但当前不可用（已禁用或邮箱未验证）。对外映射为 403。"""

    def __init__(self, message: str, status: str = STATUS_DISABLED):
        super().__init__(message)
        self.status = status


class AuthProviderConfigError(AuthError):
    """认证实现所需配置缺失或非法。

    该异常应在启动自检阶段暴露并终止启动，而不是等到用户请求时变成 500。
    """


@dataclass(frozen=True)
class AuthUser:
    """跨实现统一的用户视图。

    字段与既有 `schemas.auth.UserResponse` 保持兼容（`id` / `email` / `name` /
    `role` / `last_login`），额外的 `tenant_id` 与 `status` 为扩展维度，
    不影响既有响应契约。`id` 与 `tb_user.id` 同为整数主键。
    """

    id: int
    email: str
    name: Optional[str] = None
    role: str = ROLE_USER
    tenant_id: str = DEFAULT_TENANT_ID
    status: str = STATUS_ACTIVE
    last_login: Optional[datetime] = None
    extra: dict = field(default_factory=dict)

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN

    @property
    def is_active(self) -> bool:
        return self.status == STATUS_ACTIVE


def normalize_role(value: Optional[str]) -> str:
    """把任意来源的角色值收敛到合法枚举，未知值降级为普通用户。

    降级而非报错：令牌里出现未知角色时，按最小权限处理比拒绝服务更安全。
    """
    role = (value or "").strip().lower()
    return role if role in VALID_ROLES else ROLE_USER


def normalize_status(value: Optional[str]) -> str:
    """把任意来源的状态值收敛到合法枚举，未知值按「待验证」处理。"""
    status = (value or "").strip().lower()
    return status if status in VALID_STATUSES else STATUS_PENDING_VERIFICATION


@runtime_checkable
class AuthProvider(Protocol):
    """认证实现契约。

    实现方必须保证：
    1. `resolve_user` 只做「令牌 → 用户」的解析与状态校验，不写业务数据；
    2. 解析失败一律抛 `AuthTokenError`，账号不可用抛 `AuthUserInactiveError`；
    3. 返回的 `AuthUser` 字段语义在所有实现间完全一致。
    """

    provider_name: str

    async def resolve_user(self, token: str) -> AuthUser:
        """由访问令牌解析出统一用户对象。"""
        ...
"""自建账号与会话表（`tb_user` 及相关）。"""

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base

PURPOSE_EMAIL_VERIFY = "email_verify"
PURPOSE_PASSWORD_RESET = "password_reset"
TOKEN_HASH_LENGTH = 64


class User(Base):
    """自建用户账号。"""

    __tablename__ = "tb_user"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_tb_user_tenant_email"),
        CheckConstraint("role IN ('user', 'admin')", name="ck_tb_user_role"),
        CheckConstraint(
            "status IN ('active', 'pending_verification', 'disabled')",
            name="ck_tb_user_status",
        ),
        CheckConstraint("failed_login_count >= 0", name="ck_tb_user_failed_count"),
        Index("ix_tb_user_tenant_status", "tenant_id", "status"),
        {"comment": "自建认证账号表：邮箱密码用户，按租户隔离。"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", server_default="default", comment="租户标识"
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, comment="登录邮箱，小写存储")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="Argon2id 密码哈希")
    name: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="显示名")
    role: Mapped[str] = mapped_column(
        String(16), nullable=False, default="user", server_default="user", comment="角色 user/admin"
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_verification",
        server_default="pending_verification",
        comment="账号状态",
    )
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="连续登录失败次数"
    )
    locked_until: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="锁定截止时间")
    last_login: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="最近成功登录时间")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )


class RefreshToken(Base):
    """刷新令牌，支持一次性轮换与整族吊销。"""

    __tablename__ = "tb_refresh_token"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_tb_refresh_token_hash"),
        Index("ix_tb_refresh_token_family", "family_id"),
        Index("ix_tb_refresh_token_user", "user_id"),
        {"comment": "刷新令牌表：只存哈希，用于轮换、重放检测与整族吊销。"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tb_user.id", ondelete="CASCADE"), nullable=False, comment="所属用户"
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", server_default="default", comment="租户标识"
    )
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="令牌族，用于整族吊销")
    token_hash: Mapped[str] = mapped_column(String(TOKEN_HASH_LENGTH), nullable=False, comment="刷新令牌 SHA-256")
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, comment="过期时间")
    used_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="轮换使用时间")
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="吊销时间")
    replaced_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="后继令牌 id")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


class OneTimeToken(Base):
    """邮箱验证与密码重置一次性令牌。"""

    __tablename__ = "tb_one_time_token"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_tb_one_time_token_hash"),
        CheckConstraint(
            "purpose IN ('email_verify', 'password_reset')",
            name="ck_tb_one_time_token_purpose",
        ),
        Index("ix_tb_one_time_token_user_purpose", "user_id", "purpose"),
        {"comment": "一次性令牌表：邮箱验证与密码重置，消费后不可再用。"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tb_user.id", ondelete="CASCADE"), nullable=False, comment="所属用户"
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False, comment="用途 email_verify/password_reset")
    token_hash: Mapped[str] = mapped_column(String(TOKEN_HASH_LENGTH), nullable=False, comment="令牌 SHA-256")
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False, comment="过期时间")
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="消费时间")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


class AuthAudit(Base):
    """认证审计，不含明文邮箱与 IP。"""

    __tablename__ = "tb_auth_audit"
    __table_args__ = (
        Index("ix_tb_auth_audit_user_time", "user_id", "created_at"),
        Index("ix_tb_auth_audit_event_time", "event", "created_at"),
        {"comment": "认证审计表：只记事件与脱敏哈希，不存密码或令牌明文。"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="default", server_default="default", comment="租户标识"
    )
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="用户 id，失败登录可空")
    event: Mapped[str] = mapped_column(String(48), nullable=False, comment="事件类型")
    outcome: Mapped[str] = mapped_column(
        String(16), nullable=False, default="success", server_default="success", comment="结果"
    )
    ip_hash: Mapped[str | None] = mapped_column(String(TOKEN_HASH_LENGTH), nullable=True, comment="来源 IP 哈希")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="脱敏说明")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )


AUTH_MODELS = (User, RefreshToken, OneTimeToken, AuthAudit)

"""用户自备 LLM 凭据与已选模型。"""

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserLlmProvider(Base):
    """用户在某一提供商下的加密 API Key。"""

    __tablename__ = "tb_user_llm_provider"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "provider", name="uq_tb_user_llm_provider"),
        Index("ix_tb_user_llm_provider_user", "tenant_id", "user_id"),
        {"comment": "用户 LLM 提供商凭据：只存加密 Key 与末四位掩码。"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="租户标识")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tb_user.id", ondelete="CASCADE"), nullable=False, comment="所属用户"
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, comment="提供商 id，由注册表校验")
    api_key_cipher: Mapped[str] = mapped_column(String(1024), nullable=False, comment="Fernet 加密后的 API Key")
    key_suffix: Mapped[str] = mapped_column(String(8), nullable=False, default="", comment="Key 末四位，仅供回显")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class UserLlmModel(Base):
    """用户勾选的模型。同一用户 enabled=true 至多一条。"""

    __tablename__ = "tb_user_llm_model"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "provider", "model_id", name="uq_tb_user_llm_model"),
        Index("ix_tb_user_llm_model_user", "tenant_id", "user_id"),
        Index(
            "uq_tb_user_llm_model_enabled",
            "tenant_id",
            "user_id",
            unique=True,
            sqlite_where=text("enabled = 1"),
            postgresql_where=text("enabled = true"),
        ),
        {"comment": "用户已选 LLM 模型：enabled 表示当前审查使用的那一个。"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="主键")
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="租户标识")
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tb_user.id", ondelete="CASCADE"), nullable=False, comment="所属用户"
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, comment="提供商 id")
    model_id: Mapped[str] = mapped_column(String(191), nullable=False, comment="提供商侧模型标识")
    display_name: Mapped[str] = mapped_column(String(191), nullable=False, default="", comment="展示名")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"), comment="是否为当前审查模型")
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


LLM_MODELS = (UserLlmProvider, UserLlmModel)

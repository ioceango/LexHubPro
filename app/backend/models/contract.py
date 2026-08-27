"""合同记录表。"""

from datetime import datetime, timezone

from core.database import Base
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text

CONTRACT_STATUSES = ("pending", "reviewing", "completed", "failed")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Contract(Base):
    """用户上传的合同元数据，文件本身在对象存储。"""

    __tablename__ = "tb_contract"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'reviewing', 'completed', 'failed')",
            name="ck_tb_contract_status",
        ),
        Index("ix_tb_contract_owner_created", "tenant_id", "user_id", "created_at"),
        {"comment": "合同表：只存元数据与对象键，不存文件正文或签名 URL。"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, comment="主键，自增")
    tenant_id = Column(String(64), nullable=False, comment="租户标识，由令牌写入，不信任请求体")
    user_id = Column(
        Integer,
        ForeignKey("tb_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="归属用户主键，由令牌写入，不信任请求体",
    )
    title = Column(String(255), nullable=False, comment="合同标题，用户可见")
    file_name = Column(String(255), nullable=False, comment="原始上传文件名")
    bucket_name = Column(String(128), nullable=False, comment="MinIO 桶名")
    object_key = Column(String(512), nullable=False, comment="对象存储键，禁止存签名 URL")
    file_size = Column(Integer, nullable=True, comment="文件字节数")
    contract_type = Column(String(64), nullable=True, comment="用户声明的合同类型")
    party_role = Column(String(32), nullable=True, comment="委托方立场，如甲方/乙方")
    status = Column(
        String(32),
        nullable=False,
        default="pending",
        comment="处理状态：pending/reviewing/completed/failed",
    )
    error_message = Column(Text, nullable=True, comment="失败原因，成功时为空")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now, comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now, comment="更新时间"
    )

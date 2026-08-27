"""审查报告表。"""

from datetime import datetime, timezone

from core.database import Base
from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReviewReport(Base):
    """合同审查报告，子结构以 JSON 字符串存单列。"""

    __tablename__ = "tb_review_report"
    __table_args__ = (
        CheckConstraint(
            "overall_score >= 0 AND overall_score <= 100",
            name="ck_tb_review_report_score",
        ),
        CheckConstraint("risk_level IN ('high', 'medium', 'low')", name="ck_tb_review_report_risk"),
        Index("ix_tb_review_report_owner_created", "tenant_id", "user_id", "created_at"),
        Index("ix_tb_review_report_contract", "tenant_id", "user_id", "contract_id"),
        {"comment": "审查报告表：评分与条款子结构，按租户+用户隔离。"},
    )

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, comment="主键，自增")
    tenant_id = Column(String(64), nullable=False, comment="租户标识，由令牌写入")
    user_id = Column(
        Integer,
        ForeignKey("tb_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="归属用户主键，由令牌写入，不信任请求体",
    )
    contract_id = Column(
        Integer,
        ForeignKey("tb_contract.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联合同主键，删除合同时级联删除报告",
    )
    contract_title = Column(String(255), nullable=False, comment="合同标题快照，避免改名后报告标题漂移")
    contract_type = Column(String(64), nullable=True, comment="合同类型快照")
    overall_score = Column(Integer, nullable=False, comment="综合评分 0-100")
    risk_level = Column(String(16), nullable=False, comment="整体风险：high/medium/low")
    summary = Column(Text, nullable=False, comment="报告摘要")
    high_risk_count = Column(Integer, nullable=True, default=0, comment="高风险条款条数")
    medium_risk_count = Column(Integer, nullable=True, default=0, comment="中风险条款条数")
    low_risk_count = Column(Integer, nullable=True, default=0, comment="低风险条款条数")
    risk_clauses = Column(Text, nullable=True, comment="风险条款 JSON 字符串，只读展示")
    missing_clauses = Column(Text, nullable=True, comment="缺失条款 JSON 字符串，只读展示")
    compliance_checks = Column(Text, nullable=True, comment="合规检查 JSON 字符串，只读展示")
    key_terms = Column(Text, nullable=True, comment="关键条款 JSON 字符串，只读展示")
    suggestions = Column(Text, nullable=True, comment="建议 JSON 字符串，只读展示")
    raw_text_excerpt = Column(Text, nullable=True, comment="原文摘录，仅长度受限摘要")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utc_now, comment="创建时间")
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now, comment="更新时间"
    )

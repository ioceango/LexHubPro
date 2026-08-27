"""自托管业务数据的请求与响应模型。

**归属列不出现在任何请求模型中**：`tenant_id` / `user_id` 一律由服务端按当前登录
身份写入。若允许客户端提交这两个字段，即等于把「数据归属」交给调用方自证，
伪造一个 `user_id` 就能写入或读取他人数据。
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ContractCreateRequest(BaseModel):
    """创建合同记录请求。

    只接收对象键而不接收任何 URL：签名 URL 会过期，入库即成为死数据；
    下载时再按对象键换取临时链接。
    """

    title: str = Field(..., min_length=1, max_length=255)
    file_name: str = Field(..., min_length=1, max_length=255)
    bucket_name: str = Field(..., min_length=1, max_length=128)
    object_key: str = Field(..., min_length=1, max_length=512)
    file_size: Optional[int] = Field(default=None, ge=0)
    contract_type: Optional[str] = Field(default=None, max_length=64)
    party_role: Optional[str] = Field(default=None, max_length=32)


class ContractStatusUpdateRequest(BaseModel):
    """更新合同处理状态请求。"""

    status: str = Field(..., pattern="^(pending|reviewing|completed|failed)$")
    error_message: Optional[str] = Field(default=None, max_length=2000)


class ContractResponse(BaseModel):
    """合同记录响应。"""

    id: int
    title: str
    file_name: str
    bucket_name: str
    object_key: str
    file_size: Optional[int] = None
    contract_type: Optional[str] = None
    party_role: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ContractListResponse(BaseModel):
    """合同列表响应，带总数以支持前端分页。"""

    items: List[ContractResponse]
    total: int


class ReportCreateRequest(BaseModel):
    """创建审查报告请求。

    子结构（风险条款、缺失条款等）以 JSON 字符串传入并原样存单列：
    它们仅用于只读展示，不参与筛选与关联查询。
    """

    contract_id: int = Field(..., ge=1)
    contract_title: str = Field(..., min_length=1, max_length=255)
    contract_type: Optional[str] = Field(default=None, max_length=64)
    overall_score: int = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern="^(high|medium|low)$")
    summary: str = Field(..., min_length=1)
    high_risk_count: int = Field(default=0, ge=0)
    medium_risk_count: int = Field(default=0, ge=0)
    low_risk_count: int = Field(default=0, ge=0)
    risk_clauses: Optional[str] = None
    missing_clauses: Optional[str] = None
    compliance_checks: Optional[str] = None
    key_terms: Optional[str] = None
    suggestions: Optional[str] = None
    raw_text_excerpt: Optional[str] = None


class ReportResponse(BaseModel):
    """审查报告响应。"""

    id: int
    contract_id: int
    contract_title: str
    contract_type: Optional[str] = None
    overall_score: int
    risk_level: str
    summary: str
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    risk_clauses: Optional[str] = None
    missing_clauses: Optional[str] = None
    compliance_checks: Optional[str] = None
    key_terms: Optional[str] = None
    suggestions: Optional[str] = None
    raw_text_excerpt: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ReportListResponse(BaseModel):
    """审查报告列表响应。"""

    items: List[ReportResponse]
    total: int


class ReportSummaryResponse(BaseModel):
    """审查概览统计（历史页顶部卡片使用）。"""

    report_count: int
    average_score: Optional[float] = None
    high_risk_total: int = 0
    medium_risk_total: int = 0
    low_risk_total: int = 0


class DeleteResultResponse(BaseModel):
    """删除结果响应。"""

    success: bool = True
    message: str = "删除成功"
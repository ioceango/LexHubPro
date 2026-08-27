"""合同审查 API：从 MinIO 取文件，审查后由后端写入报告。

错误映射（docs/rules/02-logging-and-tracing.md 第 5.1 节）：
- 入参不合法               -> 400，WARNING
- 领域可重试失败           -> 422，WARNING
- AI 额度/余额不足         -> 402，ERROR（不可自愈，需充值）
- AI 凭据配置错误/服务不可用 -> 503，ERROR
- 其他未预期异常           -> 500，ERROR + 错误编号
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

import base64
import json

from auth_providers import AuthUser
from core.database import get_db
from dependencies.auth import get_current_auth_user
from dependencies.tracing import bind_trace_id, current_trace_id
from repositories.contract import Owner
from services import contracts as contract_service
from storage_providers import StorageError, StorageObjectNotFoundError, get_storage_provider
from services.ai_invoker import (
    AIConfigurationError,
    AIInvocationError,
    AIInvoker,
    AIQuotaExhaustedError,
)
from services.contract_review import ContractReviewError, ContractReviewService
from services import user_llm as llm_config
from services.user_llm import build_chat_client
from utils.log_sanitize import describe_fields

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/review",
    tags=["review"],
    dependencies=[Depends(bind_trace_id)],
)

MAX_PDF_DATA_URI_LENGTH = 22 * 1024 * 1024  # base64 后约 15MB 原始文件上限
RAW_TEXT_EXCERPT_LIMIT = 4000

HTTP_PAYMENT_REQUIRED = 402
HTTP_SERVICE_UNAVAILABLE = 503


class AnalyzeContractRequest(BaseModel):
    """合同审查请求：只收已上传合同 id。"""

    contract_id: int = Field(..., ge=1)
    contract_type: Optional[str] = Field(default="", description="用户声明的合同类型")
    party_role: Optional[str] = Field(default="", description="委托方立场，如 甲方/乙方")


class KeyTerm(BaseModel):
    label: str = ""
    value: str = ""


class RiskClause(BaseModel):
    clause_title: str = ""
    original_text: str = ""
    risk_level: str = "medium"
    risk_reason: str = ""
    impact: str = ""
    suggestion: str = ""


class MissingClause(BaseModel):
    clause_name: str = ""
    importance: str = "medium"
    reason: str = ""
    recommended_text: str = ""


class ComplianceCheck(BaseModel):
    item: str = ""
    status: str = "warn"
    law_reference: str = ""
    detail: str = ""


class AnalyzeContractResponse(BaseModel):
    """结构化审查报告。"""

    report_id: Optional[int] = None
    contract_type: str = ""
    overall_score: int
    risk_level: str
    summary: str
    key_terms: List[KeyTerm] = []
    risk_clauses: List[RiskClause] = []
    missing_clauses: List[MissingClause] = []
    compliance_checks: List[ComplianceCheck] = []
    suggestions: List[str] = []
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    raw_text_excerpt: str = ""


def _validate_pdf_input(pdf_input: str) -> None:
    """校验 PDF 入参格式与大小。"""
    if not pdf_input.startswith("data:application/pdf"):
        logger.warning("[BIZ] reject non-pdf upload trace_id=%s", current_trace_id())
        raise HTTPException(status_code=400, detail="请上传 PDF 格式的合同文件。")
    if len(pdf_input) > MAX_PDF_DATA_URI_LENGTH:
        logger.warning(
            "[BIZ] reject oversized upload chars=%s trace_id=%s",
            len(pdf_input), current_trace_id(),
        )
        raise HTTPException(status_code=400, detail="合同文件过大，请上传 15MB 以内、80 页以内的 PDF。")


def _map_ai_error(error: AIInvocationError) -> HTTPException:
    """把语义化 AI 异常映射为准确的 HTTP 响应。

    额度不足是最常见的「AI 审查失败」根因，必须与「稍后重试」区分开，
    否则用户会反复重试却永远不会成功。
    """
    trace_id = current_trace_id()
    if isinstance(error, AIQuotaExhaustedError):
        return HTTPException(status_code=HTTP_PAYMENT_REQUIRED, detail=str(error))
    if isinstance(error, AIConfigurationError):
        return HTTPException(status_code=HTTP_SERVICE_UNAVAILABLE, detail=str(error))
    return HTTPException(
        status_code=HTTP_SERVICE_UNAVAILABLE,
        detail=f"{error}（错误编号：{trace_id}）",
    )


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _copy_contract_fields(contract: Any) -> dict[str, Any]:
    """拷贝审查后续要用的标量，避免 commit 后 ORM 过期再懒加载把事务重新打开。"""
    return {
        "id": contract.id,
        "title": contract.title,
        "bucket_name": contract.bucket_name,
        "object_key": contract.object_key,
        "contract_type": contract.contract_type or "",
    }


@router.post("/analyze", response_model=AnalyzeContractResponse)
async def analyze_contract(
    data: AnalyzeContractRequest,
    auth_user: AuthUser = Depends(get_current_auth_user),
    session: AsyncSession = Depends(get_db),
) -> AnalyzeContractResponse:
    """从 MinIO 取合同、审查、短事务写报告。"""
    trace_id = current_trace_id()
    owner = Owner(tenant_id=auth_user.tenant_id, user_id=auth_user.id)
    contract = await contract_service.get_contract(session, owner, data.contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="记录不存在")

    logger.info(
        "[BIZ] analyze request user_id=%s contract_id=%s fields=%s trace_id=%s",
        auth_user.id,
        data.contract_id,
        describe_fields(data.model_dump()),
        trace_id,
    )

    active = await llm_config.get_active(session, auth_user.tenant_id, auth_user.id)
    if active is None:
        raise HTTPException(status_code=409, detail="请先配置并启用一个审查模型")

    fields = _copy_contract_fields(contract)
    # BUG-006：结束 SELECT 自动开启的事务，再短写状态；下载与模型调用在事务外。
    await contract_service.close_read_transaction(session)

    await contract_service.update_contract_status(session, owner, fields["id"], "reviewing")
    try:
        pdf_bytes = await get_storage_provider().download(fields["bucket_name"], fields["object_key"])
    except StorageObjectNotFoundError as exc:
        await contract_service.update_contract_status(session, owner, fields["id"], "failed", "文件不存在")
        raise HTTPException(status_code=404, detail="文件不存在") from exc
    except StorageError as exc:
        await contract_service.update_contract_status(session, owner, fields["id"], "failed", "对象存储暂不可用")
        raise HTTPException(status_code=503, detail="对象存储暂不可用") from exc

    prefix = "data:" + "application/pdf;base64,"
    pdf_input = prefix + base64.b64encode(pdf_bytes).decode("ascii")
    service = ContractReviewService(
        invoker=AIInvoker(chat=build_chat_client(active)),
        review_model=active.model_id,
    )
    try:
        contract_text = await _run_extraction(service, pdf_input)
        report = await _run_review(service, contract_text, data)
    except HTTPException as exc:
        await contract_service.update_contract_status(
            session, owner, fields["id"], "failed", str(exc.detail)[:500]
        )
        raise

    excerpt = contract_text[:RAW_TEXT_EXCERPT_LIMIT]
    report["raw_text_excerpt"] = excerpt
    payload = {
        "contract_id": fields["id"],
        "contract_title": fields["title"],
        "contract_type": data.contract_type or fields["contract_type"],
        "overall_score": report["overall_score"],
        "risk_level": report["risk_level"],
        "summary": report["summary"],
        "high_risk_count": report.get("high_risk_count") or 0,
        "medium_risk_count": report.get("medium_risk_count") or 0,
        "low_risk_count": report.get("low_risk_count") or 0,
        "risk_clauses": _dump_json(report.get("risk_clauses") or []),
        "missing_clauses": _dump_json(report.get("missing_clauses") or []),
        "compliance_checks": _dump_json(report.get("compliance_checks") or []),
        "key_terms": _dump_json(report.get("key_terms") or []),
        "suggestions": _dump_json(report.get("suggestions") or []),
        "raw_text_excerpt": excerpt,
    }
    saved = await contract_service.create_report(session, owner, payload)
    if saved is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    await contract_service.update_contract_status(session, owner, fields["id"], "completed")
    logger.info(
        "[BIZ] contract reviewed user_id=%s score=%s level=%s trace_id=%s",
        auth_user.id,
        report["overall_score"],
        report["risk_level"],
        trace_id,
    )
    return AnalyzeContractResponse(report_id=saved.id, **report)


async def _run_extraction(service: ContractReviewService, pdf_input: str) -> str:
    """执行合同文本提取阶段，并完成异常映射。"""
    try:
        return await service.extract_contract_text(pdf_input)
    except ContractReviewError as exc:
        logger.warning("[BIZ] contract extraction rejected trace_id=%s", current_trace_id())
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIInvocationError as exc:
        raise _map_ai_error(exc) from exc
    except ValueError as exc:
        logger.warning("[BIZ] pdf input rejected error_type=%s trace_id=%s", type(exc).__name__, current_trace_id())
        raise HTTPException(status_code=400, detail="PDF 文件无法解析，请确认文件未损坏且为标准 PDF。") from exc
    except Exception as exc:  # noqa: BLE001
        trace_id = current_trace_id()
        logger.error(
            "[BIZ] pdf extraction failed error_type=%s trace_id=%s",
            type(exc).__name__, trace_id, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"合同 PDF 解析失败，请稍后重试。（错误编号：{trace_id}）",
        ) from exc


async def _run_review(
    service: ContractReviewService,
    contract_text: str,
    data: AnalyzeContractRequest,
) -> Dict[str, Any]:
    """执行 AI 审查阶段，并完成异常映射。"""
    try:
        return await service.review_contract_text(
            contract_text=contract_text,
            contract_type=data.contract_type or "",
            party_role=data.party_role or "",
        )
    except ContractReviewError as exc:
        logger.warning("[BIZ] contract review returned unusable result trace_id=%s", current_trace_id())
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AIInvocationError as exc:
        raise _map_ai_error(exc) from exc
    except Exception as exc:  # noqa: BLE001
        trace_id = current_trace_id()
        logger.error(
            "[BIZ] contract review failed error_type=%s trace_id=%s",
            type(exc).__name__, trace_id, exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"AI 合同审查失败，请稍后重试。（错误编号：{trace_id}）",
        ) from exc
"""合同审查服务：本地抽文本 + 用户启用模型结构化审查。"""

import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional

from dependencies.tracing import current_trace_id
from schemas.chat import ChatMessage, GenTxtRequest
from services.ai_invoker import AIInvoker
from services.contract_review_prompts import (
    JSON_REPAIR_SYSTEM_PROMPT,
    MAX_CHARS_FOR_REPAIR,
    REVIEW_SYSTEM_PROMPT,
    build_review_user_prompt,
)

logger = logging.getLogger(__name__)

SCAN_PDF_MESSAGE = "无法从该 PDF 中提取到足够的文字。请上传可复制文本的合同 PDF（扫描件请先做文字识别）。"

MIN_VALID_CONTRACT_CHARS = 60
# 真实文字版合同正文远超该阈值；扫描件/图片型 PDF 本地抽取通常接近 0，
# 阈值取 200 可在「避免无谓 AI 调用」与「正确识别扫描件」之间取得平衡。
MIN_LOCAL_EXTRACT_CHARS = 200
LOCAL_EXTRACT_PAGE_LIMIT = 80

REQUIRED_FIELDS = ["overall_score", "risk_level", "summary", "risk_clauses", "missing_clauses", "compliance_checks"]

VALID_RISK_LEVELS = {"high", "medium", "low"}
VALID_COMPLIANCE_STATUS = {"pass", "warn", "fail"}

RISK_LEVEL_ALIASES = {"高": "high", "中": "medium", "低": "low", "严重": "high", "一般": "medium"}
DEFAULT_SCORE_BY_LEVEL = {"high": 45, "medium": 70, "low": 86}


class ContractReviewError(Exception):
    """合同审查业务失败（可提示用户重试或调整输入）。"""


def _extract_json_block(text: str) -> str:
    """从模型输出中抽取 JSON 主体，兼容 ```json 包装。"""
    cleaned = (text or "").strip()
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*\n(.*?)```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start:end + 1]
    return cleaned


def _as_list_of_dict(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _as_list_of_str(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_risk_level(value: Any, default: str = "medium") -> str:
    level = str(value or "").strip().lower()
    if level in VALID_RISK_LEVELS:
        return level
    return RISK_LEVEL_ALIASES.get(level, default)


def _normalize_score(value: Any, risk_level: str) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = DEFAULT_SCORE_BY_LEVEL[risk_level]
    return max(0, min(100, score))


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """规范化 AI 输出，保证前端拿到稳定结构。"""
    risk_level = _normalize_risk_level(payload.get("risk_level"))
    overall_score = _normalize_score(payload.get("overall_score"), risk_level)

    risk_clauses = [
        {
            "clause_title": str(item.get("clause_title") or "未命名条款").strip(),
            "original_text": str(item.get("original_text") or "").strip(),
            "risk_level": _normalize_risk_level(item.get("risk_level")),
            "risk_reason": str(item.get("risk_reason") or "").strip(),
            "impact": str(item.get("impact") or "").strip(),
            "suggestion": str(item.get("suggestion") or "").strip(),
        }
        for item in _as_list_of_dict(payload.get("risk_clauses"))
    ]

    missing_clauses = [
        {
            "clause_name": str(item.get("clause_name") or "未命名条款").strip(),
            "importance": _normalize_risk_level(item.get("importance")),
            "reason": str(item.get("reason") or "").strip(),
            "recommended_text": str(item.get("recommended_text") or "").strip(),
        }
        for item in _as_list_of_dict(payload.get("missing_clauses"))
    ]

    compliance_checks = []
    for item in _as_list_of_dict(payload.get("compliance_checks")):
        status = str(item.get("status") or "").strip().lower()
        compliance_checks.append({
            "item": str(item.get("item") or "合规检查项").strip(),
            "status": status if status in VALID_COMPLIANCE_STATUS else "warn",
            "law_reference": str(item.get("law_reference") or "").strip(),
            "detail": str(item.get("detail") or "").strip(),
        })

    key_terms = [
        {
            "label": str(item.get("label") or "").strip(),
            "value": str(item.get("value") or "未约定").strip(),
        }
        for item in _as_list_of_dict(payload.get("key_terms"))
    ]

    return {
        "contract_type": str(payload.get("contract_type") or "").strip(),
        "overall_score": overall_score,
        "risk_level": risk_level,
        "summary": str(payload.get("summary") or "").strip(),
        "key_terms": key_terms,
        "risk_clauses": risk_clauses,
        "missing_clauses": missing_clauses,
        "compliance_checks": compliance_checks,
        "suggestions": _as_list_of_str(payload.get("suggestions")),
        "high_risk_count": sum(1 for c in risk_clauses if c["risk_level"] == "high"),
        "medium_risk_count": sum(1 for c in risk_clauses if c["risk_level"] == "medium"),
        "low_risk_count": sum(1 for c in risk_clauses if c["risk_level"] == "low"),
    }


def _decode_pdf_data_uri(pdf_data_uri: str) -> Optional[bytes]:
    """把 base64 PDF data URI 解码为原始字节；失败返回 None 由上层降级处理。"""
    if "," not in pdf_data_uri:
        return None
    try:
        return base64.b64decode(pdf_data_uri.split(",", 1)[1])
    except Exception:  # noqa: BLE001 - 解码失败统一走降级路径
        return None


def extract_text_locally(pdf_data_uri: str) -> str:
    """使用 PyMuPDF 本地抽取文字版 PDF 正文（不消耗 AI 额度）。"""
    pdf_bytes = _decode_pdf_data_uri(pdf_data_uri)
    if not pdf_bytes:
        return ""

    import fitz

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:  # noqa: BLE001 - 非法 PDF 交由 AI 路径或上层报错
        return ""

    try:
        chunks: List[str] = []
        for index, page in enumerate(document):
            if index >= LOCAL_EXTRACT_PAGE_LIMIT:
                break
            chunks.append(page.get_text("text").strip())
    finally:
        document.close()

    return re.sub(r"\n{3,}", "\n\n", "\n\n".join(chunk for chunk in chunks if chunk)).strip()


class ContractReviewService:
    """合同审查编排服务。"""

    def __init__(self, invoker: Optional[AIInvoker] = None, review_model: str = "") -> None:
        self.invoker = invoker or AIInvoker()
        self.review_model = review_model

    async def extract_contract_text(self, pdf_data_uri: str) -> str:
        """提取合同正文：仅本地 PyMuPDF。扫描件请先 OCR。"""
        trace_id = current_trace_id()
        local_text = extract_text_locally(pdf_data_uri)
        if len(local_text) >= MIN_LOCAL_EXTRACT_CHARS:
            logger.info(
                "[BIZ] contract text extracted locally chars=%s trace_id=%s",
                len(local_text), trace_id,
            )
            return local_text
        logger.warning(
            "[BIZ] local pdf extraction insufficient chars=%s trace_id=%s",
            len(local_text), trace_id,
        )
        raise ContractReviewError(SCAN_PDF_MESSAGE)

    async def review_contract_text(
        self,
        contract_text: str,
        contract_type: str = "",
        party_role: str = "",
    ) -> Dict[str, Any]:
        """使用用户启用的模型生成结构化审查结论。"""
        if not self.review_model:
            raise ContractReviewError("请先配置并启用一个审查模型")
        request = GenTxtRequest(
            messages=[
                ChatMessage(role="system", content=REVIEW_SYSTEM_PROMPT),
                ChatMessage(role="user", content=build_review_user_prompt(contract_text, contract_type, party_role)),
            ],
            model=self.review_model,
            temperature=0.2,
            max_tokens=16384,
        )
        raw_content = await self.invoker.gentxt(request, stage="review")
        if not raw_content:
            raise ContractReviewError(
                "当前模型没有返回可用正文。推理模型可能把结果放在内部思考字段，或输出被截断。请换一个普通对话模型后重试。"
            )

        payload = self._parse_payload(raw_content)
        if payload is None:
            payload = await self._repair_payload(raw_content)

        self._assert_required_fields(payload)
        return self._validate_normalized(_normalize_payload(payload))

    @staticmethod
    def _assert_required_fields(payload: Dict[str, Any]) -> None:
        """校验 AI 输出的必需字段。"""
        missing = [field for field in REQUIRED_FIELDS if field not in payload]
        if missing:
            logger.warning(
                "[AI_OP] review payload missing fields=%s trace_id=%s",
                ",".join(missing), current_trace_id(),
            )
            raise ContractReviewError(f"AI 审查结果缺少必要字段：{'、'.join(missing)}，请重试。")

    @staticmethod
    def _validate_normalized(normalized: Dict[str, Any]) -> Dict[str, Any]:
        """归一化结果的业务完整性校验。"""
        if not normalized["summary"]:
            raise ContractReviewError("AI 审查结果缺少总体结论，请重试。")
        if not normalized["risk_clauses"] and not normalized["missing_clauses"]:
            raise ContractReviewError("AI 未能识别出有效的条款分析结果，请重试。")
        return normalized

    @staticmethod
    def _parse_payload(raw_content: str) -> Optional[Dict[str, Any]]:
        """尝试从模型输出解析 JSON 对象，失败返回 None。"""
        try:
            parsed = json.loads(_extract_json_block(raw_content))
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    async def _repair_payload(self, raw_content: str) -> Dict[str, Any]:
        """一次修复重试：让模型把内容修正为合法 JSON。"""
        logger.warning(
            "[AI_OP] retry stage=json_repair reason=json_decode_error raw_chars=%s trace_id=%s",
            len(raw_content), current_trace_id(),
        )
        repair_request = GenTxtRequest(
            messages=[
                ChatMessage(role="system", content=JSON_REPAIR_SYSTEM_PROMPT),
                ChatMessage(role="user", content=raw_content[:MAX_CHARS_FOR_REPAIR]),
            ],
            model=self.review_model,
            temperature=0.0,
            max_tokens=16384,
        )
        repaired = await self.invoker.gentxt(repair_request, stage="json_repair")
        payload = self._parse_payload(repaired)
        if payload is None:
            raise ContractReviewError("AI 审查结果解析失败，请稍后重试。")
        return payload
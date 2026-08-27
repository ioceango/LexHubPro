"""合同审查链路回归测试。

覆盖本次 Bug 修复的关键行为（全部使用假 invoker，不消耗真实 AI 额度）：
1. 本地 PyMuPDF 提取成功时不触发任何 AI 调用；
2. 本地提取内容不足时直接失败（扫描件 422），不再走平台 PDF 分析；
3. AI 额度不足 / 凭据错误 / 限流 被正确分类，且只有瞬时错误可重试；
4. AI 输出被 ```json 包裹、字段大小写与中文别名混杂时仍能归一化；
5. AI 输出为非法 JSON 时触发一次修复重试并成功；
6. 日志脱敏工具不会输出 PDF base64、合同正文等敏感内容。

规范依据：docs/rules/05-testing-and-automation.md
"""

import base64
import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.ai_invoker import (  # noqa: E402
    AIConfigurationError,
    AIQuotaExhaustedError,
    AIUnavailableError,
    classify_ai_error,
)
from services.contract_review import (  # noqa: E402
    ContractReviewError,
    ContractReviewService,
    extract_text_locally,
)
from utils.log_sanitize import describe_fields, omit_keys  # noqa: E402

CONTRACT_BODY = """采购框架合同

甲方：某科技有限公司
乙方：某供应商有限公司

第一条 标的与数量
乙方向甲方供应服务器设备，合同总金额人民币 500 万元。

第二条 付款方式
甲方应在合同签订后 3 日内一次性支付全部合同价款，乙方在收款后 90 日内交货。

第三条 质量标准
乙方交付的货物质量由乙方自行确认，甲方无权提出质量异议。

第四条 违约责任
甲方逾期付款，每日按合同总金额 5% 支付违约金；乙方逾期交货不承担任何责任。

第五条 保密与数据
甲方应向乙方提供其全部客户个人信息用于售后服务，乙方无需承担保密义务。

第六条 争议解决
本合同争议由乙方所在地法院管辖，甲方放弃上诉权利。

第七条 合同期限
本合同长期有效，乙方可随时单方解除，甲方不得解除本合同。
"""

VALID_REVIEW_PAYLOAD = {
    "contract_type": "采购合同",
    "overall_score": 32,
    "risk_level": "高",  # 中文别名，应被归一化为 high
    "summary": "合同整体明显向乙方倾斜，付款与违约责任条款对甲方极为不利。",
    "key_terms": [{"label": "合同金额", "value": "人民币 500 万元"}],
    "risk_clauses": [
        {
            "clause_title": "第二条 付款方式",
            "original_text": "甲方应在合同签订后 3 日内一次性支付全部合同价款",
            "risk_level": "high",
            "risk_reason": "全额先付且交货期长达 90 日，甲方资金风险极高。",
            "impact": "资金被长期占用且缺乏履约担保。",
            "suggestion": "改为分期支付，并约定验收合格后支付尾款。",
        },
        {
            "clause_title": "第四条 违约责任",
            "original_text": "乙方逾期交货不承担任何责任",
            "risk_level": "MEDIUM",  # 大写，应被归一化
            "risk_reason": "违约责任严重不对等。",
            "impact": "乙方违约无成本。",
            "suggestion": "补充乙方逾期交货的违约金标准。",
        },
    ],
    "missing_clauses": [
        {
            "clause_name": "不可抗力条款",
            "importance": "medium",
            "reason": "缺少不可抗力免责与通知机制。",
            "recommended_text": "因不可抗力导致不能履行的，可部分或全部免除责任。",
        }
    ],
    "compliance_checks": [
        {
            "item": "违约金是否超过法定上限",
            "status": "fail",
            "law_reference": "《民法典》第五百八十五条",
            "detail": "日违约金 5% 远超实际损失，存在被认定过高的风险。",
        },
        {
            "item": "管辖约定是否有效",
            "status": "unknown",  # 非法枚举，应被归一化为 warn
            "law_reference": "《民事诉讼法》第三十五条",
            "detail": "放弃上诉权的约定无效。",
        },
    ],
    "suggestions": ["调整付款节奏", "补齐乙方违约责任"],
}


def build_pdf_data_uri(text: str) -> str:
    """构造一份文字版 PDF 的 base64 data URI。"""
    import fitz

    document = fitz.open()
    page = document.new_page()
    page.insert_text((50, 60), text, fontsize=9, fontname="china-s")
    payload = document.tobytes()
    document.close()
    return "data:application/pdf;base64," + base64.b64encode(payload).decode()


class FakeInvoker:
    """记录调用次数的假 AI 调用器。"""

    def __init__(self, gentxt_results=None, pdf_result: str = "", pdf_error: Exception = None) -> None:
        self.gentxt_results = list(gentxt_results or [])
        self.pdf_result = pdf_result
        self.pdf_error = pdf_error
        self.pdf_calls = 0
        self.gentxt_stages = []

    async def analyze_pdf(self, request, stage: str = "pdf_extract") -> str:
        self.pdf_calls += 1
        if self.pdf_error:
            raise self.pdf_error
        return self.pdf_result

    async def gentxt(self, request, stage: str) -> str:
        self.gentxt_stages.append(stage)
        if not self.gentxt_results:
            raise AssertionError("unexpected extra gentxt call")
        return self.gentxt_results.pop(0)


# ---------- 文本提取 ----------

def test_local_extraction_reads_clause_markers():
    text = extract_text_locally(build_pdf_data_uri(CONTRACT_BODY))
    assert "第一条" in text and "第四条" in text
    assert len(text) > 300


def test_invalid_data_uri_returns_empty_string():
    assert extract_text_locally("not-a-data-uri") == ""
    assert extract_text_locally("data:application/pdf;base64,%%%") == ""


@pytest.mark.asyncio
async def test_extraction_skips_ai_when_local_text_is_sufficient():
    invoker = FakeInvoker(pdf_result="should not be used")
    service = ContractReviewService(invoker=invoker)
    text = await service.extract_contract_text(build_pdf_data_uri(CONTRACT_BODY))
    assert "第二条" in text
    assert invoker.pdf_calls == 0, "本地可解析时不应消耗 AI 额度"


@pytest.mark.asyncio
async def test_extraction_rejects_scanned_pdf_without_platform_ocr():
    invoker = FakeInvoker(pdf_result=CONTRACT_BODY)
    service = ContractReviewService(invoker=invoker)
    with pytest.raises(ContractReviewError):
        await service.extract_contract_text(build_pdf_data_uri("扫描件"))
    assert invoker.pdf_calls == 0


@pytest.mark.asyncio
async def test_extraction_raises_business_error_when_no_text_available():
    invoker = FakeInvoker(pdf_result="")
    service = ContractReviewService(invoker=invoker)
    with pytest.raises(ContractReviewError):
        await service.extract_contract_text(build_pdf_data_uri("图"))


# ---------- 异常分类 ----------

class _StubError(Exception):
    def __init__(self, message: str, status_code: int = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@pytest.mark.parametrize(
    "message,status,expected,retryable",
    [
        ("AI balance is insufficient to finish the operation", 403, AIQuotaExhaustedError, False),
        ("insufficient_ai_balance", 403, AIQuotaExhaustedError, False),
        ("You exceeded your current quota", 429, AIQuotaExhaustedError, False),
        ("Invalid API key provided", 401, AIConfigurationError, False),
        ("AI service not configured. Set APP_AI_BASE_URL and APP_AI_KEY.", None, AIConfigurationError, False),
        ("Rate limit reached for model", 429, AIUnavailableError, True),
        ("Bad gateway", 502, AIUnavailableError, True),
        ("Request timed out", None, AIUnavailableError, True),
    ],
)
def test_classify_ai_error(message, status, expected, retryable):
    error = classify_ai_error(_StubError(message, status), "review")
    assert isinstance(error, expected)
    assert error.retryable is retryable
    assert error.stage == "review"
    # 用户可见文案不得透出第三方原始报错
    assert "Error code" not in str(error)


# ---------- 审查结果归一化 ----------

@pytest.mark.asyncio
async def test_review_normalizes_aliases_and_counts():
    wrapped = "```json\n" + json.dumps(VALID_REVIEW_PAYLOAD, ensure_ascii=False) + "\n```"
    service = ContractReviewService(invoker=FakeInvoker(gentxt_results=[wrapped]), review_model="test-model")

    report = await service.review_contract_text(CONTRACT_BODY, "采购合同", "甲方")

    assert report["risk_level"] == "high"
    assert report["overall_score"] == 32
    assert report["risk_clauses"][1]["risk_level"] == "medium"
    assert report["compliance_checks"][1]["status"] == "warn"
    assert report["high_risk_count"] == 1
    assert report["medium_risk_count"] == 1
    assert report["suggestions"] == ["调整付款节奏", "补齐乙方违约责任"]


@pytest.mark.asyncio
async def test_review_repairs_invalid_json_once():
    invoker = FakeInvoker(
        gentxt_results=[
            "这是模型的解释文字，不是 JSON",
            json.dumps(VALID_REVIEW_PAYLOAD, ensure_ascii=False),
        ]
    )
    service = ContractReviewService(invoker=invoker, review_model="test-model")

    report = await service.review_contract_text(CONTRACT_BODY, "采购合同", "甲方")

    assert invoker.gentxt_stages == ["review", "json_repair"]
    assert report["summary"]


@pytest.mark.asyncio
async def test_review_rejects_payload_missing_required_fields():
    incomplete = {"overall_score": 70, "risk_level": "medium"}
    service = ContractReviewService(
        invoker=FakeInvoker(gentxt_results=[json.dumps(incomplete), json.dumps(incomplete)]),
        review_model="test-model",
    )
    with pytest.raises(ContractReviewError):
        await service.review_contract_text(CONTRACT_BODY, "采购合同", "甲方")


@pytest.mark.asyncio
async def test_review_propagates_quota_error_without_swallowing():
    class QuotaInvoker(FakeInvoker):
        async def gentxt(self, request, stage: str) -> str:
            raise AIQuotaExhaustedError("额度不足", stage=stage, retryable=False)

    service = ContractReviewService(invoker=QuotaInvoker(), review_model="test-model")
    with pytest.raises(AIQuotaExhaustedError):
        await service.review_contract_text(CONTRACT_BODY, "采购合同", "甲方")


# ---------- 日志脱敏 ----------

def test_log_sanitize_never_leaks_contract_or_secrets():
    payload = {
        "pdf": "data:application/pdf;base64," + "A" * 5000,
        "contract_text": CONTRACT_BODY,
        "app_ai_key": "sk-secret-value-1234",
        "contract_type": "采购合同",
    }

    described = describe_fields(payload)
    assert "base64" not in described
    assert "甲方" not in described
    assert "contract_type" in described

    masked = omit_keys(payload)
    assert "sk-secret-value-1234" not in json.dumps(masked, ensure_ascii=False)
    assert "甲方" not in json.dumps(masked, ensure_ascii=False)
    assert masked["contract_type"] == "采购合同"
"""AI 调用统一封装层。

职责（对上层屏蔽 SDK 细节）：
1. `[AI_OP]` 埋点：调用前/成功/重试/失败成对记录 stage、model、字符数、耗时、trace_id；
2. 异常分类：把 SDK 原始异常收敛为语义化异常，便于路由层映射准确的 HTTP 状态码；
3. 瞬时故障重试：对限流与网关类错误做一次退避重试，额度不足/配置错误不重试。

规范依据：
- docs/rules/02-logging-and-tracing.md 第 4.1 节（AI 调用埋点、禁止记录 prompt 全文）
- docs/rules/06-backend-layering.md（异常映射在 service 边界完成）
"""

import asyncio
import logging
import time
from typing import Awaitable, Callable, Optional

from dependencies.tracing import current_trace_id
from schemas.chat import GenTxtRequest

logger = logging.getLogger(__name__)

TRANSIENT_RETRY_LIMIT = 1
TRANSIENT_RETRY_DELAY_SECONDS = 2.0

# 额度/计费类错误：不可重试，需要人工充值
QUOTA_ERROR_MARKERS = (
    "insufficient_ai_balance",
    "balance is insufficient",
    "insufficient_quota",
    "exceeded your current quota",
    "quota exceeded",
    "billing",
    "top up",
)
# 凭据/配置类错误：不可重试，需要修配置
CONFIG_ERROR_MARKERS = (
    "not configured",
    "invalid_api_key",
    "incorrect api key",
    "invalid authentication",
    "unauthorized",
)
# 瞬时错误：可重试
TRANSIENT_ERROR_MARKERS = (
    "rate limit",
    "too many requests",
    "timeout",
    "timed out",
    "temporarily unavailable",
    "bad gateway",
    "service unavailable",
    "connection error",
    "connection reset",
)

QUOTA_USER_MESSAGE = "当前审查模型额度已用尽。请到对应提供商控制台充值后重试。"
CONFIG_USER_MESSAGE = "当前审查模型的密钥无效或已失效，请到「模型配置」核对后重试。"
TRANSIENT_USER_MESSAGE = "AI 审查服务暂时繁忙或不可用，请稍后重试。"


class AIInvocationError(Exception):
    """AI 调用失败基类，message 为可直接展示给用户的中文提示。"""

    def __init__(self, message: str, *, stage: str, retryable: bool) -> None:
        super().__init__(message)
        self.stage = stage
        self.retryable = retryable


class AIQuotaExhaustedError(AIInvocationError):
    """AI 服务额度/余额不足。"""


class AIConfigurationError(AIInvocationError):
    """AI 服务凭据缺失或无效。"""


class AIUnavailableError(AIInvocationError):
    """AI 服务瞬时不可用（限流、超时、网关错误等）。"""


def _status_code(exc: Exception) -> Optional[int]:
    """尽力从异常中取出 HTTP 状态码。"""
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    return code if isinstance(code, int) else None


def classify_ai_error(exc: Exception, stage: str) -> AIInvocationError:
    """把 SDK 原始异常收敛为语义化异常。

    注意：返回的 message 是自研中文提示，不含第三方原始报错原文，
    符合「HTTP detail 禁止透出第三方报错」的红线。
    """
    text = str(exc).lower()
    status = _status_code(exc)

    if any(marker in text for marker in QUOTA_ERROR_MARKERS):
        return AIQuotaExhaustedError(QUOTA_USER_MESSAGE, stage=stage, retryable=False)
    if any(marker in text for marker in CONFIG_ERROR_MARKERS) or status == 401:
        return AIConfigurationError(CONFIG_USER_MESSAGE, stage=stage, retryable=False)
    if status == 429 or (status is not None and status >= 500):
        return AIUnavailableError(TRANSIENT_USER_MESSAGE, stage=stage, retryable=True)
    if any(marker in text for marker in TRANSIENT_ERROR_MARKERS):
        return AIUnavailableError(TRANSIENT_USER_MESSAGE, stage=stage, retryable=True)
    if status == 403:
        # 403 且未命中余额关键字，按权限/策略问题处理，不重试
        return AIConfigurationError(CONFIG_USER_MESSAGE, stage=stage, retryable=False)
    return AIUnavailableError(TRANSIENT_USER_MESSAGE, stage=stage, retryable=True)


class AIInvoker:
    """带埋点、分类与重试的 AI 调用入口。"""

    def __init__(self, chat=None) -> None:
        self.chat = chat

    async def gentxt(self, request: GenTxtRequest, stage: str) -> str:
        """调用文本生成能力，返回完整文本（非流式，便于结构化校验）。"""
        result = await self._invoke(
            stage=stage,
            model=request.model,
            input_chars=self._count_input_chars(request),
            call=lambda: self._chat().gentxt(request),
        )
        return (getattr(result, "content", "") or "").strip()

    def _chat(self):
        if self.chat is None:
            raise AIConfigurationError(CONFIG_USER_MESSAGE, stage="review", retryable=False)
        return self.chat

    @staticmethod
    def _count_input_chars(request: GenTxtRequest) -> int:
        """统计输入规模（只记录长度，不记录 prompt 内容）。"""
        total = 0
        for message in request.messages:
            if isinstance(message.content, str):
                total += len(message.content)
        return total

    async def _invoke(self, *, stage: str, model: str, input_chars: int, call: Callable[[], Awaitable]):
        """执行一次 AI 调用，附带埋点与瞬时错误重试。"""
        attempt = 1
        while True:
            trace_id = current_trace_id()
            started = time.perf_counter()
            logger.info(
                "[AI_OP] start stage=%s model=%s input_chars=%s attempt=%s trace_id=%s",
                stage, model, input_chars, attempt, trace_id,
            )
            try:
                result = await call()
            except AIInvocationError:
                raise
            except Exception as exc:  # noqa: BLE001 - 统一收敛为语义化异常
                cost_ms = int((time.perf_counter() - started) * 1000)
                error = classify_ai_error(exc, stage)
                if error.retryable and attempt <= TRANSIENT_RETRY_LIMIT:
                    logger.warning(
                        "[AI_OP] retry stage=%s model=%s error_type=%s cost_ms=%s attempt=%s trace_id=%s",
                        stage, model, type(exc).__name__, cost_ms, attempt, trace_id,
                    )
                    attempt += 1
                    await asyncio.sleep(TRANSIENT_RETRY_DELAY_SECONDS)
                    continue
                logger.error(
                    "[AI_OP] failed stage=%s model=%s error_type=%s error_class=%s cost_ms=%s trace_id=%s",
                    stage, model, type(exc).__name__, type(error).__name__, cost_ms, trace_id,
                    exc_info=True,
                )
                raise error from exc

            cost_ms = int((time.perf_counter() - started) * 1000)
            logger.info(
                "[AI_OP] success stage=%s model=%s output_chars=%s cost_ms=%s trace_id=%s",
                stage, model, self._output_chars(result), cost_ms, trace_id,
            )
            return result

    @staticmethod
    def _output_chars(result: object) -> int:
        """统计输出规模（只记录长度，不记录返回内容）。"""
        text = getattr(result, "result", None) or getattr(result, "content", None) or ""
        return len(text)
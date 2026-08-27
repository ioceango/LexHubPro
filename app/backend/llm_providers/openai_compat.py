"""OpenAI 兼容 Chat Completions 与 /models 列表。不含业务规则。"""

import logging

import httpx
from openai import AsyncOpenAI

from llm_providers.base import LlmProviderError
from schemas.chat import GenTxtRequest, GenTxtResponse

logger = logging.getLogger(__name__)
# SDK 默认 DEBUG 会把 messages/prompt 打进日志，违反脱敏红线。
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("openai._base_client").setLevel(logging.WARNING)

LIST_TIMEOUT_SECONDS = 15.0
# 与审查前端 timeout 600s、约束「审查保持 600s」对齐。
CHAT_TIMEOUT_SECONDS = 600.0


async def list_openai_models(base_url: str, api_key: str, extra_headers: dict[str, str] | None = None) -> list[dict[str, str]]:
    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    if extra_headers:
        headers.update(extra_headers)
    try:
        async with httpx.AsyncClient(timeout=LIST_TIMEOUT_SECONDS) as client:
            response = await client.get(url, headers=headers)
    except httpx.TimeoutException as exc:
        raise LlmProviderError("模型列表请求超时，请稍后重试", 503) from exc
    except httpx.HTTPError as exc:
        logger.warning("[BIZ] llm catalog http error type=%s", type(exc).__name__)
        raise LlmProviderError("模型列表暂时无法获取，请稍后重试", 503) from exc
    return _parse_catalog(response)


def _parse_catalog(response: httpx.Response) -> list[dict[str, str]]:
    if response.status_code in (401, 403):
        raise LlmProviderError("密钥无效，请核对后重试", 400)
    if response.status_code >= 500:
        raise LlmProviderError("模型列表暂时无法获取，请稍后重试", 503)
    if response.status_code >= 400:
        raise LlmProviderError("无法拉取模型列表，请稍后重试", 400)
    payload = response.json()
    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    result: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        model_id = str(item["id"])
        result.append({"id": model_id, "name": str(item.get("name") or model_id)})
    return result


def _coerce_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(_coerce_text(getattr(item, "text", None)))
        return "\n".join(part for part in parts if part).strip()
    return str(value).strip()


def extract_completion_text(response) -> str:
    """从 Chat Completions 取可见正文。GLM/Kimi 等推理模型常把正文放在 reasoning_content。"""
    choices = getattr(response, "choices", None) or []
    if not choices:
        logger.warning("[AI_OP] empty completion reason=no_choices")
        return ""
    choice = choices[0]
    message = getattr(choice, "message", None)
    finish = str(getattr(choice, "finish_reason", "") or "")
    if message is None:
        logger.warning("[AI_OP] empty completion reason=no_message finish=%s", finish)
        return ""
    extra = getattr(message, "model_extra", None) or {}
    if not isinstance(extra, dict):
        extra = {}
    content = _coerce_text(getattr(message, "content", None))
    if content:
        return content
    for key in ("reasoning_content", "reasoning"):
        fallback = _coerce_text(getattr(message, key, None) or extra.get(key))
        if fallback:
            logger.info("[AI_OP] completion used fallback field=%s chars=%s finish=%s", key, len(fallback), finish)
            return fallback
    logger.warning("[AI_OP] empty completion reason=no_text finish=%s", finish)
    return ""


class OpenAICompatChat:
    """供 AIInvoker 注入的 gentxt 实现。"""

    def __init__(self, api_key: str, base_url: str, extra_headers: dict[str, str] | None = None):
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            default_headers=extra_headers or None,
            timeout=CHAT_TIMEOUT_SECONDS,
        )

    async def gentxt(self, request: GenTxtRequest) -> GenTxtResponse:
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        response = await self._client.chat.completions.create(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,
        )
        content = extract_completion_text(response)
        return GenTxtResponse(content=content, model=request.model, usage=None)

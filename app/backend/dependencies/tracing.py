"""请求级链路追踪依赖。

平台约束不允许修改 `main.py`，无法注册全局中间件，因此采用
「路由级依赖 + contextvars」的方式为每个请求绑定 trace_id：

- 路由创建时挂载 `dependencies=[Depends(bind_trace_id)]`；
- Service / Repository 层通过 `current_trace_id()` 读取，
  不把 trace_id 作为业务参数逐层透传，避免污染领域函数签名。

规范依据：docs/rules/02-logging-and-tracing.md 第 3 节。
"""

import contextvars
import logging
import uuid

from fastapi import Request

logger = logging.getLogger(__name__)

TRACE_HEADER = "X-Trace-Id"
TRACE_ID_MAX_LENGTH = 64
FALLBACK_TRACE_ID = "-"

trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default=FALLBACK_TRACE_ID)


def current_trace_id() -> str:
    """读取当前请求的 trace_id；脱离请求上下文时返回占位符。"""
    return trace_id_var.get()


async def bind_trace_id(request: Request) -> str:
    """为当前请求绑定 trace_id：优先复用上游 `X-Trace-Id`，否则新生成。"""
    incoming = (request.headers.get(TRACE_HEADER) or "").strip()
    trace_id = incoming[:TRACE_ID_MAX_LENGTH] or uuid.uuid4().hex[:16]
    trace_id_var.set(trace_id)
    logger.info("[TRACE] enter %s %s trace_id=%s", request.method, request.url.path, trace_id)
    return trace_id
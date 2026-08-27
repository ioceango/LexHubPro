"""审查用的 Chat Completions 入参出参。不是 HTTP 对外 AI Hub。"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str = Field(..., description="system/user/assistant")
    content: str = Field(..., description="纯文本内容")


class GenTxtRequest(BaseModel):
    messages: List[ChatMessage]
    model: str
    stream: bool = False
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 16384


class GenTxtResponse(BaseModel):
    content: str
    model: str
    usage: Optional[dict] = None

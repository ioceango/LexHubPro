"""用户 LLM 配置的请求与响应。不回传明文 Key。"""

from typing import Optional

from pydantic import BaseModel, Field


class SaveKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=8, max_length=512)


class ProviderView(BaseModel):
    provider: str
    name: str
    configured: bool
    key_suffix: str = ""


class CatalogItem(BaseModel):
    id: str
    name: str


class CatalogResponse(BaseModel):
    items: list[CatalogItem]


class SaveModelRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=32)
    model_id: str = Field(..., min_length=1, max_length=191)
    display_name: Optional[str] = Field(default=None, max_length=191)
    enabled: bool = False


class PatchModelRequest(BaseModel):
    enabled: bool


class ModelView(BaseModel):
    id: int
    provider: str
    model_id: str
    display_name: str
    enabled: bool


class ActiveModelView(BaseModel):
    configured: bool
    provider: Optional[str] = None
    model_id: Optional[str] = None
    display_name: Optional[str] = None

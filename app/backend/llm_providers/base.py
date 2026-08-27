"""LLM 提供商端口：各厂商适配器只实现本契约。"""

from typing import Protocol, runtime_checkable


class LlmProviderError(Exception):
    """提供商调用失败。"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@runtime_checkable
class LlmProvider(Protocol):
    provider_id: str
    display_name: str
    base_url: str

    def extra_headers(self) -> dict[str, str]:
        ...

    async def list_models(self, api_key: str) -> list[dict[str, str]]:
        """返回 [{id, name}]，禁止把 api_key 写入日志。"""
        ...

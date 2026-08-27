"""DeepSeek 适配器。"""

from llm_providers.openai_compat import list_openai_models


class DeepSeekProvider:
    provider_id = "deepseek"
    display_name = "DeepSeek"
    base_url = "https://api.deepseek.com"

    def extra_headers(self) -> dict[str, str]:
        return {}

    async def list_models(self, api_key: str) -> list[dict[str, str]]:
        return await list_openai_models(self.base_url, api_key, self.extra_headers())

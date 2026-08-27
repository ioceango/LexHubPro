"""OpenRouter 适配器。"""

from llm_providers.openai_compat import list_openai_models


class OpenRouterProvider:
    provider_id = "openrouter"
    display_name = "OpenRouter"
    base_url = "https://openrouter.ai/api/v1"

    def extra_headers(self) -> dict[str, str]:
        return {
            "HTTP-Referer": "https://lexhubpro.local",
            "X-Title": "LexHubPro",
        }

    async def list_models(self, api_key: str) -> list[dict[str, str]]:
        return await list_openai_models(self.base_url, api_key, self.extra_headers())

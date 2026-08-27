"""提供商注册表。审查与配置服务只通过本模块取适配器。"""

from llm_providers.base import LlmProvider, LlmProviderError
from llm_providers.deepseek import DeepSeekProvider
from llm_providers.openrouter import OpenRouterProvider

_PROVIDERS: dict[str, LlmProvider] = {}


def register(provider: LlmProvider) -> None:
    _PROVIDERS[provider.provider_id] = provider


def get_provider(provider_id: str) -> LlmProvider:
    found = _PROVIDERS.get((provider_id or "").strip().lower())
    if found is None:
        raise LlmProviderError("不支持的模型提供商", 400)
    return found


def all_providers() -> list[LlmProvider]:
    return list(_PROVIDERS.values())


register(DeepSeekProvider())
register(OpenRouterProvider())

from app.core.config import settings
from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse
from app.services.llm.providers.anthropic import AnthropicProvider
from app.services.llm.providers.mock import MockProvider
from app.services.llm.providers.openai_compatible import OpenAICompatibleProvider


class LLMRouter:
    def __init__(self) -> None:
        self.providers: dict[str, LLMProvider] = {
            "mock": MockProvider(),
            "qwen": OpenAICompatibleProvider(
                name="qwen", api_key=settings.qwen_api_key, base_url=settings.qwen_base_url
            ),
            "deepseek": OpenAICompatibleProvider(
                name="deepseek",
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            ),
            "openai": OpenAICompatibleProvider(
                name="openai",
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            ),
            "claude": AnthropicProvider(settings.anthropic_api_key),
        }

    async def complete(self, request: LLMRequest, provider: str | None = None) -> LLMResponse:
        selected = provider or settings.llm_default_provider
        if selected not in self.providers:
            raise ValueError(f"Unknown LLM provider: {selected}")
        return await self.providers[selected].complete(request)

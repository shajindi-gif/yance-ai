from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse


class MockProvider(LLMProvider):
    name = "mock"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            content="Mock response for local development",
            model=request.model,
            provider=self.name,
        )

    async def embed(self, input_texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("MockProvider does not support embedding")

import httpx

from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse


class AnthropicProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError("Anthropic API key is not configured")
        system = "\n".join(x["content"] for x in request.messages if x["role"] == "system")
        messages = [x for x in request.messages if x["role"] != "system"]
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": request.model,
                    "system": system,
                    "messages": messages,
                    "temperature": request.temperature,
                    "max_tokens": request.max_tokens or 1024,
                },
            )
            response.raise_for_status()
            data = response.json()
        usage = data.get("usage", {})
        return LLMResponse(
            content="".join(item.get("text", "") for item in data["content"]),
            model=data.get("model", request.model),
            provider=self.name,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            raw=data,
        )

    async def embed(self, input_texts: list[str]) -> list[list[float]]:
        raise NotImplementedError("AnthropicProvider does not support embedding")

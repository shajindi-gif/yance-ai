import json

import httpx

from app.services.llm.base import LLMProvider, LLMRequest, LLMResponse


class OpenAICompatibleProvider(LLMProvider):
    def __init__(
        self, *, name: str, api_key: str, base_url: str, embedding_model: str = ""
    ) -> None:
        self.name = name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.embedding_model = embedding_model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured")
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
        }
        if request.response_format:
            payload["response_format"] = request.response_format
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        usage = data.get("usage", {})
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=data.get("model", request.model),
            provider=self.name,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            raw=data,
        )

    async def embed(self, input_texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured")
        if not self.embedding_model:
            raise RuntimeError(f"{self.name} embedding model is not configured")
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.embedding_model, "input": input_texts},
            )
            response.raise_for_status()
            data = response.json()
        return [item["embedding"] for item in data["data"]]

    async def stream(self, request: LLMRequest):
        """Yield content deltas and final usage; never log provider payloads."""
        if not self.api_key:
            raise RuntimeError(f"{self.name} API key is not configured")
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if request.response_format:
            payload["response_format"] = request.response_format
        async with httpx.AsyncClient(timeout=httpx.Timeout(60, connect=10)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            ) as response:
                response.raise_for_status()
                size = 0
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        return
                    size += len(raw)
                    if size > 2_000_000:
                        raise RuntimeError("Provider stream exceeded response limit")
                    data = json.loads(raw)
                    for choice in data.get("choices", []):
                        delta = choice.get("delta", {}).get("content")
                        if delta:
                            yield {"token": delta}
                    if data.get("usage"):
                        yield {"usage": data["usage"]}

"""Task routing, bounded fallback and schema validation. No prompt/content logs."""

import asyncio
import json
import time
from contextvars import ContextVar
from enum import StrEnum

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import LLMCall
from app.services.llm.base import LLMRequest, LLMResponse
from app.services.llm.budget import _scope, reserve, settle
from app.services.llm.router import LLMRouter

last_call_id = ContextVar("gateway_last_call", default=None)


class TaskType(StrEnum):
    extract_criteria = "extract_criteria"
    judge_eligibility = "judge_eligibility"
    chat_answer = "chat_answer"
    draft_material = "draft_material"
    long_document = "long_document"


class InsufficientEvidence(RuntimeError):
    pass


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str
    model: str = Field(min_length=1, max_length=160)


class Route(BaseModel):
    model_config = ConfigDict(extra="forbid")
    primary: Target
    fallback: Target
    temperature: float = Field(default=0, ge=0, le=1)
    max_tokens: int = Field(default=3000, ge=1, le=6000)
    stream: bool = False


def route_for(task: TaskType) -> Route:
    task = TaskType(task)
    judgment = task in {TaskType.extract_criteria, TaskType.judge_eligibility}
    primary = (
        {"provider": "deepseek", "model": "deepseek-chat"}
        if judgment
        else {"provider": "qwen", "model": "qwen-plus"}
    )
    fallback = (
        {"provider": "qwen", "model": "qwen-plus"}
        if judgment
        else {"provider": "deepseek", "model": "deepseek-chat"}
    )
    if settings.llm_default_provider == "mock" and settings.app_env in {
        "development",
        "test",
        "eval",
    }:
        primary = fallback = {"provider": "mock", "model": "mock"}
    override = json.loads(settings.llm_task_routes)
    if not isinstance(override, dict) or set(override) - {t.value for t in TaskType}:
        raise ValueError("Invalid LLM_TASK_ROUTES task names")
    route = Route.model_validate(
        override.get(task.value, {"primary": primary, "fallback": fallback, "stream": not judgment})
    )
    for target in (route.primary, route.fallback):
        if settings.app_env not in {"development", "test", "eval"} and target.provider not in {
            "qwen",
            "deepseek",
        }:
            raise ValueError("Provider is not allowed in this environment")
        if target.provider not in {"qwen", "deepseek", "openai", "claude", "mock"}:
            raise ValueError("Unknown provider")
    return route


def verify_quotes(result: dict, policy_version_text: str) -> tuple[dict, int]:
    """Drop whole claim/criterion with a missing/fabricated quote, never only its citation."""
    rejected = 0

    def normalize(text):
        return "".join(text.split())

    source = normalize(policy_version_text)

    def clean(value):
        nonlocal rejected
        if isinstance(value, list):
            out = []
            for item in value:
                if isinstance(item, dict) and "policy_quote" in item:
                    quote = item.get("policy_quote")
                    if (
                        not isinstance(quote, str)
                        or not normalize(quote)
                        or normalize(quote) not in source
                    ):
                        rejected += 1
                        continue
                out.append(clean(item))
            return out
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        return value

    return clean(result), rejected


def transient(error: Exception) -> bool:
    return isinstance(error, (TimeoutError, httpx.TimeoutException, httpx.ConnectError)) or (
        isinstance(error, httpx.HTTPStatusError) and error.response.status_code >= 500
    )


class LLMGateway:
    def __init__(self):
        self.router = LLMRouter()
        self.providers = self.router.providers

    def _request(self, route, target, messages, schema):
        return LLMRequest(
            messages=messages,
            model=target.model,
            temperature=route.temperature,
            max_tokens=min(route.max_tokens, settings.llm_max_output_tokens),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "result",
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            }
            if schema
            else None,
        )

    def _audit(self, task, target, start, fallback, response=None, rejected=0, status="completed"):
        scope = _scope.get()
        if scope:
            with SessionLocal() as db:
                row = LLMCall(
                    tenant_id=scope[0],
                    user_id=scope[1],
                    task=task.value,
                    provider=target.provider,
                    model=target.model,
                    input_tokens=response.input_tokens if response else None,
                    output_tokens=response.output_tokens if response else None,
                    latency_ms=int((time.monotonic() - start) * 1000),
                    fallback_used=fallback,
                    quote_rejected_count=rejected,
                    status=status,
                )
                db.add(row)
                db.commit()
                last_call_id.set(row.id)

    async def complete(self, task, messages, schema=None, policy_version_text=None):
        task = TaskType(task)
        route = route_for(task)
        for index, target in enumerate((route.primary, route.fallback)):
            for attempt in range(2):
                start = time.monotonic()
                try:
                    response = await asyncio.wait_for(
                        self.router.complete(
                            self._request(route, target, messages, schema), provider=target.provider
                        ),
                        timeout=60,
                    )
                except BaseException as error:
                    self._audit(task, target, start, bool(index), status="failed")
                    if isinstance(error, Exception) and index == 0 and transient(error):
                        break
                    raise
                rejected = 0
                try:
                    if schema:
                        parsed = schema.model_validate_json(response.content).model_dump(
                            mode="json"
                        )
                        if policy_version_text is not None:
                            parsed, rejected = verify_quotes(parsed, policy_version_text)
                        response.content = json.dumps(parsed, ensure_ascii=False)
                except (ValidationError, ValueError) as error:
                    self._audit(task, target, start, bool(index), response, status="invalid_schema")
                    if attempt == 0:
                        continue
                    raise InsufficientEvidence(
                        "模型输出未满足证据结构，请重试或核对原文"
                    ) from error
                self._audit(task, target, start, bool(index), response, rejected)
                response.raw = {
                    **response.raw,
                    "fallback_used": bool(index),
                    "quote_rejected_count": rejected,
                }
                return response
        raise InsufficientEvidence("模型暂不可用")

    async def _stream(self, task, messages, schema=None):
        task = TaskType(task)
        route = route_for(task)
        if not route.stream:
            raise ValueError("Streaming disabled for this task")
        for index, target in enumerate((route.primary, route.fallback)):
            request = self._request(route, target, messages, schema)
            start = time.monotonic()
            emitted = False
            invocation = None
            response = LLMResponse(content="", model=target.model, provider=target.provider)
            try:
                if target.provider == "mock":
                    response = await self.router.complete(request, provider="mock")
                    yield response.content
                else:
                    provider = self.router.providers[target.provider]
                    if not hasattr(provider, "stream"):
                        raise ValueError("Provider does not support this stream protocol")
                    invocation, request.max_tokens = reserve(target.provider, request)
                    async with asyncio.timeout(90):
                        async for event in provider.stream(request):
                            if "token" in event:
                                emitted = True
                                yield event["token"]
                            if "usage" in event:
                                response.input_tokens = event["usage"].get("prompt_tokens")
                                response.output_tokens = event["usage"].get("completion_tokens")
                    settle(invocation, response)
                    invocation = None
                self._audit(task, target, start, bool(index), response)
                return
            except BaseException as error:
                if invocation:
                    settle(invocation)
                self._audit(task, target, start, bool(index), status="failed")
                # Never append a second provider to a partial answer.
                if not emitted and index == 0 and isinstance(error, Exception) and transient(error):
                    continue
                raise

    async def complete_stream(self, task, messages, schema=None):
        # Structured streams stay buffered until schema validation succeeds.
        # Unstructured drafting callers may receive deltas immediately.
        if schema is None:
            async for token in self._stream(task, messages):
                yield token
            return
        for attempt in range(2):
            raw = ""
            async for token in self._stream(task, messages, schema):
                raw += token
                if len(raw) > 64000:
                    raise InsufficientEvidence("Structured response exceeded limit")
            try:
                parsed = schema.model_validate_json(raw)
            except ValidationError as error:
                if last_call_id.get():
                    with SessionLocal() as db:
                        row = db.get(LLMCall, last_call_id.get())
                        if row:
                            row.status = "invalid_schema"
                            db.commit()
                if attempt == 0:
                    continue
                raise InsufficientEvidence("模型输出未满足证据结构") from error
            yield parsed.model_dump_json()
            return

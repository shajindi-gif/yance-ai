"""Tenant-scoped daily call/output reservations. Not a monetary billing claim."""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.models import LLMInvocation, Membership, Tenant, User, UserRole

_scope: ContextVar[tuple[UUID, UUID] | None] = ContextVar("llm_budget_scope", default=None)


class LLMLimitExceeded(RuntimeError):
    pass


@contextmanager
def llm_budget_scope(tenant_id: UUID, user_id: UUID):
    token = _scope.set((tenant_id, user_id))
    try:
        yield
    finally:
        _scope.reset(token)


def reserve(provider, request):
    scope = _scope.get()
    if not scope:
        raise LLMLimitExceeded("Live model call requires server budget scope")
    output = settings.llm_max_output_tokens if request.max_tokens is None else request.max_tokens
    input_bytes = sum(len(str(message).encode("utf8")) for message in request.messages)
    if (
        type(output) is not int
        or not 0 < output <= settings.llm_max_output_tokens
        or input_bytes > settings.llm_max_input_bytes
    ):
        raise LLMLimitExceeded("Model request exceeds per-call limits")
    now = datetime.now(UTC)
    with SessionLocal() as db:
        tenant = db.scalar(
            select(Tenant)
            .where(Tenant.id == scope[0], Tenant.is_active.is_(True))
            .with_for_update()
        )
        if not tenant:
            raise LLMLimitExceeded("Tenant unavailable")
        authorized = db.scalar(
            select(User.id)
            .join(Membership, Membership.user_id == User.id)
            .where(
                User.id == scope[1],
                User.tenant_id == scope[0],
                User.is_active.is_(True),
                Membership.tenant_id == scope[0],
                Membership.status == "active",
                Membership.role.in_([UserRole.owner, UserRole.admin, UserRole.member]),
            )
        )
        if not authorized:
            raise LLMLimitExceeded("Model requester no longer authorized")
        calls, tokens = db.execute(
            select(
                func.count(), func.coalesce(func.sum(LLMInvocation.charged_output_tokens), 0)
            ).where(
                LLMInvocation.tenant_id == scope[0],
                LLMInvocation.created_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
            )
        ).one()
        if (
            calls >= settings.llm_daily_call_limit
            or tokens + output > settings.llm_daily_output_token_limit
        ):
            raise LLMLimitExceeded("Daily model budget exhausted")
        row = LLMInvocation(
            tenant_id=scope[0],
            user_id=scope[1],
            provider=provider,
            model=request.model,
            reserved_output_tokens=output,
            charged_output_tokens=output,
            status="reserved",
        )
        db.add(row)
        db.commit()
        return row.id, output


def settle(invocation_id, response=None):
    with SessionLocal() as db:
        row = db.get(LLMInvocation, invocation_id, with_for_update=True)
        if not row or row.status != "reserved":
            return
        row.status = "completed" if response else "uncertain"
        usage = response.output_tokens if response else None
        if type(usage) is int and 0 <= usage <= row.reserved_output_tokens:
            row.charged_output_tokens = usage
        row.finished_at = datetime.now(UTC)
        db.commit()

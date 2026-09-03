"""Canonical tenant-aware visibility rules for global and private policies."""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.models.models import Policy


def visible_policy_clause(tenant_id: UUID) -> ColumnElement[bool]:
    return or_(Policy.tenant_id.is_(None), Policy.tenant_id == tenant_id)

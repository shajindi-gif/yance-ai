import asyncio
import uuid

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api import deps
from app.api.deps import Principal
from app.api.routes.commerce import create_order
from app.api.routes.documents import complete_upload, validate_upload
from app.api.routes.tasks import RevisionCreate, request_revision
from app.api.routes.telemetry import capture_event, start_agent_run
from app.api.routes.tenants import create_user
from app.core.config import settings
from app.models.models import Document, Membership, Product, Task, User, UserRole
from app.schemas.schemas import (
    AgentRunCreate,
    AnalyticsEventCreate,
    DocumentComplete,
    OrderCreate,
    UserCreate,
)
from app.services.policies.visibility import visible_policy_clause


def _principal(role: UserRole = UserRole.owner) -> Principal:
    tenant_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="security@example.com",
        full_name="Security Test",
        password_hash="unused",
        auth_version=0,
        role=role,
        is_active=True,
    )
    return Principal(user=user, tenant_id=tenant_id, role=role)


class FakeDb:
    def __init__(self, scalar_results: list[object] | None = None):
        self.scalar_results = iter(scalar_results or [])
        self.queries: list[object] = []
        self.added: list[object] = []
        self.commits = 0

    def scalar(self, query):
        self.queries.append(query)
        return next(self.scalar_results)

    def add(self, record):
        self.added.append(record)

    def commit(self):
        self.commits += 1

    def flush(self):
        return None

    def refresh(self, _record):
        return None


class FakeStorage:
    def __init__(self, size: int):
        self.size = size

    def exists(self, _object_key: str) -> bool:
        return True

    def object_size(self, _object_key: str) -> int:
        return self.size


def test_principal_query_requires_an_active_tenant(monkeypatch):
    principal = _principal()
    monkeypatch.setattr(
        deps,
        "decode_access_token",
        lambda _token: {
            "sub": str(principal.user.id),
            "tenant_id": str(principal.tenant_id),
        },
    )
    membership = Membership(
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        role=UserRole.owner,
        status="active",
    )
    db = FakeDb([principal.user, membership])

    result = deps.get_principal(
        request=Request({"type": "http", "method": "GET", "path": "/api/v1/companies", "headers": []}),
        token="token",
        x_api_key=None,
        db=db,
    )

    query = str(db.queries[0])
    assert "JOIN tenants" in query
    assert "tenants.is_active" in query
    assert result.tenant_id == principal.tenant_id


def test_policy_visibility_includes_global_and_current_tenant_only():
    tenant_id = uuid.uuid4()
    clause = str(visible_policy_clause(tenant_id))
    assert "policies.tenant_id IS NULL" in clause
    assert "policies.tenant_id =" in clause


@pytest.mark.parametrize(
    ("filename", "content_type"),
    [
        ("company.pdf", "application/pdf"),
        (
            "profile.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        ("facts.csv", "text/csv"),
    ],
)
def test_supported_document_uploads(filename, content_type):
    validate_upload(filename, content_type, 1024)


def test_document_upload_rejects_executables_and_oversized_files():
    with pytest.raises(HTTPException) as executable:
        validate_upload("payload.html", "text/html", 100)
    assert executable.value.status_code == 415

    with pytest.raises(HTTPException) as oversized:
        validate_upload("large.pdf", "application/pdf", settings.document_upload_max_bytes + 1)
    assert oversized.value.status_code == 413


def test_document_completion_rejects_size_mismatch():
    principal = _principal()
    document = Document(
        id=uuid.uuid4(),
        tenant_id=principal.tenant_id,
        filename="company.pdf",
        content_type="application/pdf",
        object_key=f"tenants/{principal.tenant_id}/documents/file.pdf",
        status="pending_upload",
        size_bytes=100,
    )
    db = FakeDb([document])

    with pytest.raises(HTTPException) as mismatch:
        complete_upload(
            document_id=document.id,
            payload=DocumentComplete(),
            principal=principal,
            db=db,
            storage=FakeStorage(size=99),
        )

    assert mismatch.value.status_code == 409
    assert document.status == "rejected"
    assert db.commits == 1


def test_admin_cannot_promote_another_owner():
    principal = _principal(UserRole.admin)
    payload = UserCreate(
        email="new-owner@example.com",
        full_name="New Owner",
        password="a-secure-password",
        role=UserRole.owner,
    )
    with pytest.raises(HTTPException) as forbidden:
        create_user(payload=payload, principal=principal, db=FakeDb())
    assert forbidden.value.status_code == 403


def test_commerce_rejects_cross_tenant_product_resource():
    principal = _principal()
    product = Product(
        id=uuid.uuid4(),
        code="POLICY_REPORT",
        name="Policy report",
        product_type="report",
        price=99,
        entitlement_type="report",
        active=True,
    )
    db = FakeDb([product, None])
    with pytest.raises(HTTPException) as not_found:
        create_order(
            payload=OrderCreate(product_code=product.code, resource_id=uuid.uuid4()),
            principal=principal,
            db=db,
        )
    assert not_found.value.status_code == 404
    assert db.added == []


def test_revision_rejects_deliverable_from_another_scope():
    principal = _principal()
    task = Task(
        id=uuid.uuid4(),
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        company_id=uuid.uuid4(),
        task_type="policy_scan",
        title="Scan",
        status="delivered",
    )
    db = FakeDb([task, None])
    with pytest.raises(HTTPException) as not_found:
        asyncio.run(
            request_revision(
                task_id=task.id,
                req=RevisionCreate(deliverable_id=uuid.uuid4(), request="Please update evidence"),
                principal=principal,
                db=db,
            )
        )
    assert not_found.value.status_code == 404


def test_clients_cannot_fabricate_analytics_or_agent_runs():
    principal = _principal()
    with pytest.raises(HTTPException) as analytics_disabled:
        capture_event(
            payload=AnalyticsEventCreate(name="payment_completed"),
            principal=principal,
            db=FakeDb(),
        )
    assert analytics_disabled.value.status_code == 501

    with pytest.raises(HTTPException) as runs_disabled:
        start_agent_run(
            payload=AgentRunCreate(agent_name="fake", provider="fake", model="fake"),
            principal=principal,
            db=FakeDb(),
        )
    assert runs_disabled.value.status_code == 501

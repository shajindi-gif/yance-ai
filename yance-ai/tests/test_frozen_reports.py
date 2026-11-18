"""Regression gates for stable delivery, purchasing readiness and tenant isolation."""
import hashlib
import uuid

from fastapi.testclient import TestClient
from report_fixture import ready_report
from sqlalchemy import func, select
from test_funding_os import _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Company, Deliverable, Entitlement, Order, Product


def test_empty_company_cannot_buy_report_and_no_order_is_created():
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        company = client.get('/api/v1/companies', headers=headers).json()[0]
        response = client.post('/api/v1/orders', headers=headers,
            json={'product_code': 'POLICY_REPORT', 'resource_id': company['id']})
        assert response.status_code == 409
        assert response.json()['detail']['code'] == 'report_not_ready'
        with SessionLocal() as db:
            assert db.scalar(select(func.count()).select_from(Order).where(Order.tenant_id == uuid.UUID(me['tenant_id']))) == 0


def test_report_bytes_stable_order_bound_hash_verified_and_tenant_isolated():
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        other, _ = _register(client, uuid.uuid4().hex)
        company = client.get('/api/v1/companies', headers=headers).json()[0]
        report_id, task_id, original = ready_report(company['id'])
        url = f'/api/v1/tasks/{task_id}/download'
        assert client.get(url, headers=headers).content == original
        assert client.get(url, headers=other).status_code == 404
        order = client.post('/api/v1/orders', headers=headers, json={
            'product_code': 'POLICY_REPORT', 'resource_id': company['id'],
            'client_request_id': str(uuid.uuid4())})
        assert order.status_code == 201, order.text
        # Contract-level settlement, never an actual provider/payment.
        with SessionLocal() as db:
            row = db.get(Order, uuid.UUID(order.json()['id']))
            assert str(row.report_deliverable_id) == report_id
            row.status = 'paid'
            product = db.scalar(select(Product).where(Product.code == 'POLICY_REPORT'))
            db.add(Entitlement(tenant_id=row.tenant_id, order_id=row.id, product_id=product.id,
                resource_type='report', resource_id=row.resource_id, status='active'))
            db.get(Company, uuid.UUID(company['id'])).name = '客户修改后的企业名称'
            db.commit()
        # A later artifact must not replace the purchased version.
        newer_id, _, _ = ready_report(company['id'])
        with SessionLocal() as db:
            newer = db.get(Deliverable, uuid.UUID(newer_id))
            newer.frozen_pdf = b'newer synthetic version'
            newer.frozen_pdf_sha256 = hashlib.sha256(newer.frozen_pdf).hexdigest()
            db.commit()
        paid_url = f"/api/v1/reports/{company['id']}/download"
        assert client.get(url, headers=headers).content == original
        assert client.get(paid_url, headers=headers).content == original
        assert client.get(paid_url + "?order_id=" + order.json()["id"], headers=headers).content == original
        assert client.get(paid_url + "?order_id=" + str(uuid.uuid4()), headers=headers).status_code == 409
        assert client.get(paid_url, headers=other).status_code == 404
        foreign_company = client.get('/api/v1/companies', headers=other).json()[0]
        foreign_id, _, _ = ready_report(foreign_company['id'])
        with SessionLocal() as db:
            db.get(Order, uuid.UUID(order.json()['id'])).report_deliverable_id = uuid.UUID(foreign_id)
            db.commit()
        assert client.get(paid_url, headers=headers).status_code == 409
        with SessionLocal() as db:
            db.get(Order, uuid.UUID(order.json()['id'])).report_deliverable_id = uuid.UUID(report_id)
            db.commit()

        with SessionLocal() as db:
            db.get(Deliverable, uuid.UUID(report_id)).frozen_pdf = b'tampered'
            db.commit()
        assert client.get(url, headers=headers).status_code == 409
        assert client.get(paid_url, headers=headers).status_code == 409


def test_legacy_report_not_rebuilt_and_historical_rights_retained():
    with TestClient(app) as client:
        headers, _ = _register(client, uuid.uuid4().hex)
        company = client.get('/api/v1/companies', headers=headers).json()[0]
        report_id, task_id, _ = ready_report(company['id'])
        with SessionLocal() as db:
            row = db.get(Deliverable, uuid.UUID(report_id))
            row.frozen_pdf = row.frozen_pdf_sha256 = None
            db.commit()
        response = client.get(f'/api/v1/tasks/{task_id}/download', headers=headers)
        assert response.status_code == 409
        assert '原订单和权益保留' in response.json()['detail']


def test_real_renderer_persists_snapshot_without_putting_bytes_in_tool_events():
    from unittest.mock import Mock

    from test_agent_harness import _queued_run

    from app.services.agents.policy_scan import _create_report_artifact
    with SessionLocal() as db:
        run, _, task = _queued_run(db, suffix=uuid.uuid4().hex)
        company = db.get(Company, task.company_id)
        harness = Mock()
        result = _create_report_artifact(db, run, task, company, [], None, harness)
        db.flush()
        row = db.get(Deliverable, result.deliverable_id)
        assert row.frozen_pdf.startswith(b'%PDF-')
        assert row.frozen_pdf_sha256 == hashlib.sha256(row.frozen_pdf).hexdigest()
        summary = harness._finish_tool.call_args.args[2]
        assert not any(isinstance(v, bytes) for v in summary.values())
        assert 'frozen_pdf' not in summary


def test_failed_generation_is_not_a_sellable_or_downloadable_report():
    from app.models.models import Task
    with TestClient(app) as client:
        headers, _ = _register(client, uuid.uuid4().hex)
        company = client.get('/api/v1/companies', headers=headers).json()[0]
        _, task_id, _ = ready_report(company['id'])
        with SessionLocal() as db:
            db.get(Task, uuid.UUID(task_id)).status = 'failed'
            db.commit()
        response = client.post('/api/v1/orders', headers=headers, json={
            'product_code': 'POLICY_REPORT', 'resource_id': company['id']})
        assert response.status_code == 409
        assert client.get(f'/api/v1/tasks/{task_id}/download', headers=headers).status_code == 409

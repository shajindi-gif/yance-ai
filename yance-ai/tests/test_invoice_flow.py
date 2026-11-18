"""数电票人工闭环 e2e：用户申请 → 后台待办 → 开具(上传发票文件) → 通知+下载 / 驳回。"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from report_fixture import ready_report
from sqlalchemy import select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Invoice, Notification, Order, User

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("APP_ENV") != "test",
        reason="Invoice flow tests require the migrated PostgreSQL test database",
    ),
]

client = TestClient(app)

FAKE_EINVOICE_PDF = b"%PDF-1.4 fake e-invoice from shanghai etax for test"


def _register(suffix: str) -> tuple[dict[str, str], str]:
    email = f"inv-{suffix}@example.com"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"发票测试公司 {suffix}",
            "owner_email": email,
            "owner_name": "开票测试",
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}, email


def _paid_order(headers: dict) -> str:
    """Create an order and mark it paid directly (settlement covered elsewhere)."""
    # 下单需要 product + resource：直接造一条 paid 订单更聚焦发票域
    resp = client.get("/api/v1/companies", headers=headers)
    company_id = resp.json()[0]["id"]
    ready_report(company_id)
    products = client.get("/api/v1/products").json()
    product = next(p for p in products if p["code"] == "POLICY_REPORT")
    resp = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"product_code": product["code"], "resource_id": company_id},
    )
    assert resp.status_code == 201, resp.text
    order_id = resp.json()["id"]
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_id))
        order.status = "paid"
        db.commit()
    return order_id


def _make_platform_admin(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        user.is_platform_admin = True
        db.commit()


def test_invoice_manual_loop_request_issue_download():
    suffix = uuid.uuid4().hex[:8]
    headers, _ = _register(suffix)
    admin_headers, admin_email = _register(f"admin-{suffix}")
    _make_platform_admin(admin_email)
    order_id = _paid_order(headers)

    # 1. 用户申请开票 → 进入待办
    req = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={
            "order_id": order_id,
            "title": "上海某某科技有限公司",
            "tax_number": "91310000MA1FL0000X",
        },
    )
    assert req.status_code == 202, req.text
    invoice = req.json()
    assert invoice["status"] == "requested"
    invoice_id = invoice["id"]

    # 未开具前下载凭证 → 404
    assert client.get(f"/api/v1/invoices/{invoice_id}/voucher", headers=headers).status_code == 404

    # 2. 后台待办列表能看到
    pending = client.get("/api/v1/admin/invoices", headers=admin_headers, params={"status": "requested"})
    assert pending.status_code == 200, pending.text
    assert any(item["id"] == invoice_id for item in pending.json()["items"])

    # 3. 运营开具：上传数电票文件
    issue = client.post(
        f"/api/v1/admin/invoices/{invoice_id}/issue",
        headers=admin_headers,
        files={"file": ("电子发票_测试.pdf", FAKE_EINVOICE_PDF, "application/pdf")},
        data={"note": "数电票已开"},
    )
    assert issue.status_code == 200, issue.text
    assert issue.json()["status"] == "issued"

    # 4. 通知已生成
    with SessionLocal() as db:
        note = db.scalar(
            select(Notification).where(
                Notification.dedup_key == f"invoice_issued:{invoice_id}"
            )
        )
        assert note is not None and note.kind == "invoice"

    # 5. 用户下载到原样字节
    voucher = client.get(f"/api/v1/invoices/{invoice_id}/voucher", headers=headers)
    assert voucher.status_code == 200
    assert voucher.content == FAKE_EINVOICE_PDF
    assert "attachment" in voucher.headers["content-disposition"]

    # 6. 已开具的发票不能重复开具
    again = client.post(
        f"/api/v1/admin/invoices/{invoice_id}/issue",
        headers=admin_headers,
        files={"file": ("again.pdf", b"x", "application/pdf")},
    )
    assert again.status_code == 409


def test_invoice_reject_flow_notifies_user():
    suffix = uuid.uuid4().hex[:8]
    headers, _ = _register(suffix)
    admin_headers, admin_email = _register(f"admin2-{suffix}")
    _make_platform_admin(admin_email)
    order_id = _paid_order(headers)

    req = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={"order_id": order_id, "title": "抬头有误有限公司", "tax_number": "91310000MA1FL0000X"},
    )
    invoice_id = req.json()["id"]

    reject = client.post(
        f"/api/v1/admin/invoices/{invoice_id}/reject",
        headers=admin_headers,
        json={"reason": "税号位数不对，请核对后重新申请"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == "rejected"

    with SessionLocal() as db:
        note = db.scalar(
            select(Notification).where(Notification.dedup_key == f"invoice_rejected:{invoice_id}")
        )
        assert note is not None
        invoice = db.get(Invoice, uuid.UUID(invoice_id))
        assert invoice.review_note == "税号位数不对，请核对后重新申请"
        assert invoice.voucher_data is None


def test_unpaid_order_cannot_request_invoice():
    suffix = uuid.uuid4().hex[:8]
    headers, _ = _register(suffix)
    resp = client.get("/api/v1/companies", headers=headers)
    company_id = resp.json()[0]["id"]
    ready_report(company_id)
    products = client.get("/api/v1/products").json()
    product = next(p for p in products if p["code"] == "POLICY_REPORT")
    order = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"product_code": product["code"], "resource_id": company_id},
    )
    order_id = order.json()["id"]  # status=created（未支付）
    resp = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={"order_id": order_id, "title": "测试", "tax_number": "91310000MA1FL0000X"},
    )
    assert resp.status_code == 400
    assert "paid" in resp.json()["detail"]


def test_non_admin_cannot_access_invoice_backoffice():
    suffix = uuid.uuid4().hex[:8]
    headers, _ = _register(suffix)
    assert client.get("/api/v1/admin/invoices", headers=headers).status_code == 403

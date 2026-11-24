"""Unclassified tenants can contain demo payments: status alone is not revenue."""

import uuid

from app.core.db import SessionLocal
from app.models.models import Order, Payment, PaymentEvent, Tenant
from app.services.admin.metrics import investor_metrics
from app.services.analytics.events import record_event


def test_revenue_requires_matching_real_provider_receipt_and_never_duplicates_orders():
    with SessionLocal() as db:
        baseline = investor_metrics(db)
        tenant = Tenant(
            name="Synthetic payment metrics",
            slug=uuid.uuid4().hex,
            is_demo=False,
            account_stage="unclassified",
        )
        other = Tenant(name="Other synthetic metrics", slug=uuid.uuid4().hex)
        db.add_all([tenant, other])
        db.flush()

        def order(
            provider,
            *,
            payment_amount=47,
            currency="CNY",
            receipt_status="processed",
            receipt_tenant=None,
            copies=1,
            payment_status="completed",
        ):
            row = Order(
                tenant_id=tenant.id,
                order_no="M" + uuid.uuid4().hex,
                product_code="SYNTHETIC_METRICS",
                amount=47,
                currency="CNY",
                status="paid",
            )
            db.add(row)
            db.flush()
            payment = Payment(
                tenant_id=tenant.id,
                order_id=row.id,
                provider=provider,
                provider_trade_no="P" + uuid.uuid4().hex,
                amount=payment_amount,
                currency=currency,
                status=payment_status,
            )
            db.add(payment)
            db.flush()
            if receipt_status:
                for _ in range(copies):
                    db.add(
                        PaymentEvent(
                            tenant_id=receipt_tenant or tenant.id,
                            payment_id=payment.id,
                            provider=provider,
                            provider_event_id=uuid.uuid4().hex,
                            event_type="synthetic-metrics-contract",
                            payload_sha256="a" * 64,
                            status=receipt_status,
                        )
                    )
            db.flush()

        order("demo")
        order("mock")
        order("alipay", payment_amount=46)
        order("wechat", receipt_status=None)
        order("alipay", receipt_tenant=other.id)
        order("alipay", currency="USD")
        order("wechat", receipt_status="received")
        order("wechat", payment_status="pending")
        record_event(
            db,
            tenant_id=tenant.id,
            user_id=None,
            name="payment_completed",
            event_key="synthetic-metrics:" + uuid.uuid4().hex,
        )
        db.commit()
        unverified = investor_metrics(db)
        assert unverified["revenue_by_currency"] == baseline["revenue_by_currency"]
        assert unverified["totals"]["paying_customers"] == baseline["totals"]["paying_customers"]
        assert (
            unverified["totals"]["unverified_paid_orders"]
            == baseline["totals"]["unverified_paid_orders"] + 8
        )

        def completed(metrics):
            return next(
                x["organizations"] for x in metrics["funnel"] if x["event"] == "payment_completed"
            )

        assert completed(unverified) == completed(baseline)
        order("wechat", copies=2)
        db.commit()
        confirmed = investor_metrics(db)
        old_money = {r["currency"]: r["amount"] for r in baseline["revenue_by_currency"]}
        new_money = {r["currency"]: r["amount"] for r in confirmed["revenue_by_currency"]}
        assert new_money["CNY"] == old_money.get("CNY", 0) + 47
        assert confirmed["totals"]["paying_customers"] == baseline["totals"]["paying_customers"] + 1
        assert completed(confirmed) == completed(baseline) + 1

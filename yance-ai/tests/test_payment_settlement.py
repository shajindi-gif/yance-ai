import uuid
from decimal import Decimal

from app.models.models import (
    AnalyticsEvent,
    Entitlement,
    Order,
    Payment,
    PaymentEvent,
    Product,
)
from app.services.payments.settlement import settle_payment, validate_settlement


def _records() -> tuple[Order, Payment, Product]:
    tenant_id = uuid.uuid4()
    order = Order(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        order_no="ORDER-1",
        product_code="POLICY_REPORT",
        amount=Decimal("299.00"),
        currency="CNY",
        resource_type="report",
        resource_id=uuid.uuid4(),
        status="pending",
    )
    payment = Payment(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        order_id=order.id,
        provider="alipay",
        provider_trade_no="OUT-1",
        amount=Decimal("299.00"),
        currency="CNY",
        status="created",
    )
    product = Product(
        id=uuid.uuid4(),
        code="POLICY_REPORT",
        name="Policy report",
        product_type="report",
        price=Decimal("299.00"),
        entitlement_type="report",
        active=True,
    )
    return order, payment, product


class FakeSession:
    def __init__(self, scalar_results: list[object]):
        self.scalar_results = iter(scalar_results)
        self.added: list[object] = []
        self.commits = 0
        self.rollbacks = 0

    def scalar(self, _query):
        return next(self.scalar_results)

    def add(self, record):
        self.added.append(record)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_validate_settlement_requires_exact_amount_currency_and_tenant():
    order, payment, _ = _records()
    assert (
        validate_settlement(
            order=order,
            payment=payment,
            paid_amount="299.00",
            currency="cny",
        )
        is None
    )
    assert (
        validate_settlement(
            order=order,
            payment=payment,
            paid_amount="2.99",
            currency="CNY",
        )
        == "amount_mismatch"
    )
    assert (
        validate_settlement(
            order=order,
            payment=payment,
            paid_amount="299.00",
            currency="USD",
        )
        == "currency_mismatch"
    )
    payment.tenant_id = uuid.uuid4()
    assert (
        validate_settlement(
            order=order,
            payment=payment,
            paid_amount="299.00",
            currency="CNY",
        )
        == "payment_order_mismatch"
    )


def test_settlement_creates_one_entitlement_and_real_analytics_event():
    order, payment, product = _records()
    db = FakeSession([None, order, product, None, None])

    result = settle_payment(
        db,
        payment=payment,
        provider_event_id="TRADE-1:TRADE_SUCCESS",
        event_type="TRADE_SUCCESS",
        paid_amount="299.00",
        currency="CNY",
        payload=b"signed-provider-payload",
    )

    assert result.accepted is True
    assert result.replayed is False
    assert payment.status == "completed"
    assert order.status == "paid"
    assert db.commits == 1
    assert len([item for item in db.added if isinstance(item, PaymentEvent)]) == 1
    assert len([item for item in db.added if isinstance(item, Entitlement)]) == 1
    entitlement = next(item for item in db.added if isinstance(item, Entitlement))
    assert entitlement.resource_id == order.resource_id
    analytics = [item for item in db.added if isinstance(item, AnalyticsEvent)]
    assert len(analytics) == 1
    assert analytics[0].name == "payment_completed"
    assert analytics[0].source == "server"
    assert analytics[0].event_key == f"payment_completed:{order.id}"


def test_settlement_rejects_amount_mismatch_without_entitlement():
    order, payment, _ = _records()
    db = FakeSession([None, order])

    result = settle_payment(
        db,
        payment=payment,
        provider_event_id="EVENT-UNDERPAID",
        event_type="checkout.session.completed",
        paid_amount="1.00",
        currency="CNY",
        payload=b"payload",
    )

    assert result.accepted is False
    assert result.error_code == "amount_mismatch"
    assert payment.status == "created"
    assert order.status == "pending"
    assert not any(isinstance(item, Entitlement) for item in db.added)
    event = next(item for item in db.added if isinstance(item, PaymentEvent))
    assert event.status == "rejected"


def test_settlement_treats_existing_provider_event_as_replay():
    _, payment, _ = _records()
    existing = PaymentEvent(
        tenant_id=payment.tenant_id,
        payment_id=payment.id,
        provider="alipay",
        provider_event_id="EVENT-1",
        event_type="TRADE_SUCCESS",
        payload_sha256="a" * 64,
        status="processed",
    )
    db = FakeSession([existing])

    result = settle_payment(
        db,
        payment=payment,
        provider_event_id="EVENT-1",
        event_type="TRADE_SUCCESS",
        paid_amount="299.00",
        currency="CNY",
        payload=b"same-event-retry",
    )

    assert result.accepted is True
    assert result.replayed is True
    assert db.added == []
    assert db.commits == 0

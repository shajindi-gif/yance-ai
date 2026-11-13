import base64
import json

import httpx
import pytest
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from fastapi import HTTPException
from test_payment_settlement import FakeSession, _records

from app.api.routes.payments import query_alipay_payment
from app.core.config import settings
from app.services.payments import alipay


@pytest.fixture
def gateway(monkeypatch):
    key = RSA.generate(2048)
    monkeypatch.setattr(settings, "alipay_public_key", key.public_key().export_key().decode())
    monkeypatch.setattr(settings, "alipay_private_key", key.export_key().decode())

    def respond(data, tamper=False):
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        signature = base64.b64encode(PKCS1_v1_5.new(key).sign(SHA256.new(body.encode()))).decode()
        if tamper:
            body = body.replace("299.00", "1.00")
        response = (
            '{"alipay_trade_query_response":' + body + ',"sign":' + json.dumps(signature) + "}"
        )
        monkeypatch.setattr(
            alipay.httpx,
            "post",
            lambda *args, **kwargs: httpx.Response(
                200, text=response, request=httpx.Request("POST", "https://example.invalid")
            ),
        )

    return respond


def test_signed_query_settles_then_replay_uses_same_provider_event(gateway):
    order, payment, product = _records()
    gateway(
        {
            "code": "10000",
            "out_trade_no": payment.provider_trade_no,
            "trade_no": "TEST-TRADE",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "299.00",
        }
    )
    db = FakeSession([None, order, product, None, None])
    assert query_alipay_payment(db, payment)["status"] == "paid"
    event = next(item for item in db.added if getattr(item, "provider_event_id", None))
    assert event.provider_event_id == "TEST-TRADE:TRADE_SUCCESS"
    replay = FakeSession([event])
    assert query_alipay_payment(replay, payment)["status"] == "paid"
    assert replay.added == []


def test_signed_query_rejects_wrong_amount(gateway):
    order, payment, _ = _records()
    gateway(
        {
            "code": "10000",
            "out_trade_no": payment.provider_trade_no,
            "trade_no": "TEST-TRADE",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "1.00",
        }
    )
    with pytest.raises(HTTPException) as failure:
        query_alipay_payment(FakeSession([None, order]), payment)
    assert failure.value.status_code == 409
    assert order.status == "pending"


def test_gateway_rejects_modified_raw_response(gateway):
    gateway({"code": "10000", "total_amount": "299.00"}, tamper=True)
    with pytest.raises(HTTPException) as failure:
        alipay.call("alipay.trade.query", {}, lambda _: "test-request")
    assert failure.value.status_code == 502

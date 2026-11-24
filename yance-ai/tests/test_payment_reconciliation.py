from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from test_payment_expiry import records

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Payment, ReconciliationIssue, ReconciliationRun
from app.services.payments import bills
from app.services.payments.bills import BillRecord, parse_bill
from app.services.payments.reconciliation import compare, reconcile


def test_bill_parser_uses_gross_amount_and_rejects_unsupported_or_partial_rows():
    raw = "交易时间,商户订单号,微信订单号,交易状态,订单金额,申请退款金额,商户退款单号,微信退款单号\n`2026-11-12,`YTEST,`WXTEST,`SUCCESS,`99.00,`0.00,`,``\n总交易单数,1\n".encode()
    parsed = parse_bill("wechat", raw)
    assert parsed[0].amount == Decimal("99.00")
    assert parsed[0].reference == "YTEST"
    with pytest.raises(ValueError):
        parse_bill("wechat", b"unrecognized content")
    with pytest.raises(ValueError):
        parse_bill("wechat", "商户订单号,交易状态\nYTEST\n".encode())


def test_dry_run_does_not_write_and_replay_deduplicates_issues(monkeypatch):
    with TestClient(app) as client:
        _, payment_id = records(client)
        with SessionLocal() as db:
            payment = db.get(Payment, payment_id)
            raw = (
                "商户订单号,支付宝交易号,业务类型,收入（+元）,支出（-元）\n"
                + payment.provider_trade_no
                + ",TEST,交易,99.00,0.00\n"
            ).encode()
            day = date(2026, 1, 2)
            monkeypatch.setattr(bills, "download_bill", lambda *args: raw)
            before = db.scalar(select(func.count()).select_from(ReconciliationRun))
            result = reconcile(db, "alipay", day, dry_run=True)
            assert result["issues"] == 1
            assert db.scalar(select(func.count()).select_from(ReconciliationRun)) == before
            for _ in range(2):
                result = reconcile(db, "alipay", day)
                assert result["status"] in {"partial", "differences"}
            assert (
                db.scalar(
                    select(func.count())
                    .select_from(ReconciliationIssue)
                    .where(
                        ReconciliationIssue.provider == "alipay",
                        ReconciliationIssue.bill_date == day,
                        ReconciliationIssue.reference == payment.provider_trade_no,
                    )
                )
                == 1
            )
            mismatch = compare(
                db,
                "alipay",
                day,
                [BillRecord(payment.provider_trade_no, "TEST", "paid", Decimal("0.01"))],
            )
            assert any(item["issue_type"] == "amount_or_currency_mismatch" for item in mismatch)


def test_unavailable_bill_records_waiting_instead_of_matching(monkeypatch):
    monkeypatch.setattr(
        bills, "download_bill", lambda *args: (_ for _ in ()).throw(ValueError("not ready"))
    )
    with SessionLocal() as db:
        assert reconcile(db, "wechat", date(2026, 1, 3))["status"] == "waiting"

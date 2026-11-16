import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from report_fixture import ready_report
from test_funding_os import _register

from app.api.routes.payments import _checkout_payment
from app.core.db import SessionLocal
from app.main import app
from app.models.models import Order, Payment


def test_different_requests_cannot_create_two_payable_orders_and_resume_is_scoped():
    with TestClient(app) as client:
        headers, _ = _register(client, uuid.uuid4().hex)
        other, _ = _register(client, uuid.uuid4().hex)
        company=client.get('/api/v1/companies',headers=headers).json()[0]
        ready_report(company['id'])
        def create(_):
            return client.post('/api/v1/orders',headers=headers,json={
                'product_code':'POLICY_REPORT','resource_id':company['id'],
                'client_request_id':str(uuid.uuid4())})
        with ThreadPoolExecutor(max_workers=3) as pool:
            rows=list(pool.map(create,range(3)))
        assert sorted(r.status_code for r in rows)==[201,409,409]
        order=next(r.json() for r in rows if r.status_code==201)
        url=f"/api/v1/orders/{order['id']}/checkout"
        state=client.get(url,headers=headers)
        assert state.status_code==200 and state.json()['can_continue']
        assert state.json()['order']['amount']==99
        assert client.get(url,headers=other).status_code==404
        with SessionLocal() as db:
            row=db.get(Order,uuid.UUID(order['id']))
            db.add(Payment(tenant_id=row.tenant_id,order_id=row.id,provider='wechat',amount=row.amount,currency='CNY',status='pending'))
            db.commit()
        assert client.get(url,headers=headers).json()['provider']=='wechat'
        with SessionLocal() as db:
            row=db.get(Order,uuid.UUID(order['id']))
            row.report_deliverable_id=None
            db.commit()
            with pytest.raises(HTTPException) as e:
                _checkout_payment(db,row,'wechat')
            assert e.value.status_code==409
        state=client.get(url,headers=headers).json()
        assert not state['can_continue'] and '固定报告' in state['reason']


def test_paid_report_with_active_entitlement_is_not_sold_twice():
    from sqlalchemy import select

    from app.models.models import Entitlement, Product
    with TestClient(app) as client:
        headers, _ = _register(client, uuid.uuid4().hex)
        company=client.get('/api/v1/companies',headers=headers).json()[0]
        ready_report(company['id'])
        payload={'product_code':'POLICY_REPORT','resource_id':company['id'],'client_request_id':str(uuid.uuid4())}
        response=client.post('/api/v1/orders',headers=headers,json=payload)
        assert response.status_code==201
        with SessionLocal() as db:
            order=db.get(Order,uuid.UUID(response.json()['id']))
            product=db.scalar(select(Product).where(Product.code=='POLICY_REPORT'))
            order.status='paid'
            db.add(Entitlement(tenant_id=order.tenant_id,order_id=order.id,product_id=product.id,resource_type='report',resource_id=order.resource_id,status='active'))
            db.commit()
        retry=client.post('/api/v1/orders',headers=headers,json=payload)
        assert retry.status_code==201 and retry.json()['status']=='paid'
        new=client.post('/api/v1/orders',headers=headers,json={**payload,'client_request_id':str(uuid.uuid4())})
        assert new.status_code==409 and new.json()['detail']['code']=='report_already_owned'


def test_bad_invoice_identifiers_are_validation_errors_not_server_failures():
    with TestClient(app) as client:
        headers,_=_register(client,uuid.uuid4().hex)
        for path in ['download','voucher']:
            assert client.get('/api/v1/invoices/not-a-uuid/'+path,headers=headers).status_code==422
        assert client.post('/api/v1/invoices/not-a-uuid/generate-pdf',headers=headers).status_code==422

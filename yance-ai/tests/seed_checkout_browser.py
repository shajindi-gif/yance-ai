"""Guarded synthetic owner/order for real local browser/API verification."""
import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy.engine import make_url

u=make_url(os.environ['DATABASE_URL'])
assert os.environ['APP_ENV']=='test' and u.host in {'localhost','127.0.0.1'}
assert u.database.endswith('_test') and os.environ['YANCE_TEST_DATABASE_ACK']==u.database
out=Path(sys.argv[1]).resolve()
assert not out.is_relative_to(Path(__file__).resolve().parents[2])
from fastapi.testclient import TestClient  # noqa: E402
from report_fixture import ready_report  # noqa: E402
from test_funding_os import _register  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models.models import Order, Payment  # noqa: E402

with TestClient(app) as client:
    headers,_=_register(client,uuid.uuid4().hex)
    company=client.get('/api/v1/companies',headers=headers).json()[0]
    ready_report(company['id'])
    response=client.post('/api/v1/orders',headers=headers,json={'product_code':'POLICY_REPORT','resource_id':company['id']})
    assert response.status_code==201
    order_id=response.json()['id']
    with SessionLocal() as db:
        order=db.get(Order,uuid.UUID(order_id))
        db.add(Payment(tenant_id=order.tenant_id,order_id=order.id,provider='wechat',amount=order.amount,currency='CNY',status='pending'))
        db.commit()
    out.write_text(json.dumps({'token':headers['Authorization'].removeprefix('Bearer '),'order_id':order_id}))
    out.chmod(0o600)
print('Private synthetic checkout fixture ready')

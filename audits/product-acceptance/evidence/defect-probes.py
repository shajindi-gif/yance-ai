"""Audit-only regression probes, explicit synthetic local DB, no provider calls."""
import os,json,uuid,hashlib
from sqlalchemy.engine import make_url
u=make_url(os.environ['DATABASE_URL'])
assert os.environ['APP_ENV']=='test' and u.host in {'127.0.0.1','localhost'} and u.database.endswith('_test') and os.environ['YANCE_TEST_DATABASE_ACK']==u.database
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.db import SessionLocal
from app.models.models import Company,Product,Order,Entitlement,Task,Deliverable
c=TestClient(app,client=('127.0.0.3',50001))
a=c.post('/api/v1/auth/register',json={'owner_email':str(uuid.uuid4())+'@example.com','owner_password':'synthetic-password-123456','owner_name':'合成验收用户','company_name':'合成验收原始企业','agreed_terms_version':'2026-10-29'})
assert a.status_code==201
h={'Authorization':'Bearer '+a.json()['access_token']}
company=c.get('/api/v1/companies',headers=h).json()[0]
order=c.post('/api/v1/orders',headers=h,json={'product_code':'POLICY_REPORT','resource_id':company['id']})
assert order.status_code==201
with SessionLocal() as db:
 o=db.get(Order,uuid.UUID(order.json()['id']));p=db.scalar(select(Product).where(Product.code=='POLICY_REPORT'))
 # Contract-only entitlement injection, not a payment simulation or success claim.
 db.add(Entitlement(tenant_id=o.tenant_id,order_id=o.id,product_id=p.id,resource_type='report',resource_id=uuid.UUID(company['id']),status='active'))
 t=Task(tenant_id=o.tenant_id,company_id=uuid.UUID(company['id']),task_type='policy_scan',title='合成验收固定版本',status='completed')
 db.add(t);db.flush()
 d=Deliverable(tenant_id=o.tenant_id,task_id=t.id,company_id=t.company_id,deliverable_type='report',title='合成已验收报告',version=1,status='accepted',content_json={'company_name':'合成验收原始企业','fixed_version':1})
 db.add(d);db.commit();tid=t.id;did=d.id
empty=c.get('/api/v1/reports/'+company['id']+'/download',headers=h)
first=c.get('/api/v1/tasks/'+str(tid)+'/download',headers=h)
assert first.status_code==200
with SessionLocal() as db:
 row=db.get(Company,uuid.UUID(company['id']));row.name='合成验收后续修改企业';db.commit()
second=c.get('/api/v1/tasks/'+str(tid)+'/download',headers=h)
assert second.status_code==200
# Use trusted self-generated PDFs only. Never exploit parser vulnerabilities.
import fitz
before=''.join(p.get_text() for p in fitz.open(stream=first.content,filetype='pdf'))
after=''.join(p.get_text() for p in fitz.open(stream=second.content,filetype='pdf'))
with SessionLocal() as db:
 d=db.get(Deliverable,did);unchanged=d.version==1 and d.content_json['company_name']=='合成验收原始企业'
result={'synthetic_only':True,'real_payments':False,'empty_company_order_status':order.status_code,'active_entitlement_empty_report_download_status':empty.status_code,'immutable_deliverable_version_unchanged':unchanged,'first_pdf_old_company': '合成验收原始企业' in before,'second_pdf_new_company':'合成验收后续修改企业' in after,'pdf_hash_changed':hashlib.sha256(first.content).hexdigest()!=hashlib.sha256(second.content).hexdigest()}
print('AUDIT_PROBE_RESULT='+json.dumps(result,ensure_ascii=False))

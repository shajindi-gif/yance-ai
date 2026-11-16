import json,urllib.request,time,subprocess,uuid
from pathlib import Path
r=Path('/opt/yance/releases/commercial-20261108-01')
for _ in range(50):
 try:
  with urllib.request.urlopen('http://127.0.0.1:18008/health',timeout=3) as f: assert json.load(f)['status']=='ok'
  break
 except Exception:time.sleep(1)
else:raise RuntimeError('isolated API unavailable')
seed='''
import hashlib
from app.core.db import SessionLocal
from app.models.models import Policy,PolicyVersion,PolicyChunk
with SessionLocal() as db:
 text='合成发布验收政策：仅供隔离验证，支持研发证据核对。'
 p=Policy(title='合成发布验收政策',tenant_id=None,status='collected',content=text,source_url='https://example.invalid/release-check',province='上海市',jurisdiction='上海市',level='municipal')
 db.add(p);db.flush()
 v=PolicyVersion(policy_id=p.id,version=1,title=p.title,content=text,content_sha256=hashlib.sha256(text.encode()).hexdigest(),source_url=p.source_url)
 db.add(v);db.flush()
 db.add(PolicyChunk(policy_id=p.id,policy_version_id=v.id,chunk_index=0,content=text,char_start=0,char_end=len(text),content_sha256=hashlib.sha256(text.encode()).hexdigest()))
 db.commit()
'''
subprocess.run(['docker','exec','-i','yance-release-api-1108','python','-'],input=seed.encode(),check=True)
payload={'company_name':'Synthetic Release Verification','owner_email':'release-'+uuid.uuid4().hex+'@example.com','owner_name':'Synthetic Owner','owner_password':'synthetic-release-test-password-123','agreed_terms_version':'test-terms'}
request=urllib.request.Request('http://127.0.0.1:18008/api/v1/auth/register',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=20) as f:token=json.load(f)['access_token']
def get(path):
 req=urllib.request.Request('http://127.0.0.1:18008'+path,headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(req,timeout=15) as f:return json.load(f)
hits=get('/api/v1/policies/evidence-search?q='+urllib.parse.quote('合成发布验收'))['hits'];assert hits
h=hits[0];v=get('/api/v1/policies/'+h['policy_id']+'/versions/'+h['version_id']);assert '合成发布验收' in v['content']
ver=get('/api/v1/system/version');assert ver['database_revisions']==['20261106_0038']
assert get('/api/v1/auth/config')['email_login_enabled'] is False
fixture=r/'candidate-fixture.json';fixture.write_text(json.dumps({'token':token}));fixture.chmod(0o600)
subprocess.run(['chown','ubuntu:ubuntu',str(fixture)],check=True)
print('PG16_SYNTHETIC_REGISTRATION_EVIDENCE_VERSION_READ_PASSED')

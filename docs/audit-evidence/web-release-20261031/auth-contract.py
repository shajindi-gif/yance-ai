"""Synthetic isolated registration check; no real SMS, mail or production rows."""
import os
assert os.environ['APP_ENV']=='test' and 'web_auth_test' in os.environ['DATABASE_URL']
from fastapi.testclient import TestClient
from app.api.routes import sms_auth
from app.core.config import settings
from app.main import app
settings.sms_enabled=True
sms_auth.is_sms_configured=lambda: True
sms_auth.secrets.randbelow=lambda n: 123456
sms_auth.send_sms=lambda *args: None
with TestClient(app) as c:
 for number,version in [('19900001131','2026-10-29'),('19900001132','2026-10-30')]:
  assert c.post('/api/v1/auth/sms/send',json={'phone':number}).status_code==202
  r=c.post('/api/v1/auth/sms/verify',json={'phone':number,'code':'123456','owner_name':'合成验收','company_name':'合成隔离企业','agreed_terms_version':version})
  assert r.status_code==200, r.status_code
  me=c.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+r.json()['access_token']})
  assert me.status_code==200 and me.json()['email'] is None
print('BOTH_CONSENT_VERSIONS_SYNTHETIC_REGISTRATION_PASSED_NO_MESSAGES_SENT')

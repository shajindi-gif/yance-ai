"""Local browser harness: real API/DB, synthetic SMS supplier only; never deploy."""

import os

from sqlalchemy.engine import make_url

assert os.environ.get("APP_ENV") == "test"
url = make_url(os.environ["DATABASE_URL"])
assert url.host in {"127.0.0.1", "localhost"}
assert url.database.endswith("_test") and os.environ.get("YANCE_TEST_DATABASE_ACK") == url.database

import uvicorn  # noqa: E402

from app.api.routes import sms_auth  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

settings.sms_enabled = True
settings.tencent_sms_secret_id = "synthetic-not-a-credential"
settings.tencent_sms_secret_key = "synthetic-not-a-credential"
settings.tencent_sms_app_id = "synthetic"
settings.tencent_sms_sign_name = "synthetic"
settings.tencent_sms_template_id = "synthetic"
sms_auth.secrets.randbelow = lambda n: 123456
sms_auth.send_sms = lambda phone, code: None
uvicorn.run(app, host="127.0.0.1", port=8039, access_log=False)

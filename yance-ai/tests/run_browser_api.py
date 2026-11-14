"""Local E2E API with contract-only SMS, never loaded by production entrypoints."""

import argparse
import os
import secrets
from types import SimpleNamespace

from sqlalchemy.engine import make_url

url = make_url(os.environ.get("DATABASE_URL", ""))
if not (
    os.environ.get("APP_ENV") == "test"
    and url.host in {"localhost", "127.0.0.1"}
    and url.database
    and url.database.endswith("_test")
    and "prod" not in url.database
    and os.environ.get("YANCE_TEST_DATABASE_ACK") == url.database
):
    raise RuntimeError("Explicit loopback isolated test database is required")

from app.api.routes import auth, sms_auth  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402

if settings.sms_enabled or settings.email_enabled:
    raise RuntimeError("Real messaging must be disabled before starting the contract API")
auth.is_sms_configured = lambda: True
sms_auth.is_sms_configured = lambda: True
sms_auth.send_sms = lambda phone, code: None
sms_auth.secrets = SimpleNamespace(randbelow=lambda bound: 123456,
                                  compare_digest=secrets.compare_digest,
                                  token_urlsafe=secrets.token_urlsafe)

if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8011)
    uvicorn.run(app, host="127.0.0.1", port=parser.parse_args().port,
                proxy_headers=True, forwarded_allow_ips="127.0.0.1")

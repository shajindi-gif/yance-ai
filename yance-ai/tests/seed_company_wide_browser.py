"""Guarded synthetic project + feedback accounts for real browser checks."""

import json
import os
import sys
import uuid
from pathlib import Path

from seed_frontend_redesign import main as seed_workspace
from sqlalchemy.engine import make_url


def complete_feedback_fixture(output: Path):
    raw_url = os.environ.get("DATABASE_URL", "")
    url = make_url(raw_url)
    if (
        os.environ.get("APP_ENV") != "test"
        or url.host not in {"localhost", "127.0.0.1"}
        or not url.database
        or "test" not in url.database
        or "prod" in url.database
        or os.environ.get("YANCE_TEST_DATABASE_ACK") != url.database
    ):
        raise RuntimeError("Explicit local test database required")
    if output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        raise RuntimeError("Credentials must stay outside the repository")
    from fastapi.testclient import TestClient
    from test_funding_os import _register

    from app.core.db import SessionLocal
    from app.main import app
    from app.models.models import User

    data = json.loads(output.read_text())
    with TestClient(app, client=("127.0.0.2", 50321)) as client:
        if "feedback_admin_token" not in data:
            headers, me = _register(client, "feedback-admin-" + uuid.uuid4().hex)
            with SessionLocal() as db:
                db.get(User, uuid.UUID(me["id"])).is_platform_admin = True
                db.commit()
            data["feedback_admin_token"] = headers["Authorization"].removeprefix("Bearer ")
        if "feedback_user_email" not in data:
            _, me = _register(client, "feedback-user-" + uuid.uuid4().hex)
            data["feedback_user_email"] = me["email"]
            data["feedback_user_password"] = "integration-password-123"
    output.write_text(json.dumps(data))
    output.chmod(0o600)
    print("Private synthetic feedback fixture ready")


def main():
    seed_workspace()  # Shared explicit DB ACK and private output-path guards.
    complete_feedback_fixture(Path(sys.argv[1]).resolve())


if __name__ == "__main__":
    main()

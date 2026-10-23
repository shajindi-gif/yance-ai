"""The UI role must match live membership authorization, never JWT/account role."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select
from test_funding_os import _register

from app.core.db import SessionLocal
from app.main import app
from app.models.models import Membership, User


def test_me_reports_current_membership_without_mutating_account_role():
    with TestClient(app) as client:
        headers, me = _register(client, uuid.uuid4().hex)
        with SessionLocal() as db:
            membership = db.scalar(
                select(Membership).where(Membership.user_id == uuid.UUID(me["id"]))
            )
            membership.role = "viewer"
            db.commit()
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200 and response.json()["role"] == "viewer"
        with SessionLocal() as db:
            assert db.get(User, uuid.UUID(me["id"])).role == "owner"

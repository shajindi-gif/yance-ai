import uuid

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_and_jwt_roundtrip():
    password = "a-strong-test-password"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    user_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(user_id=user_id, tenant_id=tenant_id, role="owner")
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)

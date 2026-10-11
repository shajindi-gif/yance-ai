"""WeChat Pay APIv3 crypto correctness (offline, test keypair; no live gateway)."""

import base64
import json

import pytest
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from app.core.config import settings
from app.services.payments import wechat as wx


@pytest.fixture
def wechat_test_keys(monkeypatch):
    key = RSA.generate(2048)
    priv_pem = key.export_key(format="PEM", pkcs=8).decode()
    pub_pem = key.publickey().export_key().decode()
    # Store single-line base64 like production env (no PEM headers) to exercise
    # the loader's wrapping path.
    priv_b64 = "".join(priv_pem.strip().splitlines()[1:-1])
    pub_b64 = "".join(pub_pem.strip().splitlines()[1:-1])
    monkeypatch.setattr(settings, "wxpay_mode", "direct")
    monkeypatch.setattr(settings, "wxpay_mch_id", "1900000001")
    monkeypatch.setattr(settings, "wxpay_app_id", "wxtestappid")
    monkeypatch.setattr(settings, "wxpay_serial_no", "TESTSERIAL")
    monkeypatch.setattr(settings, "wxpay_apiv3_key", "0123456789abcdef0123456789abcdef")
    monkeypatch.setattr(settings, "wxpay_private_key", priv_b64)
    monkeypatch.setattr(settings, "wxpay_pubkey", pub_b64)
    monkeypatch.setattr(settings, "wxpay_pubkey_id", "PUB_KEY_ID_TEST")
    return key


def test_sign_and_verify_are_symmetric(wechat_test_keys):
    message = "POST\n/v3/pay/transactions/native\n1700000000\nNONCE\n{}\n"
    signature = wx._sign(message)
    assert wx._verify_with_key(message, signature) is True
    assert wx._verify_with_key("tampered message", signature) is False


def test_notify_signature_verification_matches_scheme(wechat_test_keys):
    timestamp, nonce, body = "1700000000", "ABC123", '{"id":"evt"}'
    message = f"{timestamp}\n{nonce}\n{body}\n"
    signer = PKCS1_v1_5.new(wechat_test_keys)
    signature = base64.b64encode(signer.sign(SHA256.new(message.encode()))).decode()
    assert (
        wx.verify_notify_signature(timestamp, nonce, body, signature, "PUB_KEY_ID_TEST")
        is True
    )
    # Wrong serial (not our configured PUB_KEY_ID) must reject.
    assert (
        wx.verify_notify_signature(timestamp, nonce, body, signature, "OTHER_SERIAL")
        is False
    )


def test_resource_decrypt_round_trip(wechat_test_keys):
    plaintext = {"out_trade_no": "Y123", "trade_state": "SUCCESS", "transaction_id": "T999"}
    key = settings.wxpay_apiv3_key.encode()
    nonce = b"unique_nonce"  # 12 bytes
    associated = b"transaction"
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(associated)
    ct, tag = cipher.encrypt_and_digest(json.dumps(plaintext).encode())
    ciphertext_b64 = base64.b64encode(ct + tag).decode()  # WeChat appends tag
    decrypted = wx.decrypt_resource(
        {
            "ciphertext": ciphertext_b64,
            "nonce": nonce.decode(),
            "associated_data": associated.decode(),
        }
    )
    assert decrypted == plaintext


def test_is_wechat_configured_rejects_placeholders(monkeypatch):
    monkeypatch.setattr(settings, "wxpay_mch_id", "REPLACE_WITH_MCH_ID")
    monkeypatch.setattr(settings, "wxpay_private_key", "x")
    monkeypatch.setattr(settings, "wxpay_serial_no", "x")
    monkeypatch.setattr(settings, "wxpay_apiv3_key", "x")
    assert wx.is_wechat_configured() is False

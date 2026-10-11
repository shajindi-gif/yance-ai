"""WeChat Pay APIv3 (direct merchant) — Native QR, query, notify verify/decrypt.

Pure pycryptodome implementation (already a project dependency; no new SDK).
Ported from the production-verified fengyuxueye wechat-pay.ts reference,
including the two non-obvious fixes: Accept-Language header (gateway 406) and
WeChat Pay public-key verification mode (new merchants have no platform certs).
"""

import base64
import json
import secrets
import time

import httpx
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5

from app.core.config import settings

# PKCS#8 (what the WeChat/Alipay key tools export) carries the rsaEncryption
# AlgorithmIdentifier marker; PKCS#1 does not. Length-independent, unlike a fixed
# "MIIEvQ" prefix (real keys also start "MIIEvg").
_PKCS8_MARKER = "ADANBgkqhkiG9w0BAQEF"


def _load_private_key() -> RSA.RsaKey:
    pem = settings.wxpay_private_key.replace("\\n", "\n").strip()
    if not pem.startswith("-----BEGIN"):
        # Production stores the merchant key as single-line base64 in env.
        if _PKCS8_MARKER in pem[:64]:
            pem = f"-----BEGIN PRIVATE KEY-----\n{pem}\n-----END PRIVATE KEY-----"
        else:
            pem = f"-----BEGIN RSA PRIVATE KEY-----\n{pem}\n-----END RSA PRIVATE KEY-----"
    return RSA.import_key(pem)


def _load_public_key() -> RSA.RsaKey:
    raw = settings.wxpay_pubkey.replace("\\n", "\n").strip()
    if not raw.startswith("-----"):
        raw = f"-----BEGIN PUBLIC KEY-----\n{raw}\n-----END PUBLIC KEY-----"
    return RSA.import_key(raw)


def _is_placeholder(value: str) -> bool:
    upper = (value or "").upper()
    return any(m in upper for m in ("REPLACE_WITH", "CHANGEME", "YOUR_", "TODO"))


def is_wechat_configured() -> bool:
    return bool(
        settings.wxpay_mch_id
        and settings.wxpay_serial_no
        and settings.wxpay_private_key
        and settings.wxpay_apiv3_key
        and not _is_placeholder(settings.wxpay_mch_id)
        and not _is_placeholder(settings.wxpay_private_key)
    )


def _sign(message: str) -> str:
    key = _load_private_key()
    signer = PKCS1_v1_5.new(key)
    digest = SHA256.new(message.encode("utf-8"))
    return base64.b64encode(signer.sign(digest)).decode("utf-8")


def _authorization(method: str, url_path: str, body: str) -> str:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16).upper()
    message = f"{method}\n{url_path}\n{timestamp}\n{nonce}\n{body}\n"
    signature = _sign(message)
    if settings.wxpay_mode == "partner" and settings.wxpay_sp_mch_id:
        mchid = settings.wxpay_sp_mch_id
    else:
        mchid = settings.wxpay_mch_id
    return (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{mchid}",'
        f'nonce_str="{nonce}",timestamp="{timestamp}",'
        f'serial_no="{settings.wxpay_serial_no}",signature="{signature}"'
    )


def _headers(method: str, url_path: str, body: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        # WeChat gateway returns 406 for clients that omit a browser-like
        # Accept-Language (verified in the reference implementation).
        "Accept-Language": "zh-CN,zh;q=0.9",
        "User-Agent": "yance-ai/1.0",
        "Authorization": _authorization(method, url_path, body),
    }


def create_native_order(
    out_trade_no: str, total_fen: int, description: str, notify_url: str
) -> tuple[str | None, str | None]:
    """Create a Native order. Returns (code_url, error_code)."""
    if not is_wechat_configured():
        return None, "not_configured"
    partner = settings.wxpay_mode == "partner"
    url_path = "/v3/pay/partner/transactions/native" if partner else "/v3/pay/transactions/native"
    if partner:
        body = {
            "sp_appid": settings.wxpay_sp_app_id,
            "sp_mchid": settings.wxpay_sp_mch_id,
            "sub_mchid": settings.wxpay_sub_mch_id,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "amount": {"total": total_fen, "currency": "CNY"},
        }
    else:
        body = {
            "mchid": settings.wxpay_mch_id,
            "appid": settings.wxpay_app_id,
            "description": description,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "amount": {"total": total_fen, "currency": "CNY"},
        }
    payload = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    try:
        response = httpx.post(
            f"{settings.wxpay_gateway}{url_path}",
            content=payload.encode("utf-8"),
            headers=_headers("POST", url_path, payload),
            timeout=15,
        )
        data = response.json()
        if response.status_code == 200 and data.get("code_url"):
            return data["code_url"], None
        return None, str(data.get("code") or f"http_{response.status_code}")
    except (httpx.HTTPError, ValueError, KeyError):
        return None, "request_failed"


def query_order(out_trade_no: str) -> dict | None:
    """Active query (callback-loss compensation). Returns trade_state payload or None."""
    if not is_wechat_configured():
        return None
    url_path = f"/v3/pay/transactions/out-trade-no/{out_trade_no}?mchid={settings.wxpay_mch_id}"
    try:
        response = httpx.get(
            f"{settings.wxpay_gateway}{url_path}",
            headers=_headers("GET", url_path, ""),
            timeout=15,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        amount = data.get("amount") or {}
        return {
            "trade_state": data.get("trade_state"),
            "transaction_id": data.get("transaction_id"),
            "payer_total": amount.get("payer_total") or amount.get("total"),
        }
    except (httpx.HTTPError, ValueError, KeyError):
        return None


def _verify_with_key(message: str, signature_b64: str) -> bool:
    try:
        key = _load_public_key()
        verifier = PKCS1_v1_5.new(key)
        digest = SHA256.new(message.encode("utf-8"))
        # pycryptodome >= 3.15 returns True/False; older releases return None
        # on success and raise on failure. Accept both, never trust the call
        # alone — check the result.
        result = verifier.verify(digest, base64.b64decode(signature_b64))
        return result is not False
    except (ValueError, TypeError, UnicodeDecodeError):
        return False


def verify_notify_signature(
    timestamp: str, nonce: str, body: str, signature_b64: str, serial: str
) -> bool:
    """Verify callback signature using the WeChat Pay public key (PUB_KEY_ID mode)."""
    if not settings.wxpay_pubkey:
        return False
    # In public-key mode the callback serial is the configured PUB_KEY_ID.
    if settings.wxpay_pubkey_id and serial != settings.wxpay_pubkey_id:
        return False
    message = f"{timestamp}\n{nonce}\n{body}\n"
    return _verify_with_key(message, signature_b64)


def decrypt_resource(resource: dict) -> dict:
    """AES-256-GCM decrypt of the callback resource (APIv3 key).

    WeChat appends the 16-byte GCM tag to the ciphertext before base64.
    """
    ciphertext = base64.b64decode(resource["ciphertext"])
    data, tag = ciphertext[:-16], ciphertext[-16:]
    cipher = AES.new(
        settings.wxpay_apiv3_key.encode("utf-8"),
        AES.MODE_GCM,
        nonce=resource["nonce"].encode("utf-8"),
    )
    cipher.update((resource.get("associated_data") or "").encode("utf-8"))
    plaintext = cipher.decrypt_and_verify(data, tag)
    return json.loads(plaintext.decode("utf-8"))

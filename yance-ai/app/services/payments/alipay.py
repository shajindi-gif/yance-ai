"""Signed Alipay gateway requests with verification of the exact response bytes."""

import base64
import json
import re
from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from fastapi import HTTPException

from app.core.config import settings


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate gateway field")
        result[key] = value
    return result


def verify_response(raw: str, method: str) -> dict:
    key = method.replace(".", "_") + "_response"
    try:
        document = json.loads(raw, object_pairs_hook=_unique_object)
        match = re.search(r'"' + re.escape(key) + r'"\s*:\s*', raw)
        if match is None or key not in document:
            raise ValueError("Missing gateway response")
        value, end = json.JSONDecoder().raw_decode(raw, match.end())
        if value != document[key] or not isinstance(value, dict):
            raise ValueError("Ambiguous gateway response")
        content = raw[match.end() : end]
        public_key = settings.alipay_public_key.replace("\\n", "\n").strip()
        if not public_key.startswith("-----BEGIN"):
            public_key = "-----BEGIN PUBLIC KEY-----\n" + public_key + "\n-----END PUBLIC KEY-----"
        valid = PKCS1_v1_5.new(RSA.import_key(public_key)).verify(
            SHA256.new(content.encode("utf-8")),
            base64.b64decode(document["sign"], validate=True),
        )
        if not valid:
            raise ValueError("Invalid gateway signature")
        return value
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise HTTPException(502, "Alipay response verification failed") from exc


def call(method: str, business: dict, signer: Callable[[dict], str]) -> tuple[dict, bytes]:
    params = {
        "app_id": settings.alipay_app_id,
        "method": method,
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "biz_content": json.dumps(business, ensure_ascii=False, separators=(",", ":")),
    }
    params["sign"] = signer(params)
    gateway = (
        "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
        if settings.alipay_sandbox
        else settings.alipay_gateway
    )
    try:
        response = httpx.post(gateway, data=params, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Alipay gateway temporarily unavailable") from exc
    return verify_response(response.text, method), response.content

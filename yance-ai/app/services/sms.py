"""Tencent SendSms 2021-01-11. Fixed destination, no automatic retries or sensitive logs."""

import hashlib
import hmac
import json
import re
import time
from datetime import UTC, datetime

import httpx

from app.core.config import settings


class SmsDeliveryError(Exception):
    """Only an allowlisted provider error identifier may leave this adapter."""

    def __init__(self, reason: str, provider_code: str = ""):
        super().__init__(reason)
        self.provider_code = (
            provider_code if re.fullmatch(r"[A-Za-z0-9_.]{1,100}", provider_code) else "Unknown"
        )


def normalize_phone(value: str) -> str:
    value = value.strip()
    if value.startswith("+86"):
        value = value[3:]
    if not re.fullmatch(r"1[3-9][0-9]{9}", value):
        raise ValueError("请输入中国大陆11位手机号")
    return "+86" + value


def is_sms_configured() -> bool:
    return settings.sms_enabled and all(
        (
            settings.tencent_sms_secret_id,
            settings.tencent_sms_secret_key,
            settings.tencent_sms_app_id,
            settings.tencent_sms_sign_name,
            settings.tencent_sms_template_id,
        )
    )


def digest_code(phone: str, purpose: str, code: str) -> str:
    # A database-only disclosure must not permit brute-forcing six-digit codes.
    return hmac.new(
        settings.jwt_secret.encode(), f"sms:{phone}:{purpose}:{code}".encode(), hashlib.sha256
    ).hexdigest()


def send_sms(phone: str, code: str) -> None:
    if not is_sms_configured():
        raise SmsDeliveryError("sms unavailable")
    phone = normalize_phone(phone)
    if not re.fullmatch(r"[0-9]{6}", code):
        raise ValueError("invalid code")
    payload = json.dumps(
        {
            "PhoneNumberSet": [phone],
            "SmsSdkAppId": settings.tencent_sms_app_id,
            "SignName": settings.tencent_sms_sign_name,
            "TemplateId": settings.tencent_sms_template_id,
            "TemplateParamSet": [code, "5"],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    timestamp = int(time.time())
    date = datetime.fromtimestamp(timestamp, UTC).strftime("%Y-%m-%d")
    canonical = (
        "POST\n/\n\ncontent-type:application/json; charset=utf-8\nhost:sms.tencentcloudapi.com\n\ncontent-type;host\n"
        + hashlib.sha256(payload.encode()).hexdigest()
    )
    scope = f"{date}/sms/tc3_request"
    sign_text = (
        f"TC3-HMAC-SHA256\n{timestamp}\n{scope}\n" + hashlib.sha256(canonical.encode()).hexdigest()
    )

    def sign(key, message):
        return hmac.new(key, message.encode(), hashlib.sha256).digest()

    key = sign(
        sign(sign(("TC3" + settings.tencent_sms_secret_key).encode(), date), "sms"), "tc3_request"
    )
    signature = hmac.new(key, sign_text.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-TC-Action": "SendSms",
        "X-TC-Version": "2021-01-11",
        "X-TC-Region": settings.tencent_sms_region,
        "X-TC-Timestamp": str(timestamp),
        "Authorization": f"TC3-HMAC-SHA256 Credential={settings.tencent_sms_secret_id}/{scope}, SignedHeaders=content-type;host, Signature={signature}",
    }
    try:
        with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
            response = client.post(
                "https://sms.tencentcloudapi.com", headers=headers, content=payload.encode()
            )
            response.raise_for_status()
            result = response.json()["Response"]
            if not isinstance(result, dict):
                raise SmsDeliveryError("sms rejected")
            statuses = result.get("SendStatusSet", [])
            if (
                result.get("Error")
                or not isinstance(statuses, list)
                or len(statuses) != 1
                or not isinstance(statuses[0], dict)
                or statuses[0].get("Code") != "Ok"
                or statuses[0].get("PhoneNumber") != phone
            ):
                error = result.get("Error") or {}
                code = error.get("Code", "Unknown") if isinstance(error, dict) else "Unknown"
                if isinstance(statuses, list) and statuses and isinstance(statuses[0], dict):
                    code = statuses[0].get("Code", code)
                raise SmsDeliveryError("sms rejected", code if isinstance(code, str) else "Unknown")
    except httpx.HTTPStatusError as exc:
        raise SmsDeliveryError("sms HTTP failure", f"HTTP_{exc.response.status_code}") from None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        raise SmsDeliveryError("sms delivery uncertain") from None

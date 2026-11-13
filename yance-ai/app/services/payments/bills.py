"""Bounded provider bill download and strict CSV adapters. Never extract an archive."""

import csv
import hashlib
import hmac
import io
import zipfile
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from urllib.parse import urlencode, urlparse

import httpx

from app.core.config import settings
from app.services.payments import alipay, wechat

MAX_BYTES = 50 * 1024 * 1024


@dataclass(frozen=True)
class BillRecord:
    reference: str
    transaction: str
    kind: str
    amount: Decimal
    refund_reference: str = ""


def _download(url: str, provider: str) -> bytes:
    parsed = urlparse(url)
    host = parsed.hostname or ""
    allowed = (
        host.endswith(".alipay.com") if provider == "alipay" else host == "api.mch.weixin.qq.com"
    )
    if not allowed or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("Untrusted bill URL")
    if parsed.scheme == "http" and provider == "alipay":
        url = "https" + url[4:]
    elif parsed.scheme != "https":
        raise ValueError("Bill transport requires HTTPS")
    headers = {}
    if provider == "wechat":
        path = parsed.path + ("?" + parsed.query if parsed.query else "")
        headers = wechat._headers("GET", path, "")
    chunks = []
    size = 0
    with httpx.stream("GET", url, headers=headers, timeout=30, follow_redirects=False) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError("Bill exceeds size limit")
            chunks.append(chunk)
    return b"".join(chunks)


def download_bill(provider: str, day: date) -> bytes:
    from app.api.routes.payments import _alipay_available, _build_alipay_sign

    if provider == "alipay":
        if not _alipay_available():
            raise ValueError("Provider not configured")
        result, _ = alipay.call(
            "alipay.data.dataservice.bill.downloadurl.query",
            {"bill_type": "trade", "bill_date": day.isoformat()},
            _build_alipay_sign,
        )
        if result.get("code") != "10000":
            raise ValueError("Bill not ready or permission unavailable")
        return _download(result.get("bill_download_url", ""), "alipay")
    if not wechat.is_wechat_configured():
        raise ValueError("Provider not configured")
    path = "/v3/bill/tradebill?" + urlencode({"bill_date": day.isoformat(), "bill_type": "ALL"})
    response = httpx.get(
        settings.wxpay_gateway + path, headers=wechat._headers("GET", path, ""), timeout=15
    )
    response.raise_for_status()
    if not wechat.verify_notify_signature(
        response.headers.get("Wechatpay-Timestamp", ""),
        response.headers.get("Wechatpay-Nonce", ""),
        response.text,
        response.headers.get("Wechatpay-Signature", ""),
        response.headers.get("Wechatpay-Serial", ""),
    ):
        raise ValueError("Bill response signature failed")
    result = response.json()
    content = _download(result.get("download_url", ""), "wechat")
    algorithm = {"SHA1": "sha1", "SHA256": "sha256"}.get(result.get("hash_type"))
    if not algorithm or not hmac.compare_digest(
        hashlib.new(algorithm, content).hexdigest(), result.get("hash_value", "").lower()
    ):
        raise ValueError("Bill hash mismatch")
    return content


def _texts(raw: bytes) -> list[str]:
    contents = [raw]
    if raw.startswith(b"PK"):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            files = [
                item
                for item in archive.infolist()
                if item.filename.lower().endswith(".csv") and not item.is_dir()
            ]
            if len(files) > 10 or sum(item.file_size for item in files) > MAX_BYTES:
                raise ValueError("Unsafe bill archive")
            contents = [archive.read(item) for item in files if "汇总" not in item.filename]
    result = []
    for content in contents:
        try:
            result.append(content.decode("utf-8-sig"))
        except UnicodeDecodeError:
            result.append(content.decode("gb18030"))
    return result


def parse_bill(provider: str, raw: bytes) -> list[BillRecord]:
    records = []
    recognized = False
    for text in _texts(raw):
        header = None
        for line in csv.reader(io.StringIO(text)):
            row = [cell.strip().lstrip("`").strip() for cell in line]
            if "商户订单号" in row:
                header = row
                recognized = True
                continue
            if not row or not any(row) or row[0].startswith("#"):
                continue
            if row[0].startswith(("总交易", "总计", "合计")):
                break
            if not header:
                continue
            if len(row) != len(header):
                raise ValueError("Malformed bill row")
            fields = dict(zip(header, row, strict=True))
            reference = fields.get("商户订单号", "")
            if not reference or len(reference) > 128:
                raise ValueError("Invalid merchant reference")
            if fields.get("货币种类", "CNY") != "CNY":
                raise ValueError("Unsupported bill currency")
            if provider == "wechat":
                status = fields.get("交易状态")
                if status not in {"SUCCESS", "REFUND"}:
                    raise ValueError("Unsupported WeChat bill state")
                kind = "refund" if status == "REFUND" else "paid"
                value = fields.get("申请退款金额") if kind == "refund" else fields.get("订单金额")
                transaction = (
                    fields.get("微信退款单号") if kind == "refund" else fields.get("微信订单号")
                )
                refund_reference = fields.get("商户退款单号", "")
            else:
                status = fields.get("业务类型", "")
                if status in {"交易收费", "手续费"}:
                    continue
                if status not in {"交易", "交易退款", "退款"}:
                    raise ValueError("Unsupported Alipay bill state")
                kind = "paid" if status == "交易" else "refund"
                value = fields.get("收入（+元）") if kind == "paid" else fields.get("支出（-元）")
                transaction = fields.get("支付宝交易号")
                refund_reference = fields.get("商户业务流水号", "") if kind == "refund" else ""
            if value is None or not transaction:
                raise ValueError("Unsupported bill columns")
            amount = Decimal(value)
            if not amount.is_finite() or amount < 0 or amount != amount.quantize(Decimal(".01")):
                raise ValueError("Invalid bill amount")
            records.append(BillRecord(reference, transaction, kind, amount, refund_reference))
    if not recognized:
        raise ValueError("Unrecognized bill format")
    return records

import json
import time
import uuid
from urllib.parse import urlencode

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.config import settings
from app.core.db import get_db
from app.models.models import Order, Payment, UserRole

router = APIRouter(prefix="/payments", tags=["payments"])


# ── Stripe (legacy, kept for reference) ──────────────────────────────
def _stripe_checkout_available() -> bool:
    return bool(settings.stripe_secret_key and settings.stripe_webhook_secret)


# ── Alipay helpers ────────────────────────────────────────────────────
def _alipay_available() -> bool:
    return bool(settings.alipay_app_id and settings.alipay_private_key)

def _alipay_gateway_url() -> str:
    if settings.alipay_sandbox:
        return "https://openapi-sandbox.dl.alipaydev.com/gateway.do"
    return settings.alipay_gateway

def _build_alipay_sign(params: dict) -> str:
    """Build RSA-SHA256 sign for Alipay request."""
    # Sort keys alphabetically, remove sign/sign_type, concat with &
    sorted_items = sorted(
        (k, v) for k, v in params.items()
        if v != "" and v is not None and k not in ("sign", "sign_type")
    )
    raw_string = "&".join(f"{k}={v}" for k, v in sorted_items)
    private_key = settings.alipay_private_key
    # Restore newlines if stored as single-line
    if "\\n" in private_key:
        private_key = private_key.replace("\\n", "\n")
    if not private_key.startswith("-----BEGIN"):
        private_key = f"-----BEGIN RSA PRIVATE KEY-----\n{private_key}\n-----END RSA PRIVATE KEY-----"
    rsa_key = RSA.import_key(private_key)
    signer = PKCS1_v1_5.new(rsa_key)
    h = SHA256.new(raw_string.encode("utf-8"))
    signature = signer.sign(h)
    from base64 import b64encode
    return b64encode(signature).decode("utf-8")

def _verify_alipay_sign(params: dict, signature: str) -> bool:
    """Verify Alipay async notify signature."""
    sorted_items = sorted(
        (k, v) for k, v in params.items()
        if v != "" and v is not None and k not in ("sign", "sign_type")
    )
    raw_string = "&".join(f"{k}={v}" for k, v in sorted_items)
    public_key = settings.alipay_public_key
    if "\\n" in public_key:
        public_key = public_key.replace("\\n", "\n")
    if not public_key.startswith("-----BEGIN"):
        public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"
    rsa_key = RSA.import_key(public_key)
    verifier = PKCS1_v1_5.new(rsa_key)
    h = SHA256.new(raw_string.encode("utf-8"))
    from base64 import b64decode
    return verifier.verify(h, b64decode(signature))


@router.post("/alipay/page-pay")
def alipay_page_pay(
    order_id: uuid.UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> dict:
    """Create Alipay PC website payment URL (电脑网站支付)."""
    if not _alipay_available():
        raise HTTPException(status_code=503, detail="Alipay not configured")

    order = db.scalar(
        select(Order).where(
            Order.id == order_id, Order.tenant_id == principal.tenant_id
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "paid":
        raise HTTPException(status_code=400, detail="Order already paid")

    out_trade_no = f"{order.order_no}_{int(time.time())}"
    subject = f"yance.ai - {order.product_code}"
    total_amount = f"{order.amount:.2f}"

    biz_content = {
        "out_trade_no": out_trade_no,
        "product_code": "FAST_INSTANT_TRADE_PAY",
        "total_amount": total_amount,
        "subject": subject,
        "body": subject,
    }

    params = {
        "app_id": settings.alipay_app_id,
        "method": "alipay.trade.page.pay",
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "version": "1.0",
        "notify_url": settings.alipay_notify_url,
        "return_url": settings.alipay_return_url,
        "biz_content": json.dumps(biz_content, ensure_ascii=False),
    }

    params["sign"] = _build_alipay_sign(params)

    # Store payment record
    payment = Payment(
        tenant_id=principal.tenant_id,
        order_id=order.id,
        provider="alipay",
        provider_trade_no=out_trade_no,
        amount=order.amount,
        currency=order.currency,
        status="created",
    )
    db.add(payment)
    db.commit()

    gateway = _alipay_gateway_url()
    payment_url = f"{gateway}?{urlencode(params)}"
    return {"url": payment_url, "out_trade_no": out_trade_no}


@router.post("/alipay/notify")
async def alipay_notify(request: Request, db: Session = Depends(get_db)) -> str:
    """Alipay async payment notification (POST). Must return 'success' or 'fail'."""
    body = await request.body()
    form_data = dict(await request.form()) if body else {}

    sign = form_data.pop("sign", "")
    sign_type = form_data.pop("sign_type", "RSA2")

    if not _verify_alipay_sign(form_data, sign):
        return "fail"

    trade_status = form_data.get("trade_status", "")
    out_trade_no = form_data.get("out_trade_no", "")
    trade_no = form_data.get("trade_no", "")
    buyer_logon_id = form_data.get("buyer_logon_id", "")
    buyer_id = form_data.get("buyer_id", "")

    if not out_trade_no:
        return "fail"

    payment = db.scalar(
        select(Payment).where(Payment.provider_trade_no == out_trade_no)
    )
    if not payment:
        return "fail"

    payment.alipay_trade_no = trade_no
    payment.alipay_buyer_logon_id = buyer_logon_id
    payment.alipay_buyer_user_id = buyer_id
    payment.raw_response = {**form_data, "sign": sign}

    if trade_status == "TRADE_SUCCESS":
        payment.status = "completed"
        order = db.scalar(select(Order).where(Order.id == payment.order_id))
        if order:
            order.status = "paid"
    elif trade_status == "TRADE_CLOSED":
        payment.status = "expired"

    db.commit()
    return "success"


@router.post("/alipay/return")
async def alipay_return(request: Request, db: Session = Depends(get_db)) -> dict:
    """Alipay sync return (GET redirect). Verify and return order status."""
    params = dict(request.query_params)
    sign = params.pop("sign", "")
    sign_type = params.pop("sign_type", "RSA2")

    if not _verify_alipay_sign(params, sign):
        raise HTTPException(status_code=400, detail="Invalid signature")

    out_trade_no = params.get("out_trade_no", "")
    trade_no = params.get("trade_no", "")

    payment = db.scalar(
        select(Payment).where(Payment.provider_trade_no == out_trade_no)
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "out_trade_no": out_trade_no,
        "trade_no": trade_no,
        "status": payment.status,
        "order_id": str(payment.order_id),
    }


@router.post("/checkout")
def create_checkout_session(
    order_id: uuid.UUID,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> dict:
    """Unified checkout: auto-selects Alipay if configured, falls back to Stripe."""
    if _alipay_available():
        return alipay_page_pay(order_id, principal, db)

    # Fallback to Stripe
    if not _stripe_checkout_available():
        raise HTTPException(status_code=503, detail="No payment provider configured")

    import stripe
    stripe.api_key = settings.stripe_secret_key

    order = db.scalar(
        select(Order).where(
            Order.id == order_id, Order.tenant_id == principal.tenant_id
        )
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    unit_amount = int(order.amount * 100)
    session = stripe.checkout.Session.create(
        mode="payment",
        currency=order.currency.lower(),
        line_items=[{
            "price_data": {
                "currency": order.currency.lower(),
                "product_data": {"name": order.product_code},
                "unit_amount": unit_amount,
            },
            "quantity": 1,
        }],
        success_url="https://yance.ai/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://yance.ai/cancel",
        metadata={"order_id": str(order.id), "tenant_id": str(principal.tenant_id)},
    )

    payment = Payment(
        tenant_id=principal.tenant_id,
        order_id=order.id,
        provider="stripe",
        provider_trade_no=session.id,
        amount=order.amount,
        currency=order.currency,
        stripe_session_id=session.id,
        status="created",
    )
    db.add(payment)
    db.commit()

    return {"url": session.url, "session_id": session.id}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    """Stripe webhook handler (legacy)."""
    import stripe
    stripe.api_key = settings.stripe_secret_key

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=503, detail="Stripe webhook not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        payment = db.scalar(
            select(Payment).where(Payment.stripe_session_id == session["id"])
        )
        if payment:
            payment.status = "completed"
            payment.raw_response = event["data"]["object"]
            order = db.scalar(select(Order).where(Order.id == payment.order_id))
            if order:
                order.status = "paid"
            db.commit()

    return {"received": True}


# ─── 银行对公转账 ─────────────────────────────────────────────

bank_router = APIRouter(prefix="/bank", tags=["bank-transfer"])


@bank_router.get("/info")
def get_bank_info():
    """返回公司对公账户信息，供客户端展示银行转账方式。"""
    return {
        "company_name": settings.company_name,
        "tax_id": settings.company_tax_id,
        "bank_name": settings.company_bank_name,
        "bank_account": settings.company_bank_account,
        "bank_card": settings.company_bank_card,
    }


class BankReceiptUpload(BaseModel):
    receipt_url: str


@bank_router.post("/orders/{order_id}/receipt")
def upload_bank_receipt(
    order_id: str,
    body: BankReceiptUpload,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    """客户提交银行转账凭证，创建待核实的 Payment 记录。"""
    order = db.scalar(select(Order).where(Order.id == order_id, Order.user_id == principal.user_id))
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.status not in ("created",):
        raise HTTPException(status_code=400, detail="订单状态不允许提交凭证")

    payment = db.scalar(
        select(Payment).where(Payment.order_id == order_id, Payment.method == "bank_transfer")
    )
    if payment:
        payment.bank_receipt_url = body.receipt_url
        payment.status = "submitted"
    else:
        payment = Payment(
            order_id=order_id,
            method="bank_transfer",
            amount=order.total_amount * 100 if order.total_amount else 0,
            currency=order.currency or "cny",
            bank_receipt_url=body.receipt_url,
            status="submitted",
        )
        db.add(payment)
    db.commit()
    db.refresh(payment)
    return {"payment_id": payment.id, "status": payment.status}


@bank_router.post("/payments/{payment_id}/verify")
def verify_bank_transfer(
    payment_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
):
    """管理端核实银行转账到账，将订单标记为已支付。"""
    payment = db.scalar(
        select(Payment).where(Payment.id == payment_id, Payment.method == "bank_transfer")
    )
    if not payment:
        raise HTTPException(status_code=404, detail="凭证不存在")
    if payment.status == "verified":
        raise HTTPException(status_code=400, detail="该凭证已核实")

    payment.status = "verified"
    payment.bank_verified_at = datetime.now(timezone.utc)
    order = db.scalar(select(Order).where(Order.id == payment.order_id))
    if order:
        order.status = "paid"
    db.commit()
    return {"payment_id": payment.id, "status": "verified", "order_status": order.status if order else None}

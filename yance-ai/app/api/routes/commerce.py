import secrets
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.config import settings
from app.core.db import get_db
from app.models.models import Company, Invoice, Opportunity, Order, Payment, Product, User, UserRole
from app.schemas.schemas import (
    CommerceOut,
    InvoiceCreate,
    InvoiceOut,
    OrderCreate,
    OrderOut,
    PaymentCreate,
)
from app.services.analytics.events import record_event
from app.services.commerce.availability import purchase_status
from app.services.invoice.generator import generate_invoice_pdf

router = APIRouter(tags=["orders", "payments", "invoices"])


def _generate_invoice_no() -> str:
    """Generate invoice number: YYMMDD + 6 random digits"""
    date_part = time.strftime("%y%m%d")
    rand_part = secrets.token_hex(3).upper()  # 6 hex chars
    return f"{date_part}{rand_part}"


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    principal: Principal = Depends(get_principal), db: Session = Depends(get_db)
) -> list[Order]:
    return list(db.scalars(select(Order).where(Order.tenant_id == principal.tenant_id)).all())


@router.post("/orders", response_model=CommerceOut, status_code=201)
def create_order(
    payload: OrderCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin, UserRole.member)),
    db: Session = Depends(get_db),
) -> Order:
    request_order_id = None
    if payload.client_request_id:
        # Stable, principal-scoped ID plus a row lock make retries atomic without
        # changing the schema or historical orders. UUID is never authorization.
        request_order_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"https://yance.ai/orders/v1/{principal.tenant_id}/{principal.user.id}/{payload.client_request_id}",
        )
        db.execute(select(User.id).where(User.id == principal.user.id).with_for_update())
        existing = db.scalar(
            select(Order).where(
                Order.id == request_order_id, Order.tenant_id == principal.tenant_id
            )
        )
        if existing:
            if (
                existing.product_code != payload.product_code
                or existing.resource_id != payload.resource_id
            ):
                raise HTTPException(
                    status_code=409, detail="该请求已关联其他订单内容，请返回订单核对"
                )
            return existing
    product = db.scalar(
        select(Product).where(Product.code == payload.product_code, Product.active.is_(True))
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    availability = purchase_status(product)
    if not availability["purchase_available"]:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "product_not_available_for_new_orders",
                "message": availability["purchase_unavailable_reason"],
            },
        )
    if not payload.resource_id:
        raise HTTPException(status_code=400, detail="A product resource is required")
    resource_model = Company if product.entitlement_type == "report" else Opportunity
    resource = db.scalar(
        select(resource_model).where(
            resource_model.id == payload.resource_id,
            resource_model.tenant_id == principal.tenant_id,
        )
    )
    if not resource:
        raise HTTPException(status_code=404, detail="Product resource not found")
    order = Order(
        **({"id": request_order_id} if request_order_id else {}),
        tenant_id=principal.tenant_id,
        order_no=f"Y{secrets.token_hex(8).upper()}",
        product_code=product.code,
        amount=product.promotional_price
        if product.promotional_price is not None
        else product.price,
        currency="CNY",
        resource_type=product.entitlement_type,
        resource_id=payload.resource_id,
        status="created",
    )
    db.add(order)
    db.flush()
    record_event(
        db,
        tenant_id=principal.tenant_id,
        user_id=principal.user.id,
        name="checkout_started",
        event_key=f"checkout_started:{order.id}",
        properties={"order_id": str(order.id), "product_code": order.product_code},
    )
    db.commit()
    db.refresh(order)
    return order


@router.post("/payments", response_model=CommerceOut, status_code=202)
def create_payment_skeleton(
    payload: PaymentCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> Payment:
    raise HTTPException(
        status_code=501,
        detail="Payments can only be created by a configured checkout provider",
    )


@router.post("/invoices", response_model=InvoiceOut, status_code=202)
def create_invoice(
    payload: InvoiceCreate,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> Invoice:
    """Create invoice (payment voucher) record for an order.

    Note: the generated PDF is a payment voucher for reconciliation,
    NOT a tax invoice. Formal tax invoices are issued via manual review.
    """
    order = db.scalar(
        select(Order).where(Order.id == payload.order_id, Order.tenant_id == principal.tenant_id).with_for_update()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "paid":
        raise HTTPException(status_code=400, detail="Order must be paid before invoicing")

    existing = db.scalar(select(Invoice).where(Invoice.order_id == order.id, Invoice.tenant_id == principal.tenant_id, Invoice.status != "rejected").order_by(Invoice.created_at.desc()))
    if existing:
        if (existing.title, existing.tax_number, existing.invoice_type) != (payload.title, payload.tax_number, payload.invoice_type or "vat_normal"):
            raise HTTPException(status_code=409, detail="该订单已有开票申请，请联系管理员核实后更正")
        return existing

    invoice_no = _generate_invoice_no()

    invoice = Invoice(
        tenant_id=principal.tenant_id,
        order_id=order.id,
        invoice_no=invoice_no,
        title=payload.title,
        tax_number=payload.tax_number,
        address_phone=payload.address_phone,
        bank_account=payload.bank_account,
        seller_name=settings.company_name,
        seller_tax_number=settings.company_tax_id,
        items_json=[
            {
                "name": order.product_code,
                "spec": "",
                "unit": "次",
                "qty": 1,
                "price": float(order.amount),
                "amount": float(order.amount),
                "tax_rate": 0,
                "tax": 0,
            }
        ],
        amount=order.amount,
        tax_amount=0,
        total_amount=order.amount,
        invoice_type=payload.invoice_type or "vat_normal",
        # 数电票人工闭环：申请即进入后台待办，运营在电子税务局开票后上传凭证
        status="requested",
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/invoices/{invoice_id}/generate-pdf")
async def generate_invoice(
    invoice_id: str,
    principal: Principal = Depends(require_roles(UserRole.owner, UserRole.admin)),
    db: Session = Depends(get_db),
) -> dict:
    """Generate PDF for an existing invoice."""
    from uuid import UUID

    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == UUID(invoice_id),
            Invoice.tenant_id == principal.tenant_id,
        )
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf_path = await generate_invoice_pdf(invoice)
    invoice.pdf_path = pdf_path
    # 付款凭证 PDF 与数电票状态解耦：生成凭证不再改变开票流程状态
    # （requested/issued/rejected 由后台开具/驳回驱动）。
    if invoice.status not in ("requested", "issued", "rejected"):
        invoice.status = "generated"
    db.commit()

    return {"pdf_path": pdf_path, "invoice_no": invoice.invoice_no}


@router.get("/invoices/{invoice_id}/download")
async def download_invoice(
    invoice_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """Download payment voucher PDF (not a tax invoice)."""
    from uuid import UUID

    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == UUID(invoice_id),
            Invoice.tenant_id == principal.tenant_id,
        )
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not invoice.pdf_path:
        raise HTTPException(status_code=404, detail="Invoice PDF not generated yet")

    return FileResponse(
        invoice.pdf_path,
        media_type="application/pdf",
        filename=f"付款凭证_{invoice.invoice_no}.pdf",
    )


@router.get("/invoices/{invoice_id}/voucher")
async def download_invoice_voucher(
    invoice_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """Download the issued e-invoice file (数电票) uploaded by the operator."""
    from uuid import UUID

    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == UUID(invoice_id),
            Invoice.tenant_id == principal.tenant_id,
        )
    )
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status != "issued" or not invoice.voucher_data:
        raise HTTPException(status_code=404, detail="发票尚未开具")

    from urllib.parse import quote

    from fastapi.responses import Response

    filename = quote(invoice.voucher_filename or f"einvoice_{invoice.invoice_no}")
    return Response(
        content=invoice.voucher_data,
        media_type=invoice.voucher_content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        },
    )


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
) -> list[Invoice]:
    return list(
        db.scalars(
            select(Invoice)
            .where(Invoice.tenant_id == principal.tenant_id)
            .order_by(Invoice.created_at.desc())
        ).all()
    )

import secrets
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_principal, require_roles
from app.core.db import get_db
from app.models.models import Invoice, Order, Payment, Product, UserRole
from app.schemas.schemas import (
    CommerceOut,
    InvoiceCreate,
    InvoiceOut,
    OrderCreate,
    OrderOut,
    PaymentCreate,
)
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
    product = db.scalar(
        select(Product).where(Product.code == payload.product_code, Product.active.is_(True))
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    order = Order(
        tenant_id=principal.tenant_id,
        order_no=f"Y{secrets.token_hex(8).upper()}",
        product_code=product.code,
        amount=product.promotional_price or product.price,
        currency="CNY",
        status="created",
    )
    db.add(order)
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
    """Create invoice record for an order."""
    order = db.scalar(
        select(Order).where(Order.id == payload.order_id, Order.tenant_id == principal.tenant_id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "paid":
        raise HTTPException(status_code=400, detail="Order must be paid before invoicing")

    invoice_no = _generate_invoice_no()

    invoice = Invoice(
        tenant_id=principal.tenant_id,
        order_id=order.id,
        invoice_no=invoice_no,
        title=payload.title,
        tax_number=payload.tax_number,
        address_phone=payload.address_phone,
        bank_account=payload.bank_account,
        seller_name=payload.seller_name or "",
        seller_tax_number=payload.seller_tax_number or "",
        items_json=payload.items or [
            {
                "name": order.product_code,
                "spec": "",
                "unit": "次",
                "qty": 1,
                "price": order.amount,
                "amount": order.amount,
                "tax_rate": 0,
                "tax": 0,
            }
        ],
        amount=order.amount,
        tax_amount=0,
        total_amount=order.amount,
        invoice_type=payload.invoice_type or "vat_normal",
        status="generated",
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
    invoice.status = "generated"
    db.commit()

    return {"pdf_path": pdf_path, "invoice_no": invoice.invoice_no}


@router.get("/invoices/{invoice_id}/download")
async def download_invoice(
    invoice_id: str,
    principal: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    """Download invoice PDF."""
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
        filename=f"发票_{invoice.invoice_no}.pdf",
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

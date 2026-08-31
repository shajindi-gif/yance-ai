"""Add Alipay + invoice fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260809_0003"
down_revision: Union[str, None] = "20260809_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Payment: add alipay fields + currency
    op.add_column("payments", sa.Column("currency", sa.String(8), nullable=True, server_default="CNY"))
    op.add_column("payments", sa.Column("alipay_trade_no", sa.String(64), nullable=True))
    op.add_column("payments", sa.Column("alipay_buyer_logon_id", sa.String(160), nullable=True))
    op.add_column("payments", sa.Column("alipay_buyer_user_id", sa.String(32), nullable=True))
    op.create_index(op.f("ix_payments_alipay_trade_no"), "payments", ["alipay_trade_no"], unique=False)

    # Invoice: rebuild with new columns
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS amount")
    op.add_column("invoices", sa.Column("invoice_no", sa.String(64), nullable=True))
    op.add_column("invoices", sa.Column("invoice_code", sa.String(32), nullable=True))
    op.add_column("invoices", sa.Column("address_phone", sa.String(300), nullable=True))
    op.add_column("invoices", sa.Column("bank_account", sa.String(200), nullable=True))
    op.add_column("invoices", sa.Column("seller_name", sa.String(240), nullable=True))
    op.add_column("invoices", sa.Column("seller_tax_number", sa.String(64), nullable=True))
    op.add_column("invoices", sa.Column("items_json", postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default="[]"))
    op.add_column("invoices", sa.Column("amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("tax_amount", sa.Numeric(12, 2), nullable=True, server_default="0"))
    op.add_column("invoices", sa.Column("total_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column("invoices", sa.Column("invoice_type", sa.String(40), nullable=True, server_default="vat_normal"))
    op.add_column("invoices", sa.Column("pdf_path", sa.String(700), nullable=True))
    op.create_index(op.f("ix_invoices_invoice_no"), "invoices", ["invoice_no"], unique=True)

    # Fix null columns for existing rows
    op.execute("UPDATE payments SET currency='CNY' WHERE currency IS NULL")
    op.execute("UPDATE invoices SET amount=0 WHERE amount IS NULL")
    op.execute("UPDATE invoices SET total_amount=0 WHERE total_amount IS NULL")


def downgrade() -> None:
    # Payment
    op.drop_index(op.f("ix_payments_alipay_trade_no"), table_name="payments")
    op.drop_column("payments", "alipay_buyer_user_id")
    op.drop_column("payments", "alipay_buyer_logon_id")
    op.drop_column("payments", "alipay_trade_no")
    op.drop_column("payments", "currency")

    # Invoice
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS tax_amount")
    op.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS total_amount")
    op.drop_index(op.f("ix_invoices_invoice_no"), table_name="invoices")
    op.drop_column("invoices", "pdf_path")
    op.drop_column("invoices", "invoice_type")
    op.drop_column("invoices", "total_amount")
    op.drop_column("invoices", "tax_amount")
    op.drop_column("invoices", "amount")
    op.drop_column("invoices", "items_json")
    op.drop_column("invoices", "seller_tax_number")
    op.drop_column("invoices", "seller_name")
    op.drop_column("invoices", "bank_account")
    op.drop_column("invoices", "address_phone")
    op.drop_column("invoices", "invoice_code")
    op.drop_column("invoices", "invoice_no")

"""Align ORM invariants with the additive legacy schema.

Revision ID: 20260903_0012
Revises: 20260903_0011
"""

import sqlalchemy as sa
from sqlalchemy.types import TypeEngine

from alembic import op

revision = "20260903_0012"
down_revision = "20260903_0011"
branch_labels = None
depends_on = None


def _backfill_and_require(
    table: str, column: str, value_sql: str, column_type: TypeEngine
) -> None:
    op.execute(sa.text(f'UPDATE "{table}" SET "{column}" = {value_sql} WHERE "{column}" IS NULL'))
    op.alter_column(table, column, existing_type=column_type, nullable=False)


def upgrade() -> None:
    _backfill_and_require("deliverables", "version", "1", sa.Integer())
    _backfill_and_require("deliverables", "status", "'generated'", sa.String(40))
    _backfill_and_require("deliverables", "metadata", "'{}'::json", sa.JSON())

    _backfill_and_require("invoices", "seller_name", "''", sa.String(240))
    _backfill_and_require("invoices", "seller_tax_number", "''", sa.String(64))
    _backfill_and_require("invoices", "items_json", "'[]'::json", sa.JSON())
    _backfill_and_require("invoices", "amount", "0", sa.Numeric(12, 2))
    _backfill_and_require("invoices", "tax_amount", "0", sa.Numeric(12, 2))
    _backfill_and_require("invoices", "total_amount", "0", sa.Numeric(12, 2))
    _backfill_and_require("invoices", "invoice_type", "'vat_normal'", sa.String(40))

    _backfill_and_require("payments", "currency", "'CNY'", sa.String(8))

    _backfill_and_require("revision_requests", "created_at", "now()", sa.DateTime(timezone=True))
    _backfill_and_require("revision_requests", "status", "'pending'", sa.String(40))

    _backfill_and_require("tasks", "input_data", "'{}'::json", sa.JSON())
    _backfill_and_require("tasks", "metadata", "'{}'::json", sa.JSON())
    _backfill_and_require("tasks", "priority", "'normal'", sa.String(20))
    _backfill_and_require("tasks", "workflow_version", "'v1'", sa.String(20))
    _backfill_and_require("tasks", "payment_status", "'unpaid'", sa.String(40))
    _backfill_and_require("tasks", "created_at", "now()", sa.DateTime(timezone=True))
    _backfill_and_require("tasks", "updated_at", "now()", sa.DateTime(timezone=True))


def downgrade() -> None:
    for table, column, column_type in (
        ("tasks", "updated_at", sa.DateTime(timezone=True)),
        ("tasks", "created_at", sa.DateTime(timezone=True)),
        ("tasks", "payment_status", sa.String(40)),
        ("tasks", "workflow_version", sa.String(20)),
        ("tasks", "priority", sa.String(20)),
        ("tasks", "metadata", sa.JSON()),
        ("tasks", "input_data", sa.JSON()),
        ("revision_requests", "status", sa.String(40)),
        ("revision_requests", "created_at", sa.DateTime(timezone=True)),
        ("payments", "currency", sa.String(8)),
        ("invoices", "invoice_type", sa.String(40)),
        ("invoices", "total_amount", sa.Numeric(12, 2)),
        ("invoices", "tax_amount", sa.Numeric(12, 2)),
        ("invoices", "amount", sa.Numeric(12, 2)),
        ("invoices", "items_json", sa.JSON()),
        ("invoices", "seller_tax_number", sa.String(64)),
        ("invoices", "seller_name", sa.String(240)),
        ("deliverables", "status", sa.String(40)),
        ("deliverables", "metadata", sa.JSON()),
        ("deliverables", "version", sa.Integer()),
    ):
        op.alter_column(table, column, existing_type=column_type, nullable=True)

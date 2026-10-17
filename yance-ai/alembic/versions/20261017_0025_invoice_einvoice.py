"""Invoice e-invoice manual issuance loop (数电票人工闭环).

Revision ID: 20261017_0025
Revises: 20261017_0024

ROLLBACK PLAN: downgrade() drops the five added columns on invoices.
No business data is lost except the uploaded voucher file bytes themselves
(the 数电票 file can be re-uploaded from 电子税务局). Safe to roll back.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261017_0025"
down_revision = "20261017_0024"
branch_labels = None
depends_on = None

COLUMNS = [
    sa.Column("voucher_filename", sa.String(255)),
    sa.Column("voucher_content_type", sa.String(120)),
    sa.Column("voucher_data", sa.LargeBinary),
    sa.Column("issued_at", sa.DateTime(timezone=True)),
    sa.Column("review_note", sa.Text()),
]


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column("invoices", column)


def downgrade() -> None:
    for column in reversed(COLUMNS):
        op.drop_column("invoices", column.name)

"""Add bank receipt fields to payments

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260809_0004"
down_revision: Union[str, None] = "20260809_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("bank_receipt_url", sa.String(700), nullable=True))
    op.add_column("payments", sa.Column("bank_verified_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "bank_verified_at")
    op.drop_column("payments", "bank_receipt_url")

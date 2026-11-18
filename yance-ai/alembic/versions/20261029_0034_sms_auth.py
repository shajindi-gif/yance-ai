"""Phone identities and short-lived SMS verification ledger; retain on rollback."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261029_0034"
down_revision = "20261027_0033"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("users", "email", existing_type=sa.String(320), nullable=True)
    op.add_column("users", sa.Column("phone", sa.String(16), nullable=True))
    op.create_unique_constraint("uq_users_phone", "users", ["phone"])
    op.create_table(
        "sms_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("phone", sa.String(16), nullable=False),
        sa.Column("purpose", sa.String(80), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sms_phone_created", "sms_codes", ["phone", "created_at"])


def downgrade():
    raise RuntimeError(
        "Retain phone identities and nullable emails. Roll back to a phone-compatible app; never drop accounts or invent email addresses."
    )

"""Email verification codes for passwordless login.

Revision ID: 20261015_0023
Revises: 20260927_0022
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261015_0023"
down_revision = "20260927_0022"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "email_codes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False, server_default="login"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_email_codes_email", "email_codes", ["email"])
    op.create_index("ix_email_code_email_created", "email_codes", ["email", "created_at"])
    op.create_index("ix_email_code_ip_created", "email_codes", ["ip_address", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_email_code_ip_created", table_name="email_codes")
    op.drop_index("ix_email_code_email_created", table_name="email_codes")
    op.drop_index("ix_email_codes_email", table_name="email_codes")
    op.drop_table("email_codes")

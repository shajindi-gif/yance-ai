"""Optional feedback retry identifiers. Keep this additive field on app rollback."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261027_0033"
down_revision = "20261024_0032"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "feedback", sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_unique_constraint(
        "uq_feedback_user_request", "feedback", ["tenant_id", "user_id", "client_request_id"]
    )


def downgrade():
    raise RuntimeError(
        "Retain additive feedback retry identifiers; roll back the app or restore to a separate verified database."
    )

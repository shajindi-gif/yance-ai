"""Optional request identifiers for comment creation. Retain on app rollback."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261023_0031"
down_revision = "20261023_0030"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "application_comments",
        sa.Column("client_request_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_application_comment_request",
        "application_comments",
        ["tenant_id", "application_id", "client_request_id"],
    )


def downgrade():
    op.drop_constraint("uq_application_comment_request", "application_comments", type_="unique")
    op.drop_column("application_comments", "client_request_id")

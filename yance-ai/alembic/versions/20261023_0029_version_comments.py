"""Bind optional review comments to immutable draft versions.

Keep the column on production application rollback. Downgrade loses bindings.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261023_0029"
down_revision = "20261023_0028"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "application_comments",
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_application_comments_artifact_id",
        "application_comments",
        "application_artifacts",
        ["artifact_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_constraint(
        "fk_application_comments_artifact_id", "application_comments", type_="foreignkey"
    )
    op.drop_column("application_comments", "artifact_id")

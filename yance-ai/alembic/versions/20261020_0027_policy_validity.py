"""Separate policy validity from an application-window deadline.

No historical evidence is rewritten or inferred. Legacy expiry_date values
remain intact (may be historical deadlines); new versions use separate fields.
Keep additive columns on application rollback. Downgrade loses newly curated
metadata and is only appropriate for disposable databases.
"""
import sqlalchemy as sa

from alembic import op

revision = "20261020_0027"
down_revision = "20261020_0026"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("policies", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policy_versions", sa.Column("application_deadline", sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column("policy_versions", "application_deadline")
    op.drop_column("policies", "expires_at")

"""Optional human summary suggestions and immutable resolution records.

Retain columns on application rollback; downgrade discards review history.
"""

import sqlalchemy as sa

from alembic import op

revision = "20261023_0030"
down_revision = "20261023_0029"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("application_comments", sa.Column("proposed_summary", sa.Text(), nullable=True))
    op.add_column("application_comments", sa.Column("resolution_json", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("application_comments", "resolution_json")
    op.drop_column("application_comments", "proposed_summary")

"""Add a backwards-compatible JWT revocation counter.

Existing tokens omit the counter and are treated as version zero until reset
or logout. Old applications can read this schema but do NOT enforce revocation;
rolling back auth code requires invalidating JWTs at the gateway/secret layer.
Keep the column during application rollback. Downgrade is destructive to
revocation history and is only for disposable test databases.
"""
import sqlalchemy as sa

from alembic import op

revision = "20261020_0026"
down_revision = "20261017_0025"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("users", "auth_version")

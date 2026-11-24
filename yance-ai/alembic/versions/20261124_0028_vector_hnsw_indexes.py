"""Add HNSW indexes for cosine vector search (acceptance ACC-10).

Revision ID: 20261124_0028
Revises: 20261020_0027

Without an index every policy / policy-chunk vector query is a sequential scan.
Indexes are built CONCURRENTLY so writes are not blocked; on a large production
corpus schedule this migration in a low-traffic window (see the release runbook).
"""

from alembic import op

revision = "20261124_0028"
down_revision = "20261020_0027"
branch_labels = None
depends_on = None

INDEXES = (
    ("ix_policy_chunks_embedding_hnsw", "policy_chunks"),
    ("ix_policies_embedding_hnsw", "policies"),
)


def upgrade():
    with op.get_context().autocommit_block():
        for name, table in INDEXES:
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} "
                "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
            )


def downgrade():
    with op.get_context().autocommit_block():
        for name, _ in INDEXES:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")

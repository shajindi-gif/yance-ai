"""Fix policies.embedding dimension 1536 -> 1024 (B1).

The embedding model (Cloudflare Workers AI bge-large-en-v1.5) produces
1024-dimensional vectors, but the initial migration created the column as
vector(1536). Align the column with the model and the SQLAlchemy model
definition (Vector(1024)).

Revision ID: 20260809_0005
Revises: 20260809_0004
Create Date: 2026-08-09
"""

from pgvector.sqlalchemy import Vector

from alembic import op

revision = "20260809_0005"
down_revision = "20260809_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "policies",
        "embedding",
        type_=Vector(dim=1024),
        existing_type=Vector(dim=1536),
        existing_nullable=True,
        postgresql_using="embedding::vector(1024)",
    )


def downgrade() -> None:
    op.alter_column(
        "policies",
        "embedding",
        type_=Vector(dim=1536),
        existing_type=Vector(dim=1024),
        existing_nullable=True,
        postgresql_using="embedding::vector(1536)",
    )

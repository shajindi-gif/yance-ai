"""Align task and deliverable columns with the current ORM.

Revision ID: 20260902_0009
Revises: 20260817_0008
"""

import sqlalchemy as sa

from alembic import op

revision = "20260902_0009"
down_revision = "20260817_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("tasks", sa.Column("current_stage", sa.String(200), nullable=True))
    op.add_column(
        "deliverables",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.add_column(
        "deliverables",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_column("deliverables", "updated_at")
    op.drop_column("deliverables", "created_at")
    op.drop_column("tasks", "current_stage")
    op.drop_column("tasks", "progress")

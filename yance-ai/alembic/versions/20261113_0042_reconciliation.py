"""Daily provider bill audit and signed provider payment timestamps."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision = "20261113_0042"
down_revision = "20261113_0041"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("paid_at", sa.DateTime(timezone=True)))
    op.create_index("ix_payments_paid_at", "payments", ["paid_at"])
    op.create_table(
        "reconciliation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("source_sha256", sa.String(64)),
        sa.Column("issue_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(80)),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "bill_date", name="uq_reconciliation_run"),
    )
    op.create_table(
        "reconciliation_issues",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("reference", sa.String(128), nullable=False),
        sa.Column("issue_type", sa.String(80), nullable=False),
        sa.Column("expected_amount", sa.Numeric(12, 2)),
        sa.Column("received_amount", sa.Numeric(12, 2)),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider", "bill_date", "reference", "issue_type", name="uq_reconciliation_issue"
        ),
    )


def downgrade():
    for table in ("reconciliation_runs", "reconciliation_issues"):
        if op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {table}")):
            raise RuntimeError(
                "Reconciliation evidence exists; retain tables during application rollback"
            )
    op.drop_table("reconciliation_issues")
    op.drop_table("reconciliation_runs")
    op.drop_index("ix_payments_paid_at", table_name="payments")
    op.drop_column("payments", "paid_at")

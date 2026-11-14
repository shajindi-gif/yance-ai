"""Freeze report bytes and bind new orders; no historical rewrite or destructive rollback."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20261031_0035"
down_revision = "20261029_0034"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("deliverables", sa.Column("frozen_pdf", sa.LargeBinary(), nullable=True))
    op.add_column("deliverables", sa.Column("frozen_pdf_sha256", sa.String(64), nullable=True))
    op.add_column("orders", sa.Column("report_deliverable_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_orders_report_deliverable", "orders", "deliverables", ["report_deliverable_id"], ["id"], ondelete="RESTRICT")


def downgrade():
    raise RuntimeError("Retain immutable reports and purchased-version bindings; roll back the application only to a snapshot-compatible build.")

"""Make Policy global (remove tenant scoping) + add Global Policy KB fields.

Per master task: Policy should be platform-level, shared by all tenants.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "20260814_0006_global_policy_kb"
down_revision = "20260809_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Make tenant_id nullable on policies
    op.alter_column(
        "policies",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=True,
        existing_nullable=False,
    )

    # 2. Add Global Policy KB fields
    op.add_column("policies", sa.Column("issuing_authority", sa.String(240), nullable=True))
    op.add_column("policies", sa.Column("level", sa.String(40), nullable=True))  # national/provincial/municipal/district
    op.add_column("policies", sa.Column("province", sa.String(80), nullable=True))
    op.add_column("policies", sa.Column("city", sa.String(80), nullable=True))
    op.add_column("policies", sa.Column("district", sa.String(80), nullable=True))
    op.add_column("policies", sa.Column("industry", sa.String(160), nullable=True))
    op.add_column("policies", sa.Column("policy_type", sa.String(80), nullable=True))  # subsidy/tax_break/qualification/...
    op.add_column("policies", sa.Column("start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policies", sa.Column("deadline", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policies", sa.Column("original_text", sa.Text, nullable=True))
    op.add_column("policies", sa.Column("summary", sa.Text, nullable=True))
    op.add_column("policies", sa.Column("source", sa.String(160), nullable=True))
    op.add_column("policies", sa.Column("crawled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("policies", sa.Column("support_amount", sa.String(120), nullable=True))  # e.g. "最高500万"
    op.add_column("policies", sa.Column("support_type", sa.String(120), nullable=True))   # 资金补贴/税收优惠/资质认定

    # 3. Index for global policy queries
    op.create_index("ix_policies_level", "policies", ["level"])
    op.create_index("ix_policies_province", "policies", ["province"])
    op.create_index("ix_policies_industry", "policies", ["industry"])
    op.create_index("ix_policies_status", "policies", ["status"])
    op.create_index("ix_policies_deadline", "policies", ["deadline"])


def downgrade() -> None:
    op.drop_index("ix_policies_deadline", table_name="policies")
    op.drop_index("ix_policies_status", table_name="policies")
    op.drop_index("ix_policies_industry", table_name="policies")
    op.drop_index("ix_policies_province", table_name="policies")
    op.drop_index("ix_policies_level", table_name="policies")

    op.drop_column("policies", "support_type")
    op.drop_column("policies", "support_amount")
    op.drop_column("policies", "crawled_at")
    op.drop_column("policies", "source")
    op.drop_column("policies", "summary")
    op.drop_column("policies", "original_text")
    op.drop_column("policies", "deadline")
    op.drop_column("policies", "start_date")
    op.drop_column("policies", "policy_type")
    op.drop_column("policies", "industry")
    op.drop_column("policies", "district")
    op.drop_column("policies", "city")
    op.drop_column("policies", "province")
    op.drop_column("policies", "level")
    op.drop_column("policies", "issuing_authority")

    op.alter_column(
        "policies",
        "tenant_id",
        existing_type=sa.UUID(),
        nullable=False,
        existing_nullable=True,
    )

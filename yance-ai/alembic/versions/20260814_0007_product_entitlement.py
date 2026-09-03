"""Add Product SKU table and Entitlement table for unified pricing.

Per master task section 4 & 23: unified Product model as single source of truth
for all pricing. Entitlement tracks what each tenant has purchased.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260814_0007"
down_revision = "20260814_0006_global_policy_kb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create products table
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("code", sa.String(80), unique=True, nullable=False, index=True),
        sa.Column("name", sa.String(240), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("product_type", sa.String(40), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("original_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("promotional_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("entitlement_type", sa.String(40), nullable=False, server_default="report"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 2. Create entitlements table
    op.create_table(
        "entitlements",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column(
            "product_id", sa.UUID(), sa.ForeignKey("products.id"), nullable=False, index=True
        ),
        sa.Column("order_id", sa.UUID(), sa.ForeignKey("orders.id"), nullable=False, index=True),
        sa.Column("resource_type", sa.String(40), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # 3. Seed 4 SKUs
    op.execute("""
        INSERT INTO products (id, code, name, description, product_type, price, original_price, promotional_price, entitlement_type, active, sort_order, created_at, updated_at)
        VALUES
        (gen_random_uuid(), 'FREE_POLICY_MATCH', '免费政策匹配', '注册即享：企业画像、政策AI匹配、Top 5政策机会、基础匹配理由。发现政策机会的第一步。', 'free', 0.00, NULL, NULL, 'free', true, 0, now(), now()),
        (gen_random_uuid(), 'POLICY_REPORT', '企业政策 AI 体检报告', '完整政策机会分析：企业资格矩阵、条件差距、行动路线图、申报日历、专业PDF交付。一个企业一份报告。', 'report', 99.00, 199.00, NULL, 'report', true, 1, now(), now()),
        (gen_random_uuid(), 'POLICY_DIAGNOSIS', '单项目申报诊断', '针对一项具体政策的深度诊断：所有硬性条件逐条判断、材料清单、申报流程、时间节点、评分机制、主要风险。', 'diagnosis', 299.00, 399.00, NULL, 'diagnosis', true, 2, now(), now()),
        (gen_random_uuid(), 'APPLICATION_PLAN', 'AI 申报方案包', '完整申报策略：企业亮点提炼、政策条款对应、材料目录、实施计划、申报时间表、信息缺口分析、填报Checklist。', 'plan', 699.00, 999.00, NULL, 'plan', true, 3, now(), now())
    """)


def downgrade() -> None:
    op.drop_table("entitlements")
    op.drop_table("products")

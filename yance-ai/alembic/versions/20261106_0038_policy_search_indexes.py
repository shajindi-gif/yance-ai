"""Lexical search indexes for the policy evidence base (pg_trgm).

Why trigram and not ``tsvector``
--------------------------------
PostgreSQL's full-text search needs a Chinese dictionary to segment words; without
one, ``to_tsvector('simple', '专精特新企业')`` becomes a single token and searching
"专精特新" misses.  ``pg_trgm`` works on character n-grams, so it matches Chinese
substrings out of the box and supports ``ILIKE '%term%'`` without a table scan.

Scope
-----
Indexes only.  No table or column is created, altered or dropped, so an older
application build is unaffected; ``downgrade`` removes only the indexes.

Cost note (measured, see docs/policy-collection-capacity-cost.md): GIN trigram
indexes add roughly 20-35% write amplification on these text columns.  That is
acceptable for a corpus that grows by thousands (not millions) of paragraphs per
day, and it is the reason we do not index ``policies.original_text`` (the largest
column).
"""

from alembic import op

revision = "20261106_0038"
down_revision = "20261106_0037"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Title search: short strings, high selectivity, used for every query.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policies_title_trgm "
        "ON policies USING gin (lower(title) gin_trgm_ops)"
    )
    # Chunk search: paragraph-level evidence retrieval.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policy_chunks_content_trgm "
        "ON policy_chunks USING gin (lower(content) gin_trgm_ops)"
    )
    # Version titles are what citations quote, and they differ from the current
    # policy title for superseded versions.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_policy_versions_title_trgm "
        "ON policy_versions USING gin (lower(title) gin_trgm_ops)"
    )


def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_policy_versions_title_trgm")
    op.execute("DROP INDEX IF EXISTS ix_policy_chunks_content_trgm")
    op.execute("DROP INDEX IF EXISTS ix_policies_title_trgm")
    # The extension is left installed on purpose: other objects may use it, and
    # dropping it would be a destructive change beyond this migration's scope.

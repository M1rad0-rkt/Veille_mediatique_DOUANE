"""Schéma initial

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    # Les extensions sont aussi créées par scripts/db-init ; IF NOT EXISTS rend ceci sans risque.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table("roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(30), nullable=False, unique=True),
        sa.Column("permissions", pg.JSONB, nullable=False, server_default="[]"))

    op.create_table("users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("last_login_at", TZ))

    op.create_table("categories",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("slug", sa.String(60), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(9), nullable=False, server_default="#64748b"),
        sa.Column("nav_group", sa.String(30), nullable=False, server_default="autres"),
        sa.Column("position", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"))

    op.create_table("sources",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("base_url", sa.Text, nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="rss"),
        sa.Column("feed_url", sa.Text),
        sa.Column("selectors", pg.JSONB),
        sa.Column("interval_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("robots_ok", sa.Boolean),
        sa.Column("status", sa.String(20), nullable=False, server_default="idle"),
        sa.Column("last_success_at", TZ),
        sa.Column("last_error", sa.Text),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("etag", sa.String(255)),
        sa.Column("last_modified", sa.String(255)),
        sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now()))

    op.create_table("news",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("canonical_url", sa.Text),
        sa.Column("url_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("content_text", sa.Text),
        sa.Column("content_is_partial", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("excerpt", sa.Text),
        sa.Column("author", sa.String(255)),
        sa.Column("image_url", sa.Text),
        sa.Column("published_at", TZ),
        sa.Column("published_at_origin", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("collected_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("sort_date", TZ, sa.Computed("COALESCE(published_at, collected_at)", persisted=True)),
        sa.Column("language", sa.String(8), nullable=False, server_default="fr"),
        sa.Column("processing_status", sa.String(20), nullable=False, server_default="collected"),
        sa.Column("duplicate_of_id", sa.Integer, sa.ForeignKey("news.id", ondelete="SET NULL")),
        sa.Column("search_vector", pg.TSVECTOR, sa.Computed(
            "to_tsvector('french', coalesce(title, '') || ' ' || coalesce(excerpt, ''))", persisted=True)))
    op.execute("CREATE INDEX ix_news_sort_date ON news (sort_date DESC)")
    op.create_index("ix_news_source_id", "news", ["source_id"])
    op.create_index("ix_news_content_hash", "news", ["content_hash"])
    op.create_index("ix_news_processing_status", "news", ["processing_status"])
    op.create_index("ix_news_search_vector", "news", ["search_vector"], postgresql_using="gin")
    op.create_index("ix_news_title_trgm", "news", ["title"], postgresql_using="gin",
                    postgresql_ops={"title": "gin_trgm_ops"})

    op.create_table("news_categories",
        sa.Column("news_id", sa.Integer, sa.ForeignKey("news.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("category_id", sa.Integer, sa.ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confidence", sa.Float),
        sa.Column("origin", sa.String(10), nullable=False, server_default="ai"))

    op.create_table("news_summaries",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("news_id", sa.Integer, sa.ForeignKey("news.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("provider", sa.String(30)),
        sa.Column("model", sa.String(80)),
        sa.Column("prompt_version", sa.String(20)),
        sa.Column("status", sa.String(25), nullable=False),
        sa.Column("summary", sa.Text),
        sa.Column("key_points", pg.JSONB),
        sa.Column("entities", pg.JSONB),
        sa.Column("error", sa.Text),
        sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now()))

    op.create_table("user_favorites",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("news_id", sa.Integer, sa.ForeignKey("news.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", TZ, nullable=False, server_default=sa.func.now()))

    op.create_table("user_read_history",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("news_id", sa.Integer, sa.ForeignKey("news.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("read_at", TZ, nullable=False, server_default=sa.func.now()))

    op.create_table("collection_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", TZ),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("found", sa.Integer, nullable=False, server_default="0"),
        sa.Column("new", sa.Integer, nullable=False, server_default="0"),
        sa.Column("duplicates", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer, nullable=False, server_default="0"),
        sa.Column("message", sa.Text))
    op.execute("CREATE INDEX ix_collection_logs_started ON collection_logs (started_at DESC)")

    op.create_table("app_settings",
        sa.Column("key", sa.String(80), primary_key=True),
        sa.Column("value", pg.JSONB))


def downgrade() -> None:
    for table in ["app_settings", "collection_logs", "user_read_history", "user_favorites",
                  "news_summaries", "news_categories", "news", "sources", "categories", "users", "roles"]:
        op.drop_table(table)

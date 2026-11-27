"""File de demandes de l'agent + compteur de tentatives IA

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "agent_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id", ondelete="CASCADE")),
        sa.Column("requested_by", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("requested_at", TZ, nullable=False, server_default=sa.func.now()),
        sa.Column("claimed_at", TZ),
    )
    op.add_column("news_summaries", sa.Column("attempts", sa.Integer, nullable=False, server_default="0"))
    op.add_column("news_summaries", sa.Column("updated_at", TZ, nullable=False, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_column("news_summaries", "updated_at")
    op.drop_column("news_summaries", "attempts")
    op.drop_table("agent_requests")

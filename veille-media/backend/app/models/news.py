from datetime import datetime

from sqlalchemy import (Boolean, Computed, DateTime, Float, ForeignKey, Index, Integer,
                        String, Text, func, text)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.category import Category
from app.models.source import Source


class News(Base):
    __tablename__ = "news"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str | None] = mapped_column(Text)
    url_hash: Mapped[str] = mapped_column(String(64), unique=True)       # dédoublonnage niveau 1
    content_hash: Mapped[str | None] = mapped_column(String(64))         # dédoublonnage niveau 2
    content_text: Mapped[str | None] = mapped_column(Text)               # texte complet : usage interne
    content_is_partial: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    excerpt: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))
    image_url: Mapped[str | None] = mapped_column(Text)

    # Date réelle de publication (peut être inconnue) — JAMAIS remplacée par la date de collecte.
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at_origin: Mapped[str] = mapped_column(String(20), default="unknown", server_default="unknown")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Date technique de tri uniquement.
    sort_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), Computed("COALESCE(published_at, collected_at)", persisted=True))

    language: Mapped[str] = mapped_column(String(8), default="fr", server_default="fr")
    processing_status: Mapped[str] = mapped_column(
        String(20), default="collected", server_default="collected")  # collected|extracted|enriched|failed
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("news.id", ondelete="SET NULL"))
    search_vector = mapped_column(TSVECTOR, Computed(
        "to_tsvector('french', coalesce(title, '') || ' ' || coalesce(excerpt, ''))", persisted=True))

    source: Mapped[Source] = relationship()
    category_links: Mapped[list["NewsCategory"]] = relationship(
        back_populates="news", cascade="all, delete-orphan")
    summary: Mapped["NewsSummary | None"] = relationship(
        back_populates="news", cascade="all, delete-orphan", uselist=False)

    __table_args__ = (
        Index("ix_news_sort_date", text("sort_date DESC")),
        Index("ix_news_source_id", "source_id"),
        Index("ix_news_content_hash", "content_hash"),
        Index("ix_news_processing_status", "processing_status"),
        Index("ix_news_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_news_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
    )


class NewsCategory(Base):
    """Association multi-thématiques. origin='manual' n'est jamais écrasé par l'IA."""
    __tablename__ = "news_categories"
    news_id: Mapped[int] = mapped_column(ForeignKey("news.id", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    confidence: Mapped[float | None] = mapped_column(Float)
    origin: Mapped[str] = mapped_column(String(10), default="ai", server_default="ai")  # ai|manual

    news: Mapped[News] = relationship(back_populates="category_links")
    category: Mapped[Category] = relationship()


class NewsSummary(Base):
    __tablename__ = "news_summaries"
    id: Mapped[int] = mapped_column(primary_key=True)
    news_id: Mapped[int] = mapped_column(ForeignKey("news.id", ondelete="CASCADE"), unique=True)
    provider: Mapped[str | None] = mapped_column(String(30))
    model: Mapped[str | None] = mapped_column(String(80))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(25))  # ok|insufficient_content|failed
    summary: Mapped[str | None] = mapped_column(Text)
    key_points: Mapped[list | None] = mapped_column(JSONB)
    entities: Mapped[dict | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    news: Mapped[News] = relationship(back_populates="summary")

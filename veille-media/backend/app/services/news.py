"""Requêtes sur les actualités : filtres combinables, pagination, état favori/lu par utilisateur."""
import math
from datetime import date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Query
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import settings
from app.models import (Category, News, NewsCategory, User, UserFavorite, UserReadHistory)
from app.schemas.news import (CategoryTag, NewsOut, NewsPage, SourceMini, SummaryOut)

TZ = ZoneInfo(settings.timezone)


class NewsFilters:
    """Paramètres de requête combinables (mot-clé, catégorie, source, période, statut de lecture)."""

    def __init__(
        self,
        q: str | None = Query(None, max_length=200, description="Mot-clé"),
        category: str | None = Query(None, description="Slug de catégorie"),
        nav_group: str | None = Query(None, description="Groupe de navigation (economie, politique…)"),
        source_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        read_status: Literal["all", "read", "unread"] = "all",
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=100),
    ):
        self.q, self.category, self.nav_group, self.source_id = q, category, nav_group, source_id
        self.date_from, self.date_to, self.read_status = date_from, date_to, read_status
        self.page, self.page_size = page, page_size


def _fav_exists(user_id: int):
    return exists().where(UserFavorite.user_id == user_id, UserFavorite.news_id == News.id).correlate(News)


def _read_exists(user_id: int):
    return exists().where(UserReadHistory.user_id == user_id, UserReadHistory.news_id == News.id).correlate(News)


def _base_select(user_id: int):
    return (
        select(News, _fav_exists(user_id).label("is_favorite"), _read_exists(user_id).label("is_read"))
        .where(News.duplicate_of_id.is_(None))
        .options(
            joinedload(News.source),
            joinedload(News.summary),
            selectinload(News.category_links).joinedload(NewsCategory.category),
        )
    )


def _conditions(f: NewsFilters, user_id: int, favorites_only: bool = False) -> list:
    conds = []
    if f.q:
        tsq = func.websearch_to_tsquery("french", f.q)
        conds.append(or_(News.search_vector.op("@@")(tsq), News.title.icontains(f.q, autoescape=True)))
    if f.category:
        conds.append(News.id.in_(
            select(NewsCategory.news_id).join(Category, Category.id == NewsCategory.category_id)
            .where(Category.slug == f.category)))
    if f.nav_group:
        conds.append(News.id.in_(
            select(NewsCategory.news_id).join(Category, Category.id == NewsCategory.category_id)
            .where(Category.nav_group == f.nav_group)))
    if f.source_id:
        conds.append(News.source_id == f.source_id)
    if f.date_from:
        conds.append(News.sort_date >= datetime.combine(f.date_from, time.min, tzinfo=TZ))
    if f.date_to:
        conds.append(News.sort_date < datetime.combine(f.date_to + timedelta(days=1), time.min, tzinfo=TZ))
    if f.read_status == "read":
        conds.append(_read_exists(user_id))
    elif f.read_status == "unread":
        conds.append(~_read_exists(user_id))
    if favorites_only:
        conds.append(_fav_exists(user_id))
    return conds


def to_out(news: News, is_favorite: bool, is_read: bool) -> NewsOut:
    links = sorted(news.category_links, key=lambda l: (not l.is_primary, l.category.position))
    summary = None
    if news.summary:
        s = news.summary
        summary = SummaryOut(status=s.status, summary=s.summary,
                             key_points=s.key_points, entities=s.entities)
    return NewsOut(
        id=news.id, title=news.title, url=news.url, excerpt=news.excerpt, image_url=news.image_url,
        author=news.author, published_at=news.published_at, published_at_origin=news.published_at_origin,
        collected_at=news.collected_at, sort_date=news.sort_date, processing_status=news.processing_status,
        source=SourceMini(id=news.source.id, name=news.source.name),
        categories=[CategoryTag(id=l.category.id, slug=l.category.slug, name=l.category.name,
                                color=l.category.color, is_primary=l.is_primary, origin=l.origin,
                                confidence=l.confidence) for l in links],
        summary=summary, is_favorite=is_favorite, is_read=is_read)


def list_news(db: Session, user: User, f: NewsFilters, *, favorites_only: bool = False,
              history_only: bool = False) -> NewsPage:
    conds = _conditions(f, user.id, favorites_only)
    stmt = _base_select(user.id).where(*conds)
    count_stmt = select(func.count()).select_from(News).where(News.duplicate_of_id.is_(None), *conds)

    if history_only:  # tri par date de lecture
        join_on = and_(UserReadHistory.news_id == News.id, UserReadHistory.user_id == user.id)
        stmt = stmt.join(UserReadHistory, join_on).order_by(UserReadHistory.read_at.desc())
        count_stmt = count_stmt.join(UserReadHistory, join_on)
    else:  # les plus récentes d'abord
        stmt = stmt.order_by(News.sort_date.desc(), News.id.desc())

    total = db.scalar(count_stmt) or 0
    rows = db.execute(stmt.offset((f.page - 1) * f.page_size).limit(f.page_size)).unique().all()
    return NewsPage(items=[to_out(n, fav, rd) for n, fav, rd in rows], total=total, page=f.page,
                    page_size=f.page_size, pages=max(1, math.ceil(total / f.page_size)))


def latest_since(db: Session, user: User, since: datetime | None, limit: int = 50) -> list[NewsOut]:
    """Articles collectés après `since` (utilisé pour l'actualisation automatique du fil)."""
    stmt = _base_select(user.id)
    if since:
        stmt = stmt.where(News.collected_at > since)
    rows = db.execute(stmt.order_by(News.sort_date.desc(), News.id.desc()).limit(limit)).unique().all()
    return [to_out(n, fav, rd) for n, fav, rd in rows]


def get_news_row(db: Session, user: User, news_id: int):
    row = db.execute(_base_select(user.id).where(News.id == news_id)).unique().first()
    if not row:
        raise HTTPException(404, "Actualité introuvable")
    return row


def related_news(db: Session, user: User, news: News, limit: int = 5) -> list[NewsOut]:
    """Articles du même sujet : mêmes catégories (30 jours), classés par similarité de titre (pg_trgm)
    puis par date. Une similarité vectorielle (pgvector) reste possible plus tard sans changer l'API."""
    cat_ids = [l.category_id for l in news.category_links]
    if not cat_ids:
        return []
    since = datetime.now(TZ) - timedelta(days=30)
    sim = func.similarity(News.title, news.title)
    stmt = (_base_select(user.id)
            .where(News.id != news.id, News.sort_date >= since,
                   News.id.in_(select(NewsCategory.news_id).where(NewsCategory.category_id.in_(cat_ids))))
            .order_by(sim.desc(), News.sort_date.desc()).limit(limit))
    return [to_out(n, fav, rd) for n, fav, rd in db.execute(stmt).unique().all()]

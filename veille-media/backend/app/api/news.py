from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models import Category, News, NewsCategory, UserFavorite, UserReadHistory
from app.schemas.news import CategoryAssignment, LatestOut, NewsDetailOut, NewsPage
from app.services import news as svc

router = APIRouter(prefix="/news", tags=["news"])
Filters = Annotated[svc.NewsFilters, Depends()]


@router.get("", response_model=NewsPage)
def list_news(db: DbSession, user: CurrentUser, f: Filters):
    return svc.list_news(db, user, f)


@router.get("/search", response_model=NewsPage)
def search_news(db: DbSession, user: CurrentUser, f: Filters):
    if not f.q:
        raise HTTPException(422, "Le paramètre q est requis")
    return svc.list_news(db, user, f)


@router.get("/latest", response_model=LatestOut)
def latest(db: DbSession, user: CurrentUser, since: datetime | None = None):
    """Polling du fil : renvoie les articles collectés après `since`."""
    server_time = datetime.now(timezone.utc)
    items = svc.latest_since(db, user, since)
    return LatestOut(items=items, count=len(items), server_time=server_time)


@router.get("/favorites", response_model=NewsPage)
def favorites(db: DbSession, user: CurrentUser, f: Filters):
    return svc.list_news(db, user, f, favorites_only=True)


@router.get("/history", response_model=NewsPage)
def history(db: DbSession, user: CurrentUser, f: Filters):
    return svc.list_news(db, user, f, history_only=True)


@router.get("/{news_id}", response_model=NewsDetailOut)
def news_detail(news_id: int, db: DbSession, user: CurrentUser):
    news, fav, read = svc.get_news_row(db, user, news_id)
    base = svc.to_out(news, fav, read)
    return NewsDetailOut(**base.model_dump(), content_is_partial=news.content_is_partial,
                         related=svc.related_news(db, user, news))


@router.post("/{news_id}/favorite", status_code=204)
def add_favorite(news_id: int, db: DbSession, user: CurrentUser):
    svc.get_news_row(db, user, news_id)
    db.execute(pg_insert(UserFavorite).values(user_id=user.id, news_id=news_id).on_conflict_do_nothing())
    db.commit()


@router.delete("/{news_id}/favorite", status_code=204)
def remove_favorite(news_id: int, db: DbSession, user: CurrentUser):
    db.execute(delete(UserFavorite).where(UserFavorite.user_id == user.id, UserFavorite.news_id == news_id))
    db.commit()


@router.post("/{news_id}/read", status_code=204)
def mark_read(news_id: int, db: DbSession, user: CurrentUser):
    svc.get_news_row(db, user, news_id)
    stmt = pg_insert(UserReadHistory).values(user_id=user.id, news_id=news_id)
    db.execute(stmt.on_conflict_do_update(index_elements=["user_id", "news_id"], set_={"read_at": func.now()}))
    db.commit()


@router.delete("/{news_id}/read", status_code=204)
def mark_unread(news_id: int, db: DbSession, user: CurrentUser):
    db.execute(delete(UserReadHistory).where(UserReadHistory.user_id == user.id, UserReadHistory.news_id == news_id))
    db.commit()


@router.patch("/{news_id}/category", response_model=NewsDetailOut)
def correct_category(news_id: int, body: CategoryAssignment, db: DbSession, admin: AdminUser):
    """Correction manuelle : remplace les catégories ; origin='manual' n'est jamais écrasé par l'IA."""
    news = db.get(News, news_id)
    if not news:
        raise HTTPException(404, "Actualité introuvable")
    ids = set(body.category_ids)
    if body.primary_category_id not in ids:
        raise HTTPException(422, "La catégorie principale doit faire partie des catégories choisies")
    found = set(db.scalars(select(Category.id).where(Category.id.in_(ids))))
    if found != ids:
        raise HTTPException(422, "Catégorie inconnue")
    db.execute(delete(NewsCategory).where(NewsCategory.news_id == news_id))
    for cid in ids:
        db.add(NewsCategory(news_id=news_id, category_id=cid, origin="manual", confidence=None,
                            is_primary=(cid == body.primary_category_id)))
    db.commit()
    db.expire_all()  # recharger les catégories fraîchement écrites
    return news_detail(news_id, db, admin)


@router.post("/{news_id}/reprocess", response_model=NewsDetailOut)
def reprocess(news_id: int, db: DbSession, admin: AdminUser):
    """Relance classification + résumé IA sur un article (action administrateur, exécutée tout de suite)."""
    from sqlalchemy.orm import joinedload
    from app.ai import get_provider
    from app.ai.base import RateLimited
    from app.services.enrichment import enrich_news
    provider = get_provider()
    if provider is None:
        raise HTTPException(503, "IA non configurée : renseignez la clé API dans .env")
    news = db.scalar(select(News).where(News.id == news_id).options(joinedload(News.source)))
    if not news:
        raise HTTPException(404, "Actualité introuvable")
    if news.summary:
        news.summary.attempts = 0
    try:
        enrich_news(db, news, provider)
    except RateLimited:
        raise HTTPException(429, "Quota du fournisseur IA atteint, réessayez dans un instant")
    db.expire_all()
    return news_detail(news_id, db, admin)

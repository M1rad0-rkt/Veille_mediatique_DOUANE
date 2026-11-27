"""Enregistrement des articles collectés : dates, doublons, statut de traitement."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import News
from app.scrapers.extractor import ExtractedPage
from app.scrapers.base import RawArticle
from app.utils.dates import sane
from app.utils.text import content_hash, truncate
from app.utils.urls import normalize_url, same_site, url_hash

log = logging.getLogger(__name__)
PARTIAL_BELOW = 800   # caractères : en dessous, le texte est considéré comme partiel


def existing_hashes(db: Session, hashes: list[str]) -> set[str]:
    if not hashes:
        return set()
    return set(db.scalars(select(News.url_hash).where(News.url_hash.in_(hashes))))


def is_republished(db: Session, source_id: int, chash: str) -> bool:
    """Même titre+début de texte déjà publié par la MÊME source récemment (republication sous une autre URL).
    Volontairement limité à une source : deux médias qui reprennent une même dépêche doivent rester visibles
    (utile pour comparer la couverture d'un événement)."""
    since = datetime.now(timezone.utc) - timedelta(days=30)
    return db.scalar(select(News.id).where(News.source_id == source_id, News.content_hash == chash,
                                           News.collected_at >= since).limit(1)) is not None


def build_news(source_id: int, raw: RawArticle, page: ExtractedPage | None, full_text: str | None) -> News | None:
    """Fusionne les infos du flux et de la page. Retourne None si l'article est inexploitable (pas de titre)."""
    title = (raw.title or (page.title if page else None) or "").strip()
    if not title:
        return None
    published, origin = sane(raw.published_at), "feed"
    if published is None and page is not None:
        published, origin = sane(page.published_at), "page"
    if published is None:
        origin = "unknown"       # jamais remplacé par la date de collecte

    canonical = raw.url
    if page and page.canonical_url and same_site(page.canonical_url, raw.url):
        canonical = page.canonical_url
    text = full_text or None
    excerpt = raw.excerpt or (truncate(text, 500) if text else None)
    return News(
        source_id=source_id, title=title[:1000], url=raw.url, canonical_url=canonical,
        url_hash=url_hash(canonical), content_hash=content_hash(title, text or excerpt),
        content_text=text, content_is_partial=not text or len(text) < PARTIAL_BELOW,
        excerpt=excerpt, author=(raw.author or (page.author if page else None)),
        image_url=raw.image_url or (page.image_url if page else None),
        published_at=published, published_at_origin=origin,
        processing_status="extracted" if text else "collected",
    )


def save_news(db: Session, news: News) -> bool:
    """True si inséré ; False si doublon (course entre deux passages)."""
    db.add(news)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False

"""Connecteur RSS/Atom (feedparser). Source privilégiée : stable, légère, prévue pour la syndication."""
import logging
from urllib.parse import urljoin

import feedparser

from app.core.config import settings
from app.scrapers.base import CollectError, PoliteClient, RawArticle
from app.utils.dates import from_struct
from app.utils.text import clean, strip_html, truncate

log = logging.getLogger(__name__)


def _image(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key, []) or []:
            if m.get("url"):
                return m["url"]
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("image/") and enc.get("href"):
            return enc["href"]
    for link in entry.get("links", []) or []:
        if str(link.get("type", "")).startswith("image/") and link.get("href"):
            return link["href"]
    return None


def parse_feed(content: bytes, base_url: str) -> list[RawArticle]:
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise CollectError("Flux illisible ou invalide (ce n'est pas du RSS/Atom)")
    out: list[RawArticle] = []
    for e in parsed.entries:
        link = e.get("link")
        if not link:
            continue
        body_html = None
        if e.get("content"):
            body_html = e["content"][0].get("value")
        summary_text = strip_html(e.get("summary") or e.get("description"))
        full_text = strip_html(body_html) if body_html else ""
        out.append(RawArticle(
            url=urljoin(base_url, link),
            title=clean(e.get("title")) or None,
            excerpt=truncate(summary_text or full_text, 500) or None,
            content_html=body_html if len(full_text) > 600 else None,
            author=clean(e.get("author")) or None,
            published_at=from_struct(e.get("published_parsed") or e.get("updated_parsed")),
            image_url=_image(e),
        ))
    return out


def fetch_rss(client: PoliteClient, feed_url: str, *, etag=None, last_modified=None):
    """Retourne (articles | None si 304, etag, last_modified)."""
    res = client.get(feed_url, etag=etag, last_modified=last_modified)
    if res.not_modified:
        return None, etag, last_modified
    articles = parse_feed(res.content, feed_url)[: settings.max_articles_per_run]
    return articles, res.headers.get("etag"), res.headers.get("last-modified")

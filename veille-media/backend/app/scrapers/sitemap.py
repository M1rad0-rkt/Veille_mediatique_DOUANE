"""Connecteur sitemap (sitemap d'actualités ou sitemap classique triés par date de modification)."""
import logging
import xml.etree.ElementTree as ET

from app.core.config import settings
from app.scrapers.base import CollectError, PoliteClient, RawArticle
from app.utils.dates import parse_date

log = logging.getLogger(__name__)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse(xml_bytes: bytes):
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise CollectError(f"Sitemap XML invalide : {e}") from e
    return _local(root.tag), root


def _urls(root):
    for node in root:
        d = {_local(c.tag): (c.text or "").strip() for c in node.iter() if c is not node}
        yield d


def fetch_sitemap(client: PoliteClient, sitemap_url: str, selectors: dict | None) -> list[RawArticle]:
    contains = (selectors or {}).get("url_contains")
    kind, root = _parse(client.get(sitemap_url).content)
    if kind == "sitemapindex":  # on suit les 2 sitemaps les plus récents seulement
        children = sorted(_urls(root), key=lambda d: d.get("lastmod", ""), reverse=True)[:2]
        entries = []
        for child in children:
            if child.get("loc"):
                k, r = _parse(client.get(child["loc"]).content)
                if k == "urlset":
                    entries.extend(_urls(r))
    else:
        entries = list(_urls(root))
    items = []
    for d in entries:
        url = d.get("loc")
        if not url or (contains and contains not in url):
            continue
        dt = parse_date(d.get("publication_date") or d.get("lastmod"))
        items.append(RawArticle(url=url, title=d.get("title") or None,
                                published_at=None,                      # la vraie date vient de la page
                                extra={"sitemap_date": dt}))
    items.sort(key=lambda a: a.extra["sitemap_date"].timestamp() if a.extra.get("sitemap_date") else 0,
               reverse=True)
    if not items:
        raise CollectError("Sitemap sans URL exploitable")
    return items[: settings.max_articles_per_run]

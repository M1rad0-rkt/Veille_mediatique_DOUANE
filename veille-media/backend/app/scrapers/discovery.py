"""Découverte et diagnostic d'une source : robots.txt, flux RSS déclarés, chemins usuels, sitemaps.
Aucune hypothèse sur un site : on teste réellement et on rapporte ce qui a été trouvé."""
import logging
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.scrapers.base import CollectError, PoliteClient
from app.scrapers.rss import parse_feed

log = logging.getLogger(__name__)
COMMON_FEED_PATHS = ("/feed", "/feed/", "/rss", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml", "/?feed=rss2")
COMMON_SITEMAPS = ("/news-sitemap.xml", "/sitemap_news.xml", "/sitemap.xml", "/sitemap_index.xml")


@dataclass
class ProbeReport:
    base_url: str
    robots_ok: bool | None = None
    feed_url: str | None = None
    feed_items: int = 0
    sitemap_url: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def recommended_type(self) -> str | None:
        if self.feed_url:
            return "rss"
        if self.sitemap_url:
            return "sitemap"
        return None


def _try_feed(client: PoliteClient, url: str) -> int:
    try:
        res = client.get(url, retries=0)
        return len(parse_feed(res.content, url))
    except CollectError:
        return 0


def probe_source(client: PoliteClient, base_url: str) -> ProbeReport:
    rep = ProbeReport(base_url=base_url)
    origin = f"{urlsplit(base_url).scheme}://{urlsplit(base_url).netloc}"
    try:
        rep.robots_ok = client.allowed(base_url)
        if not rep.robots_ok:
            rep.notes.append("robots.txt interdit l'accès à la page d'accueil : ne pas collecter sans autorisation.")
            return rep
    except CollectError as e:
        rep.notes.append(str(e))
        return rep

    candidates: list[str] = []
    try:
        home = client.get(base_url, retries=0)
        soup = BeautifulSoup(home.text, "html.parser")
        for link in soup.find_all("link", rel="alternate"):
            if "rss" in (link.get("type") or "") or "atom" in (link.get("type") or ""):
                candidates.append(urljoin(base_url, link.get("href", "")))
    except CollectError as e:
        rep.notes.append(f"Page d'accueil : {e}")
    candidates += [origin + p for p in COMMON_FEED_PATHS]

    for url in dict.fromkeys(candidates):
        try:
            if not client.allowed(url):
                continue
        except CollectError:
            continue
        n = _try_feed(client, url)
        if n:
            rep.feed_url, rep.feed_items = url, n
            break
    if not rep.feed_url:
        rep.notes.append("Aucun flux RSS/Atom trouvé.")
        for path in COMMON_SITEMAPS:
            url = origin + path
            try:
                if client.allowed(url) and client.get(url, retries=0).content.lstrip().startswith(b"<"):
                    rep.sitemap_url = url
                    break
            except CollectError:
                continue
        rep.notes.append(f"Sitemap trouvé : {rep.sitemap_url}" if rep.sitemap_url
                         else "Aucun sitemap trouvé : configurer un connecteur HTML (sélecteurs) à la main.")
    return rep

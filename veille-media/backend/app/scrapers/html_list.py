"""Connecteur « page de listing » : à utiliser seulement si le site n'a ni RSS ni sitemap.
Configuration (source.selectors) : {"link": "h2 a", "list_url": "https://.../actualites", "url_contains": "/20"}.
Aucun sélecteur par défaut n'est inventé : il doit être vérifié sur le vrai site."""
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.core.config import settings
from app.scrapers.base import CollectError, PoliteClient, RawArticle
from app.utils.urls import normalize_url, same_site


def fetch_listing(client: PoliteClient, base_url: str, selectors: dict | None) -> list[RawArticle]:
    sel = selectors or {}
    if not sel.get("link"):
        raise CollectError("Source HTML sans sélecteur « link » : à configurer dans l'administration")
    page_url = sel.get("list_url") or base_url
    res = client.get(page_url)
    soup = BeautifulSoup(res.text, "html.parser")
    seen, out = set(), []
    for a in soup.select(sel["link"]):
        href = a if isinstance(a, str) else a.get("href")
        if not href and a.name != "a":
            inner = a.find("a")
            href = inner.get("href") if inner else None
        if not href:
            continue
        url = urljoin(page_url, href)
        if not same_site(url, base_url) or (sel.get("url_contains") and sel["url_contains"] not in url):
            continue
        key = normalize_url(url)
        if key in seen:
            continue
        seen.add(key)
        title = a.get_text(" ", strip=True) if a.name == "a" else None
        out.append(RawArticle(url=url, title=title or None))
        if len(out) >= settings.max_articles_per_run:
            break
    if not out:
        raise CollectError("Aucun lien d'article trouvé avec ce sélecteur (le site a peut-être changé)")
    return out

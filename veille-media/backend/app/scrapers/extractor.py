"""Extraction du texte et des métadonnées d'une page article (Trafilatura + balises meta)."""
import json
import logging
from dataclasses import dataclass
from datetime import datetime

from bs4 import BeautifulSoup

from app.utils.dates import parse_date
from app.utils.text import clean

log = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    title: str | None = None
    text: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    image_url: str | None = None
    canonical_url: str | None = None


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return clean(tag["content"])
    return None


def _jsonld(soup: BeautifulSoup) -> dict:
    """Premier objet NewsArticle/Article des blocs JSON-LD (datePublished, author, image)."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (ValueError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            obj = stack.pop()
            if isinstance(obj, dict):
                if "@graph" in obj:
                    stack.extend(obj["@graph"])
                t = obj.get("@type")
                t = t if isinstance(t, list) else [t]
                if any(x in ("NewsArticle", "Article", "ReportageNewsArticle", "BlogPosting") for x in t):
                    return obj
    return {}


def _trafilatura(html: str, url: str):
    try:
        import trafilatura
        doc = trafilatura.bare_extraction(html, url=url, with_metadata=True, favor_precision=True,
                                          include_comments=False, include_tables=False)
    except Exception as e:  # extraction best-effort : ne jamais faire échouer la collecte
        log.warning("Trafilatura a échoué sur %s : %s", url, e)
        return None
    return doc


def _get(doc, key):
    if doc is None:
        return None
    return doc.get(key) if isinstance(doc, dict) else getattr(doc, key, None)


def extract_page(html: str, url: str) -> ExtractedPage:
    soup = BeautifulSoup(html, "html.parser")
    ld = _jsonld(soup)
    doc = _trafilatura(html, url)

    canonical = None
    link = soup.find("link", rel="canonical")
    if link and link.get("href"):
        canonical = link["href"].strip()

    ld_author = ld.get("author")
    if isinstance(ld_author, list):
        ld_author = ld_author[0] if ld_author else None
    if isinstance(ld_author, dict):
        ld_author = ld_author.get("name")
    ld_image = ld.get("image")
    if isinstance(ld_image, list):
        ld_image = ld_image[0] if ld_image else None
    if isinstance(ld_image, dict):
        ld_image = ld_image.get("url")

    date_raw = (_meta(soup, "article:published_time", "og:article:published_time", "datePublished", "date")
                or ld.get("datePublished") or _get(doc, "date"))
    title = _meta(soup, "og:title") or _get(doc, "title") or (soup.title.string.strip() if soup.title and soup.title.string else None)
    text = _get(doc, "text")
    return ExtractedPage(
        title=clean(title) or None,
        text=clean(text) if text else None,
        author=clean(_get(doc, "author") or ld_author or _meta(soup, "author")) or None,
        published_at=parse_date(str(date_raw)) if date_raw else None,
        image_url=_meta(soup, "og:image", "twitter:image") or ld_image or _get(doc, "image"),
        canonical_url=canonical,
    )

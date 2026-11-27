"""Nettoyage de texte et empreinte de contenu (niveau 2 du dédoublonnage)."""
import hashlib
import html
import re
import unicodedata

from bs4 import BeautifulSoup

_WS = re.compile(r"\s+")


def strip_html(raw: str | None) -> str:
    if not raw:
        return ""
    text = BeautifulSoup(raw, "html.parser").get_text(" ")
    return _WS.sub(" ", html.unescape(text)).strip()


def clean(text: str | None) -> str:
    return _WS.sub(" ", html.unescape(text or "")).strip()


def truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-")
    return cut + "…"


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def content_hash(title: str, body: str | None) -> str:
    """Titre + début du texte, sans accents ni ponctuation : détecte un article republié sous une autre URL."""
    return hashlib.sha256(f"{_fold(title)}|{_fold(body or '')[:200]}".encode()).hexdigest()

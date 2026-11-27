"""Normalisation d'URL et empreintes de dédoublonnage (niveau 1 : URL canonique)."""
import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|mc_cid|mc_eid|igshid|ref|ref_src|at_.*|xtor|share|amp)$", re.I)
_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_url(url: str) -> str:
    """URL stable : schéma/hôte en minuscules, sans fragment, sans paramètres de suivi,
    paramètres triés, sans « / » final, sans « www. » (même article quelle que soit l'écriture)."""
    parts = urlsplit(url.strip())
    scheme = (parts.scheme or "https").lower()
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if parts.port and parts.port != _DEFAULT_PORTS.get(scheme):
        host = f"{host}:{parts.port}"
    query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                             if not _TRACKING.match(k)))
    path = re.sub(r"/{2,}", "/", parts.path or "/")
    if len(path) > 1:
        path = path.rstrip("/")
    return urlunsplit((scheme, host, path, query, ""))


def same_site(a: str, b: str) -> bool:
    host = lambda u: (urlsplit(u).hostname or "").lower().removeprefix("www.")
    return host(a) == host(b) and host(a) != ""


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode()).hexdigest()

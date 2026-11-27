"""Briques communes : client HTTP poli (robots.txt, délais, taille max) et objet RawArticle.

Principes : on ne contourne jamais une protection (403/429/challenge => la source passe en erreur),
on respecte robots.txt, on s'identifie par un User-Agent clair, on espace les requêtes.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)
MAX_BYTES = 5 * 1024 * 1024


class CollectError(Exception):
    """Échec de collecte avec un message lisible par l'administrateur."""


class RobotsDisallowed(CollectError):
    pass


@dataclass
class RawArticle:
    """Ce qu'un connecteur sait d'un article avant extraction complète."""
    url: str
    title: str | None = None
    excerpt: str | None = None
    content_html: str | None = None          # contenu intégral fourni par le flux, s'il existe
    author: str | None = None
    published_at: datetime | None = None
    image_url: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass
class FetchResult:
    status: int
    content: bytes
    text: str
    headers: httpx.Headers
    not_modified: bool = False


class PoliteClient:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(
            headers={"User-Agent": settings.user_agent, "Accept-Language": "fr,mg;q=0.8,en;q=0.5"},
            timeout=settings.http_timeout_seconds, follow_redirects=True, transport=transport)
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_hit: dict[str, float] = {}

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ---- robots.txt ----
    def _robots_for(self, url: str) -> RobotFileParser | None:
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin in self._robots:
            return self._robots[origin]
        rp: RobotFileParser | None = RobotFileParser()
        try:
            r = self._client.get(f"{origin}/robots.txt")
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            elif 400 <= r.status_code < 500:
                rp.parse([])                       # pas de robots.txt : tout est permis
            else:
                raise CollectError(f"robots.txt indisponible (HTTP {r.status_code}) : collecte différée")
        except httpx.HTTPError as e:
            raise CollectError(f"robots.txt injoignable ({type(e).__name__}) : collecte différée") from e
        self._robots[origin] = rp
        return rp

    def allowed(self, url: str) -> bool:
        rp = self._robots_for(url)
        return rp is None or rp.can_fetch(settings.user_agent, url)

    # ---- requêtes ----
    def _wait(self, host: str) -> None:
        delta = time.monotonic() - self._last_hit.get(host, 0.0)
        if delta < settings.http_delay_seconds:
            time.sleep(settings.http_delay_seconds - delta)
        self._last_hit[host] = time.monotonic()

    def get(self, url: str, *, etag: str | None = None, last_modified: str | None = None,
            check_robots: bool = True, retries: int = 2) -> FetchResult:
        if check_robots and not self.allowed(url):
            raise RobotsDisallowed(f"robots.txt interdit la collecte de {url}")
        headers = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        host = urlsplit(url).netloc
        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            self._wait(host)
            try:
                with self._client.stream("GET", url, headers=headers) as r:
                    if r.status_code == 304:
                        return FetchResult(304, b"", "", r.headers, not_modified=True)
                    if r.status_code in (401, 403, 429) or r.status_code == 503 and "cf-ray" in r.headers:
                        # Protection ou limitation : on s'arrête, on ne contourne pas.
                        raise CollectError(f"Accès refusé ou limité par le site (HTTP {r.status_code})")
                    if r.status_code >= 500:
                        raise httpx.HTTPStatusError("server error", request=r.request, response=r)
                    if r.status_code >= 400:
                        raise CollectError(f"HTTP {r.status_code} pour {url}")
                    chunks, size = [], 0
                    for chunk in r.iter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise CollectError("Réponse trop volumineuse")
                        chunks.append(chunk)
                    data = b"".join(chunks)
                    r.encoding = r.encoding or "utf-8"
                    return FetchResult(r.status_code, data, data.decode(r.encoding, errors="replace"), r.headers)
            except (httpx.TransportError, httpx.HTTPStatusError) as e:
                last_exc = e
                time.sleep(2 ** attempt)
        raise CollectError(f"Site injoignable après {retries + 1} essais ({type(last_exc).__name__})")

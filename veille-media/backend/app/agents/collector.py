"""Agent de collecte : une passe sur une source (liste -> doublons -> extraction -> enregistrement -> journal)."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CollectionLog, News, Source
from app.scrapers.base import CollectError, PoliteClient, RawArticle, RobotsDisallowed
from app.scrapers.discovery import probe_source
from app.scrapers.extractor import ExtractedPage, extract_page
from app.scrapers.html_list import fetch_listing
from app.scrapers.rss import fetch_rss, parse_feed
from app.scrapers.sitemap import fetch_sitemap
from app.services import ingest
from app.utils.urls import normalize_url, url_hash

log = logging.getLogger(__name__)
MAX_FAILURE_BACKOFF = 3   # intervalle x2, x4, x8 au maximum après des échecs consécutifs


def claim_source(db: Session, source_id: int) -> bool:
    """Passe la source en « collecting » de façon atomique ; False si une autre passe la traite déjà."""
    res = db.execute(update(Source).where(Source.id == source_id, Source.status != "collecting")
                     .values(status="collecting"))
    db.commit()
    return res.rowcount == 1


def is_due(db: Session, source: Source, now: datetime | None = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if not source.is_active or source.status == "collecting":
        return False
    last = db.scalar(select(CollectionLog.started_at).where(CollectionLog.source_id == source.id)
                     .order_by(CollectionLog.started_at.desc()).limit(1))
    if last is None:
        return True
    factor = 2 ** min(source.consecutive_failures, MAX_FAILURE_BACKOFF)
    return now - last >= timedelta(minutes=source.interval_minutes * factor)


def _list_candidates(client: PoliteClient, source: Source) -> tuple[list[RawArticle] | None, dict]:
    """Retourne (articles, mises à jour de la source). articles=None => rien de nouveau (HTTP 304)."""
    updates: dict = {}
    if source.type == "rss":
        feed_url = source.feed_url
        if not feed_url:
            report = probe_source(client, source.base_url)
            updates["robots_ok"] = report.robots_ok
            if not report.feed_url:
                raise CollectError("Aucun flux RSS trouvé : changer le type de source ou renseigner feed_url. "
                                   + " ".join(report.notes))
            feed_url = updates["feed_url"] = report.feed_url
        articles, etag, lm = fetch_rss(client, feed_url, etag=source.etag, last_modified=source.last_modified)
        updates.update(etag=etag, last_modified=lm)
        return articles, updates
    if source.type == "sitemap":
        return fetch_sitemap(client, source.feed_url or source.base_url.rstrip("/") + "/sitemap.xml",
                             source.selectors), updates
    if source.type == "html":
        return fetch_listing(client, source.base_url, source.selectors), updates
    raise CollectError(f"Type de source « {source.type} » non pris en charge (Playwright n'est pas activé : "
                       "à n'ajouter que si le site l'exige ET que la collecte est autorisée)")


def _needs_page(source: Source, raw: RawArticle) -> bool:
    if not settings.fetch_full_content:
        return source.type != "rss"          # html/sitemap n'ont rien d'autre
    if source.type != "rss":
        return True
    return raw.content_html is None          # RSS avec texte intégral : pas besoin de la page


def _enrich_from_page(client: PoliteClient, raw: RawArticle):
    """Télécharge la page article. Retourne (page, texte, erreur?)."""
    try:
        res = client.get(raw.url)
    except RobotsDisallowed:
        return None, None, False             # interdit : on garde ce que le flux a fourni, ce n'est pas une erreur
    except CollectError as e:
        log.warning("Page non récupérée %s : %s", raw.url, e)
        return None, None, True
    page = extract_page(res.text, raw.url)
    return page, page.text, False


def collect_source(db: Session, source_id: int, client: PoliteClient | None = None) -> CollectionLog:
    source = db.get(Source, source_id)
    log_row = CollectionLog(source_id=source_id, status="running")
    db.add(log_row)
    db.commit()
    own_client = client is None
    client = client or PoliteClient()
    found = new = dups = errors = 0
    status, message = "success", None
    updates: dict = {}
    try:
        candidates, updates = _list_candidates(client, source)
        if candidates is None:
            message = "Flux inchangé depuis la dernière collecte (HTTP 304)"
            candidates = []
        found = len(candidates)
        hashes = {c.url: url_hash(c.url) for c in candidates}
        known = ingest.existing_hashes(db, list(hashes.values()))
        for raw in candidates:
            if hashes[raw.url] in known:
                dups += 1
                continue
            try:
                page = text = None
                if raw.content_html:
                    from app.utils.text import strip_html
                    text = strip_html(raw.content_html)
                if _needs_page(source, raw):
                    page, page_text, failed = _enrich_from_page(client, raw)
                    errors += failed
                    text = page_text or text
                news = ingest.build_news(source.id, raw, page, text)
                if news is None:
                    errors += 1
                    continue
                if news.url_hash in known or ingest.is_republished(db, source.id, news.content_hash):
                    dups += 1
                    continue
                if ingest.save_news(db, news):
                    new += 1
                    known.add(news.url_hash)
                else:
                    dups += 1
            except Exception:   # un article défaillant ne doit pas arrêter la passe
                log.exception("Erreur sur l'article %s", raw.url)
                db.rollback()
                errors += 1
        if errors and not new and found:
            status = "error"
        elif errors:
            status = "partial"
        source = db.get(Source, source_id)
        for k, v in updates.items():
            setattr(source, k, v)
        source.status, source.last_error = "idle", None
        if status != "error":
            source.last_success_at, source.consecutive_failures = datetime.now(timezone.utc), 0
        else:
            source.consecutive_failures += 1
            source.status, source.last_error = "error", f"{errors} article(s) en échec sur {found}"
    except CollectError as e:
        status, message, errors = "error", str(e), errors + 1
        db.rollback()
        source = db.get(Source, source_id)
        for k, v in updates.items():
            setattr(source, k, v)
        source.status, source.last_error = "error", str(e)[:1000]
        source.consecutive_failures += 1
        if isinstance(e, RobotsDisallowed):
            source.robots_ok = False
    except Exception as e:   # bug imprévu : on journalise, la source passe en erreur
        log.exception("Collecte de la source %s interrompue", source_id)
        status, message, errors = "error", f"Erreur interne : {type(e).__name__}: {e}", errors + 1
        db.rollback()
        source = db.get(Source, source_id)
        source.status, source.last_error = "error", message[:1000]
        source.consecutive_failures += 1
    finally:
        if own_client:
            client.close()
    log_row = db.get(CollectionLog, log_row.id)
    log_row.ended_at, log_row.status = datetime.now(timezone.utc), status
    log_row.found, log_row.new, log_row.duplicates, log_row.errors = found, new, dups, errors
    log_row.message = message
    db.commit()
    log.info("Source %s : %s (trouvés=%s, nouveaux=%s, doublons=%s, erreurs=%s)",
             source.name, status, found, new, dups, errors)
    return log_row


def recover_stale(db: Session) -> None:
    """Au démarrage du worker : une passe « en cours » est forcément orpheline."""
    db.execute(update(Source).where(Source.status == "collecting").values(status="idle"))
    db.execute(update(CollectionLog).where(CollectionLog.status == "running")
               .values(status="error", ended_at=datetime.now(timezone.utc), message="Interrompu (redémarrage)"))
    db.commit()

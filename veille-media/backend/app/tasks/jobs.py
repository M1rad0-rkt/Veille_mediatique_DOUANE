"""Tâches planifiées du worker. Chaque fonction ouvre sa propre session et ne lève jamais d'exception."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.agents.collector import claim_source, collect_source, is_due, recover_stale
from app.ai import ai_info, get_provider
from app.database.session import SessionLocal
from app.models import AgentRequest, AppSetting, Source
from app.scrapers.base import PoliteClient
from app.services.enrichment import process_pending

log = logging.getLogger(__name__)


def heartbeat() -> None:
    with SessionLocal() as db:
        value = datetime.now(timezone.utc).isoformat()
        row = db.get(AppSetting, "worker_heartbeat")
        if row:
            row.value = value
        else:
            db.add(AppSetting(key="worker_heartbeat", value=value))
        db.commit()


def _collect(source_ids: list[int]) -> None:
    with PoliteClient() as client:
        for sid in source_ids:
            with SessionLocal() as db:
                if claim_source(db, sid):
                    collect_source(db, sid, client)


def collect_due() -> None:
    try:
        with SessionLocal() as db:
            due = [s.id for s in db.scalars(select(Source).where(Source.is_active).order_by(Source.id)) if is_due(db, s)]
        if due:
            _collect(due)
    except Exception:
        log.exception("collect_due a échoué")


def handle_requests() -> None:
    """Consomme les demandes manuelles postées par l'API (bouton « Collecter maintenant »)."""
    try:
        with SessionLocal() as db:
            reqs = db.scalars(select(AgentRequest).where(AgentRequest.claimed_at.is_(None))
                              .order_by(AgentRequest.id).with_for_update(skip_locked=True)).all()
            for r in reqs:
                r.claimed_at = datetime.now(timezone.utc)
            db.commit()
            collect_ids, process = [], False
            for r in reqs:
                if r.kind == "process":
                    process = True
                elif r.source_id:
                    collect_ids.append(r.source_id)
                else:
                    collect_ids += list(db.scalars(select(Source.id).where(Source.is_active)))
        if collect_ids:
            _collect(list(dict.fromkeys(collect_ids)))
        if process:
            process_ai()
    except Exception:
        log.exception("handle_requests a échoué")


def process_ai() -> None:
    try:
        if get_provider() is None:
            return
        with SessionLocal() as db:
            n = process_pending(db)
            if n:
                log.info("IA : %s article(s) traité(s)", n)
    except Exception:
        log.exception("process_ai a échoué")


def startup() -> None:
    with SessionLocal() as db:
        recover_stale(db)
    info = ai_info()
    if not info["configured"]:
        log.warning("IA non configurée (AI_PROVIDER=%s) : la collecte fonctionne, mais aucun résumé ni "
                    "classement ne sera produit tant que la clé n'est pas renseignée dans .env", info["provider"])
    else:
        log.info("IA : %s / %s", info["provider"], info["model"])

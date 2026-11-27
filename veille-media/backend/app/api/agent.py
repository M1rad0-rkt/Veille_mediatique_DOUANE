from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from app.ai import ai_info
from app.api.admin import query_logs
from app.core.deps import AdminUser, DbSession
from app.models import AgentRequest, AppSetting, News, Source
from app.schemas.admin import (AgentSourceStatus, AgentStatusOut, AiInfo, CollectionLogOut, CollectRequestIn)

router = APIRouter(prefix="/agent", tags=["agent"])


@router.get("/status", response_model=AgentStatusOut)
def agent_status(db: DbSession, _admin: AdminUser):
    """État de chaque source : active, en cours de collecte, erreur, dernière collecte réussie."""
    sources = db.scalars(select(Source).order_by(Source.name)).all()
    hb = db.get(AppSetting, "worker_heartbeat")
    seen = datetime.fromisoformat(hb.value) if hb and hb.value else None
    return AgentStatusOut(
        sources=[AgentSourceStatus.model_validate(s, from_attributes=True) for s in sources],
        worker_last_seen=seen,
        worker_alive=bool(seen and datetime.now(timezone.utc) - seen < timedelta(minutes=2)),
        pending_requests=db.scalar(select(func.count()).select_from(AgentRequest)
                                   .where(AgentRequest.claimed_at.is_(None))) or 0,
        pending_ai=db.scalar(select(func.count()).select_from(News).where(
            News.processing_status.in_(["collected", "extracted"]))) or 0,
        ai=AiInfo(**ai_info()))


@router.post("/collect", status_code=202)
def trigger_collect(body: CollectRequestIn, db: DbSession, admin: AdminUser):
    """Demande une collecte immédiate : le worker la prend en charge dans les secondes qui suivent."""
    if body.source_id is not None and not db.get(Source, body.source_id):
        raise HTTPException(404, "Source introuvable")
    req = AgentRequest(kind="collect", source_id=body.source_id, requested_by=admin.id)
    db.add(req)
    db.commit()
    return {"request_id": req.id, "message": "Collecte demandée"}


@router.post("/process", status_code=202)
def trigger_process(db: DbSession, admin: AdminUser):
    """Demande un passage immédiat du traitement IA (classification + résumés)."""
    req = AgentRequest(kind="process", requested_by=admin.id)
    db.add(req)
    db.commit()
    return {"request_id": req.id, "message": "Traitement IA demandé"}


@router.get("/logs", response_model=list[CollectionLogOut])
def agent_logs(db: DbSession, _admin: AdminUser, source_id: int | None = None, status: str | None = None,
               page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    return query_logs(db, source_id, status, page, page_size)

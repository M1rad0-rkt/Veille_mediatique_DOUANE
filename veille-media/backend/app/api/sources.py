from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.models import News, Source
from app.schemas.admin import ProbeOut
from app.schemas.source import SourceCreate, SourceOut, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("", response_model=list[SourceOut])
def list_sources(db: DbSession, _user: CurrentUser):
    return db.scalars(select(Source).order_by(Source.name)).all()


@router.post("", response_model=SourceOut, status_code=201)
def create_source(body: SourceCreate, db: DbSession, _admin: AdminUser):
    src = Source(**body.model_dump())
    db.add(src)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Une source porte déjà ce nom")
    return src


@router.put("/{source_id}", response_model=SourceOut)
def update_source(source_id: int, body: SourceUpdate, db: DbSession, _admin: AdminUser):
    src = db.get(Source, source_id)
    if not src:
        raise HTTPException(404, "Source introuvable")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(src, k, v)
    if data.get("is_active") is True and src.status == "error":
        src.status, src.consecutive_failures = "idle", 0  # réactivation = nouveau départ
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Une source porte déjà ce nom")
    return src


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: DbSession, _admin: AdminUser):
    src = db.get(Source, source_id)
    if not src:
        raise HTTPException(404, "Source introuvable")
    if db.scalar(select(func.count()).select_from(News).where(News.source_id == source_id)):
        raise HTTPException(409, "Cette source a des articles : désactivez-la plutôt que de la supprimer")
    db.delete(src)
    db.commit()


@router.post("/{source_id}/probe", response_model=ProbeOut)
def probe(source_id: int, db: DbSession, _admin: AdminUser, apply: bool = False):
    """Diagnostic réel du site (robots.txt, flux RSS, sitemap). Avec apply=true, configure la source."""
    from app.scrapers.base import PoliteClient
    from app.scrapers.discovery import probe_source
    src = db.get(Source, source_id)
    if not src:
        raise HTTPException(404, "Source introuvable")
    with PoliteClient() as client:
        rep = probe_source(client, src.base_url)
    applied = False
    if apply:
        src.robots_ok = rep.robots_ok
        if rep.robots_ok and rep.recommended_type:
            src.type, src.feed_url, src.is_active = rep.recommended_type, rep.feed_url or rep.sitemap_url, True
            src.status, src.consecutive_failures, src.last_error = "idle", 0, None
            applied = True
        db.commit()
    return ProbeOut(robots_ok=rep.robots_ok, feed_url=rep.feed_url, feed_items=rep.feed_items,
                    sitemap_url=rep.sitemap_url, recommended_type=rep.recommended_type, notes=rep.notes,
                    applied=applied)

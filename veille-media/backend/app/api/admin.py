from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select, update

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.core.security import hash_password
from app.models import AppSetting, CollectionLog, Role, Source, User
from app.schemas.admin import (AdminDashboardOut, CollectionLogOut, DashboardOut, SettingsIn, SettingsOut)
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.dashboard import build_admin_dashboard, build_dashboard
from app.services.users import create_user

router = APIRouter(tags=["admin"])


# ---- Tableau de bord ----
@router.get("/dashboard", response_model=DashboardOut)
def dashboard(db: DbSession, user: CurrentUser):
    """Tableau de bord de l'utilisateur connecté (le compteur « non lus » lui est propre)."""
    return build_dashboard(db, user)


@router.get("/admin/dashboard", response_model=AdminDashboardOut)
def admin_dashboard(db: DbSession, admin: AdminUser):
    return build_admin_dashboard(db, admin)


# ---- Utilisateurs ----
@router.get("/admin/users", response_model=list[UserOut])
def list_users(db: DbSession, _admin: AdminUser):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.post("/admin/users", response_model=UserOut, status_code=201)
def add_user(body: UserCreate, db: DbSession, _admin: AdminUser):
    return create_user(db, body)


@router.patch("/admin/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: UserUpdate, db: DbSession, admin: AdminUser):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    data = body.model_dump(exclude_unset=True)
    if user.id == admin.id and (data.get("is_active") is False or data.get("role") == "user"):
        raise HTTPException(409, "Vous ne pouvez pas vous retirer vos propres droits ou désactiver votre compte")
    if "password" in data:
        user.password_hash = hash_password(data.pop("password"))
    if "role" in data:
        user.role_id = db.scalar(select(Role.id).where(Role.name == data.pop("role")))
    for k, v in data.items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/admin/users/{user_id}", status_code=204)
def delete_user(user_id: int, db: DbSession, admin: AdminUser):
    if user_id == admin.id:
        raise HTTPException(409, "Vous ne pouvez pas supprimer votre propre compte")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Utilisateur introuvable")
    db.delete(user)
    db.commit()


# ---- Journaux de collecte ----
def query_logs(db, source_id: int | None, status: str | None, page: int, page_size: int):
    stmt = (select(CollectionLog, Source.name).join(Source, Source.id == CollectionLog.source_id)
            .order_by(CollectionLog.started_at.desc()))
    if source_id:
        stmt = stmt.where(CollectionLog.source_id == source_id)
    if status:
        stmt = stmt.where(CollectionLog.status == status)
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return [CollectionLogOut(source_name=name, **{c: getattr(log, c) for c in CollectionLogOut.model_fields
                                                  if c != "source_name"}) for log, name in rows]


@router.get("/admin/collection-logs", response_model=list[CollectionLogOut])
def collection_logs(db: DbSession, _admin: AdminUser, source_id: int | None = None, status: str | None = None,
                    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200)):
    return query_logs(db, source_id, status, page, page_size)


# ---- Paramètres de l'application ----
def _interval(db) -> int:
    row = db.get(AppSetting, "default_interval_minutes")
    return int(row.value) if row and row.value else 30


@router.get("/admin/settings", response_model=SettingsOut)
def get_settings(db: DbSession, _admin: AdminUser):
    return SettingsOut(default_interval_minutes=_interval(db))


@router.put("/admin/settings", response_model=SettingsOut)
def put_settings(body: SettingsIn, db: DbSession, _admin: AdminUser):
    """Fréquence de collecte par défaut (nouvelles sources) ; apply_to_all_sources l'impose à toutes les sources."""
    if body.default_interval_minutes is not None:
        row = db.get(AppSetting, "default_interval_minutes")
        if row:
            row.value = body.default_interval_minutes
        else:
            db.add(AppSetting(key="default_interval_minutes", value=body.default_interval_minutes))
        if body.apply_to_all_sources:
            db.execute(update(Source).values(interval_minutes=body.default_interval_minutes))
        db.commit()
    return SettingsOut(default_interval_minutes=_interval(db))

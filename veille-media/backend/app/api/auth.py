from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Cookie, HTTPException, Request, Response, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.deps import AdminUser, CurrentUser, DbSession
from app.core.limiter import limiter
from app.core.security import (DUMMY_HASH, create_access_token, create_refresh_token,
                               decode_token, verify_password)
from app.models import User
from app.schemas.auth import LoginRequest, TokenOut
from app.schemas.user import UserCreate, UserOut
from app.services.users import create_user

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE = "refresh_token"


def _set_refresh_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        REFRESH_COOKIE, create_refresh_token(user_id), httponly=True, secure=settings.cookie_secure,
        samesite="lax", max_age=settings.refresh_token_days * 86400, path="/api/auth")


@router.post("/login", response_model=TokenOut)
@limiter.limit("5/minute")  # limite anti force brute
def login(request: Request, response: Response, body: LoginRequest, db: DbSession):
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    password_ok = verify_password(user.password_hash if user else DUMMY_HASH, body.password)
    if not user or not password_ok or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    _set_refresh_cookie(response, user.id)
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/refresh", response_model=TokenOut)
def refresh(response: Response, db: DbSession, refresh_token: str | None = Cookie(None)):
    try:
        payload = decode_token(refresh_token or "", "refresh")
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée")
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expirée")
    _set_refresh_cookie(response, user.id)  # rotation du cookie
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(REFRESH_COOKIE, path="/api/auth")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: UserCreate, db: DbSession, _admin: AdminUser):
    """Pas d'inscription publique : seul un administrateur crée des comptes."""
    return create_user(db, body)

"""Hachage Argon2 et jetons JWT (access court + refresh en cookie httpOnly)."""
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

_ph = PasswordHasher()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


# Hash factice : on vérifie toujours un mot de passe, même si l'e-mail est inconnu,
# pour ne pas révéler l'existence d'un compte par le temps de réponse.
DUMMY_HASH = hash_password("dummy-password-for-timing")


def create_token(subject: str, kind: str, expires_delta: timedelta) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "type": kind, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: int) -> str:
    return create_token(str(user_id), "access", timedelta(minutes=settings.access_token_minutes))


def create_refresh_token(user_id: int) -> str:
    return create_token(str(user_id), "refresh", timedelta(days=settings.refresh_token_days))


def decode_token(token: str, kind: str) -> dict:
    """Lève jwt.PyJWTError si le jeton est invalide, expiré ou du mauvais type."""
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != kind:
        raise jwt.InvalidTokenError("Mauvais type de jeton")
    return payload

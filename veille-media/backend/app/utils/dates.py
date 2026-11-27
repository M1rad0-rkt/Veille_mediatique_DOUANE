"""Dates de publication : on ne devine jamais. Une date douteuse devient « inconnue »."""
from datetime import datetime, timedelta, timezone
from time import struct_time
from zoneinfo import ZoneInfo

from dateutil import parser as dtparser  # installé avec feedparser/trafilatura via python-dateutil

from app.core.config import settings

_TZ = ZoneInfo(settings.timezone)


def from_struct(t: struct_time | None) -> datetime | None:
    """feedparser fournit des struct_time déjà en UTC."""
    if not t:
        return None
    try:
        return datetime(*t[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def parse_date(value: str | None) -> datetime | None:
    """Parse une date texte. Sans fuseau, on suppose l'heure locale de Madagascar."""
    if not value:
        return None
    try:
        dt = dtparser.parse(value)
    except (ValueError, OverflowError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ)
    return dt.astimezone(timezone.utc)


def sane(dt: datetime | None, now: datetime | None = None) -> datetime | None:
    """Rejette les dates dans le futur (> max_future_days) ou absurdement anciennes."""
    if dt is None:
        return None
    now = now or datetime.now(timezone.utc)
    if dt > now + timedelta(days=settings.max_future_days) or dt.year < 2000:
        return None
    return dt

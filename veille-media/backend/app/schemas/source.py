from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SourceType = Literal["rss", "html", "sitemap", "playwright"]


def _check_url(v: str | None) -> str | None:
    if v is not None and not v.startswith(("http://", "https://")):
        raise ValueError("L'URL doit commencer par http:// ou https://")
    return v


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    base_url: str
    type: str
    feed_url: str | None
    selectors: dict | None
    interval_minutes: int
    is_active: bool
    robots_ok: bool | None
    status: str
    last_success_at: datetime | None
    last_error: str | None
    consecutive_failures: int


class _UrlChecked(BaseModel):
    @field_validator("base_url", "feed_url", check_fields=False)
    @classmethod
    def _urls(cls, v):
        return _check_url(v)


class SourceCreate(_UrlChecked):
    name: str = Field(min_length=2, max_length=120)
    base_url: str
    type: SourceType = "rss"
    feed_url: str | None = None
    selectors: dict | None = None
    interval_minutes: int = Field(default=30, ge=5, le=1440)
    is_active: bool = True



class SourceUpdate(_UrlChecked):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    base_url: str | None = None
    type: SourceType | None = None
    feed_url: str | None = None
    selectors: dict | None = None
    interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    is_active: bool | None = None


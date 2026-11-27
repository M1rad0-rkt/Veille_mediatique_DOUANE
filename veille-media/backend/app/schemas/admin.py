from datetime import date, datetime

from pydantic import BaseModel, Field


class CategoryCount(BaseModel):
    slug: str
    name: str
    color: str
    count: int


class DailyCount(BaseModel):
    day: date
    count: int


class DashboardOut(BaseModel):
    total_news: int
    today_news: int
    unread_news: int
    active_sources: int
    last_sync: datetime | None
    by_category: list[CategoryCount]
    daily_series: list[DailyCount]


class AdminDashboardOut(DashboardOut):
    users_count: int
    sources_in_error: int
    pending_ai: int
    summaries_failed: int


class CollectionLogOut(BaseModel):
    id: int
    source_id: int
    source_name: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    found: int
    new: int
    duplicates: int
    errors: int
    message: str | None


class AiInfo(BaseModel):
    provider: str
    model: str | None
    configured: bool


class AgentStatusOut(BaseModel):
    sources: list["AgentSourceStatus"]
    worker_last_seen: datetime | None = None
    worker_alive: bool = False
    pending_requests: int = 0
    pending_ai: int = 0
    ai: AiInfo


class AgentSourceStatus(BaseModel):
    id: int
    name: str
    is_active: bool
    status: str
    last_success_at: datetime | None
    last_error: str | None
    consecutive_failures: int
    interval_minutes: int


AgentStatusOut.model_rebuild()


class CollectRequestIn(BaseModel):
    source_id: int | None = None   # None = toutes les sources actives


class SettingsOut(BaseModel):
    default_interval_minutes: int


class SettingsIn(BaseModel):
    default_interval_minutes: int | None = Field(default=None, ge=5, le=1440)
    apply_to_all_sources: bool = False


class ProbeOut(BaseModel):
    robots_ok: bool | None
    feed_url: str | None
    feed_items: int
    sitemap_url: str | None
    recommended_type: str | None
    notes: list[str]
    applied: bool

from datetime import datetime

from pydantic import BaseModel, Field


class SourceMini(BaseModel):
    id: int
    name: str


class CategoryTag(BaseModel):
    id: int
    slug: str
    name: str
    color: str
    is_primary: bool
    origin: str
    confidence: float | None = None


class SummaryOut(BaseModel):
    # status = ok | insufficient_content | failed ; si != ok, l'interface affiche
    # « Résumé non disponible » (aucun texte n'est inventé).
    status: str
    summary: str | None = None
    key_points: list[str] | None = None
    entities: dict | None = None


class NewsOut(BaseModel):
    id: int
    title: str
    url: str
    excerpt: str | None
    image_url: str | None
    author: str | None
    published_at: datetime | None      # None => « date non disponible »
    published_at_origin: str
    collected_at: datetime
    sort_date: datetime
    processing_status: str
    source: SourceMini
    categories: list[CategoryTag]
    summary: SummaryOut | None
    is_favorite: bool
    is_read: bool


class NewsDetailOut(NewsOut):
    content_is_partial: bool
    related: list[NewsOut]


class NewsPage(BaseModel):
    items: list[NewsOut]
    total: int
    page: int
    page_size: int
    pages: int


class LatestOut(BaseModel):
    items: list[NewsOut]
    count: int
    server_time: datetime   # à renvoyer comme paramètre `since` au prochain appel


class CategoryAssignment(BaseModel):
    category_ids: list[int] = Field(min_length=1, max_length=5)
    primary_category_id: int

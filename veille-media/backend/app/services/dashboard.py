from datetime import datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Category, News, NewsCategory, NewsSummary, Source, User
from app.schemas.admin import AdminDashboardOut, CategoryCount, DailyCount, DashboardOut
from app.services.news import TZ, _read_exists


def _common(db: Session, user: User) -> dict:
    not_dup = News.duplicate_of_id.is_(None)
    now = datetime.now(TZ)
    today_start = datetime.combine(now.date(), time.min, tzinfo=TZ)
    count = lambda *conds: db.scalar(select(func.count()).select_from(News).where(not_dup, *conds)) or 0

    by_cat = db.execute(
        select(Category.slug, Category.name, Category.color, func.count(News.id))
        .outerjoin(NewsCategory, NewsCategory.category_id == Category.id)
        .outerjoin(News, (News.id == NewsCategory.news_id) & not_dup)
        .where(Category.is_active).group_by(Category.id).order_by(Category.position)).all()

    day = func.date(func.timezone(settings.timezone, News.sort_date))
    since_day = now.date() - timedelta(days=29)
    series_raw = dict(db.execute(
        select(day, func.count()).where(not_dup, day >= since_day).group_by(day)).all())

    return dict(
        total_news=count(),
        today_news=count(News.sort_date >= today_start),
        unread_news=count(~_read_exists(user.id)),
        active_sources=db.scalar(select(func.count()).select_from(Source).where(Source.is_active)) or 0,
        last_sync=db.scalar(select(func.max(Source.last_success_at))),
        by_category=[CategoryCount(slug=s, name=n, color=c, count=k) for s, n, c, k in by_cat],
        # jours sans article inclus (courbe continue)
        daily_series=[DailyCount(day=since_day + timedelta(days=i), count=series_raw.get(since_day + timedelta(days=i), 0))
                      for i in range(30)],
    )


def build_dashboard(db: Session, user: User) -> DashboardOut:
    return DashboardOut(**_common(db, user))


def build_admin_dashboard(db: Session, user: User) -> AdminDashboardOut:
    extra = dict(
        users_count=db.scalar(select(func.count()).select_from(User)) or 0,
        sources_in_error=db.scalar(select(func.count()).select_from(Source).where(Source.status == "error")) or 0,
        pending_ai=db.scalar(select(func.count()).select_from(News).where(
            News.processing_status.in_(["collected", "extracted"]))) or 0,
        summaries_failed=db.scalar(select(func.count()).select_from(NewsSummary).where(
            NewsSummary.status == "failed")) or 0,
    )
    return AdminDashboardOut(**_common(db, user), **extra)

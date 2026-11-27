"""Classification multi-thèmes + résumé fidèle. Le modèle ne décide jamais seul : tout est validé ici."""
import json
import logging
import re
import time
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session, joinedload

from app.ai import get_provider
from app.ai.base import AIProvider, ProviderError, RateLimited
from app.ai.prompts import PROMPT_VERSION, SYSTEM, build_prompt
from app.core.config import settings
from app.models import Category, News, NewsCategory, NewsSummary

log = logging.getLogger(__name__)
RETRY_AFTER = timedelta(minutes=15)
PRIMARY_MIN_CONF = 0.4      # sous ce seuil, la catégorie principale devient « Autres »
SECONDARY_MIN_CONF = 0.5


class _Cat(BaseModel):
    slug: str
    confidence: float = Field(default=0.5, ge=0, le=1)


class _Entities(BaseModel):
    people: list[str] = []
    organizations: list[str] = []
    places: list[str] = []


class AIResult(BaseModel):
    categories: list[_Cat] = Field(min_length=1)
    summary: str | None = None
    key_points: list[str] = []
    entities: _Entities = _Entities()

    @field_validator("key_points", mode="before")
    @classmethod
    def _kp(cls, v):
        return [str(x).strip() for x in (v or []) if str(x).strip()][:5]


def parse_result(raw: str) -> AIResult:
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    try:
        return AIResult.model_validate(json.loads(cleaned))
    except (ValueError, ValidationError) as e:
        raise ProviderError(f"Réponse IA non conforme : {str(e)[:200]}") from e


def grounded_entities(ent: _Entities, source_text: str) -> dict:
    """Garde-fou anti-invention : une entité absente du texte de l'article est supprimée."""
    hay = source_text.lower()
    keep = lambda names: [n.strip() for n in names if n.strip() and n.strip().lower() in hay][:8]
    return {"people": keep(ent.people), "organizations": keep(ent.organizations), "places": keep(ent.places)}


def pick_categories(result: AIResult, valid: dict[str, int], fallback_slug: str = "autres") -> list[tuple[int, bool, float]]:
    """-> [(category_id, is_primary, confidence)] ; slugs inconnus ignorés, seuils appliqués."""
    seen, picked = set(), []
    for c in sorted(result.categories, key=lambda c: -c.confidence):
        if c.slug in valid and c.slug not in seen:
            seen.add(c.slug)
            picked.append(c)
    if not picked or picked[0].confidence < PRIMARY_MIN_CONF:
        return [(valid[fallback_slug], True, picked[0].confidence if picked else 0.0)]
    out = [(valid[picked[0].slug], True, picked[0].confidence)]
    out += [(valid[c.slug], False, c.confidence) for c in picked[1:3] if c.confidence >= SECONDARY_MIN_CONF]
    return out


def _upsert_summary(db: Session, news: News, **vals) -> NewsSummary:
    s = news.summary or NewsSummary(news_id=news.id, status="failed")
    if s not in db:
        db.add(s)
        news.summary = s
    for k, v in vals.items():
        setattr(s, k, v)
    s.updated_at = datetime.now(timezone.utc)
    return s


def enrich_news(db: Session, news: News, provider: AIProvider) -> None:
    """Traite un article. Lève RateLimited (le lot s'arrête) ; les autres erreurs sont enregistrées."""
    cats = db.execute(select(Category.id, Category.slug, Category.name).where(Category.is_active)
                      .order_by(Category.position)).all()
    valid = {slug: cid for cid, slug, _ in cats}
    if "autres" not in valid:
        raise ProviderError("La catégorie de repli « autres » est inactive ou absente")
    body = (news.content_text or news.excerpt or "").strip()
    full = len(news.content_text or "") >= settings.ai_min_content_chars
    text = body[: settings.ai_max_input_chars]
    prompt = build_prompt(
        title=news.title, source=news.source.name,
        published=news.published_at.date().isoformat() if news.published_at else None,
        text=text, categories=[(s, n) for _, s, n in cats], with_summary=full)
    attempts = (news.summary.attempts if news.summary else 0) + 1
    try:
        result = parse_result(provider.generate_json(SYSTEM, prompt))
    except RateLimited:
        raise
    except ProviderError as e:
        give_up = attempts >= settings.ai_max_attempts
        _upsert_summary(db, news, provider=provider.name, model=provider.model, prompt_version=PROMPT_VERSION,
                        status="failed", error=str(e)[:500], attempts=attempts)
        if give_up:
            news.processing_status = "failed"
        db.commit()
        log.warning("IA : échec sur l'article %s (tentative %s) : %s", news.id, attempts, e)
        return

    # Catégories : une correction manuelle n'est jamais écrasée.
    has_manual = db.scalar(select(NewsCategory.news_id).where(NewsCategory.news_id == news.id,
                                                              NewsCategory.origin == "manual").limit(1))
    if not has_manual:
        db.execute(delete(NewsCategory).where(NewsCategory.news_id == news.id))
        for cid, primary, conf in pick_categories(result, valid):
            db.add(NewsCategory(news_id=news.id, category_id=cid, is_primary=primary, confidence=conf, origin="ai"))

    common = dict(provider=provider.name, model=provider.model, prompt_version=PROMPT_VERSION, attempts=attempts)
    if full and result.summary and result.summary.strip():
        _upsert_summary(db, news, status="ok", summary=result.summary.strip(), key_points=result.key_points,
                        entities=grounded_entities(result.entities, f"{news.title}\n{body}"), error=None, **common)
    elif not full:
        _upsert_summary(db, news, status="insufficient_content", summary=None, key_points=None, entities=None,
                        error="Texte disponible trop court pour un résumé fiable", **common)
    else:
        _upsert_summary(db, news, status="failed", summary=None, key_points=None, entities=None,
                        error="Le modèle n'a pas fourni de résumé", **common)
        if attempts >= settings.ai_max_attempts:
            news.processing_status = "failed"
        db.commit()
        return
    news.processing_status = "enriched"
    db.commit()


def pending_ids(db: Session, limit: int) -> list[int]:
    """Articles à traiter, les plus récents d'abord ; les échecs sont retentés après 15 min, 3 fois max."""
    retry_cutoff = datetime.now(timezone.utc) - RETRY_AFTER
    stmt = (select(News.id).outerjoin(NewsSummary, NewsSummary.news_id == News.id)
            .where(News.duplicate_of_id.is_(None), News.processing_status.in_(["collected", "extracted"]),
                   or_(NewsSummary.id.is_(None),
                       and_(NewsSummary.status == "failed", NewsSummary.attempts < settings.ai_max_attempts,
                            NewsSummary.updated_at < retry_cutoff)))
            .order_by(News.sort_date.desc()).limit(limit))
    return list(db.scalars(stmt))


def process_pending(db: Session, limit: int | None = None, provider: AIProvider | None = None,
                    sleep=time.sleep) -> int:
    provider = provider or get_provider()
    if provider is None:
        return 0
    done = 0
    gap = 60.0 / settings.ai_requests_per_minute if settings.ai_requests_per_minute > 0 else 0
    for nid in pending_ids(db, limit or settings.ai_batch_size):
        news = db.scalar(select(News).where(News.id == nid).options(joinedload(News.source)))
        try:
            enrich_news(db, news, provider)
        except RateLimited:
            log.warning("Quota IA atteint : lot interrompu, reprise au prochain passage")
            break
        except Exception:
            log.exception("Erreur inattendue sur l'article %s", nid)
            db.rollback()
        done += 1
        if gap:
            sleep(gap)
    return done

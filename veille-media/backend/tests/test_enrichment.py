import json

import pytest
from sqlalchemy import select

from app.ai.base import ProviderError, RateLimited
from app.models import Category, NewsCategory
from app.services.enrichment import (AIResult, enrich_news, grounded_entities, parse_result, pick_categories,
                                     process_pending)


class FakeProvider:
    name, model = "fake", "fake-1"

    def __init__(self, payload=None, error=None):
        self.payload, self.error, self.calls = payload, error, 0

    def generate_json(self, system, prompt):
        self.calls += 1
        if self.error:
            raise self.error
        return json.dumps(self.payload)


VALID = {"economie-finances": 1, "sante": 2, "autres": 3}
LONG_TEXT = "Le ministre des Finances Jean Rakoto a présenté le budget à Antananarivo. " * 12


def test_parse_result_accepts_code_fences_and_rejects_garbage():
    raw = '```json\n{"categories":[{"slug":"sante","confidence":0.9}],"summary":"Ok."}\n```'
    assert parse_result(raw).categories[0].slug == "sante"
    with pytest.raises(ProviderError):
        parse_result("pas du json")
    with pytest.raises(ProviderError):
        parse_result('{"categories": []}')


def test_pick_categories_applies_thresholds_and_fallback():
    r = AIResult.model_validate({"categories": [{"slug": "economie-finances", "confidence": 0.9},
                                                {"slug": "sante", "confidence": 0.3},
                                                {"slug": "inconnue", "confidence": 0.99}]})
    assert pick_categories(r, VALID) == [(1, True, 0.9)]                  # secondaire < 0.5 ignoré, slug inconnu ignoré
    weak = AIResult.model_validate({"categories": [{"slug": "sante", "confidence": 0.2}]})
    assert pick_categories(weak, VALID)[0][0] == 3                         # confiance faible => « autres »
    nothing = AIResult.model_validate({"categories": [{"slug": "zzz", "confidence": 1}]})
    assert pick_categories(nothing, VALID)[0][0] == 3


def test_entities_not_in_article_are_dropped():
    ent = AIResult.model_validate({"categories": [{"slug": "autres"}],
                                   "entities": {"people": ["Jean Rakoto", "Emmanuel Macron"],
                                                "places": ["Antananarivo"]}}).entities
    out = grounded_entities(ent, LONG_TEXT)
    assert out["people"] == ["Jean Rakoto"] and out["places"] == ["Antananarivo"]   # Macron absent du texte => retiré


def _article(make_news, **kw):
    return make_news("Budget de l'État", content_text=kw.pop("text", LONG_TEXT), processing_status="extracted", **kw)


def test_enrich_ok_writes_summary_and_categories(db, make_news):
    n = _article(make_news)
    p = FakeProvider({"categories": [{"slug": "economie-finances", "confidence": 0.95}],
                      "summary": "Le ministre a présenté le budget.", "key_points": ["Budget présenté"],
                      "entities": {"people": ["Jean Rakoto"], "organizations": [], "places": []}})
    enrich_news(db, n, p)
    db.refresh(n)
    assert n.processing_status == "enriched" and n.summary.status == "ok" and n.summary.provider == "fake"
    link = db.scalars(select(NewsCategory).where(NewsCategory.news_id == n.id)).one()
    assert link.origin == "ai" and link.is_primary


def test_short_content_gets_no_summary(db, make_news):
    n = _article(make_news, text="Trop court.")
    p = FakeProvider({"categories": [{"slug": "sante", "confidence": 0.8}], "summary": "Résumé inventé !"})
    enrich_news(db, n, p)
    db.refresh(n)
    assert n.summary.status == "insufficient_content" and n.summary.summary is None   # aucun résumé affiché
    assert db.scalars(select(NewsCategory).where(NewsCategory.news_id == n.id)).one()  # mais classé


def test_manual_category_is_never_overwritten(db, make_news):
    n = _article(make_news)
    cat = db.scalar(select(Category).where(Category.slug == "sport"))
    db.add(NewsCategory(news_id=n.id, category_id=cat.id, is_primary=True, origin="manual"))
    db.commit()
    enrich_news(db, n, FakeProvider({"categories": [{"slug": "sante", "confidence": 0.9}], "summary": "Ok."}))
    links = db.scalars(select(NewsCategory).where(NewsCategory.news_id == n.id)).all()
    assert [(l.category_id, l.origin) for l in links] == [(cat.id, "manual")]


def test_failures_are_counted_then_given_up(db, make_news):
    n = _article(make_news)
    bad = FakeProvider(error=ProviderError("boom"))
    for _ in range(3):
        enrich_news(db, n, bad)
    db.refresh(n)
    assert n.summary.status == "failed" and n.summary.attempts == 3 and n.processing_status == "failed"


def test_rate_limit_stops_batch_without_penalty(db, make_news):
    for i in range(3):
        _article(make_news)
    p = FakeProvider(error=RateLimited("429"))
    done = process_pending(db, limit=10, provider=p, sleep=lambda s: None)
    assert done == 0 and p.calls == 1                    # le lot s'arrête au premier 429
    assert db.query(NewsCategory).count() == 0

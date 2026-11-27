"""Collecte complète contre un faux serveur HTTP (httpx.MockTransport) et la vraie base PostgreSQL."""
import httpx
import pytest
from sqlalchemy import select

from app.agents.collector import claim_source, collect_source, is_due
from app.models import CollectionLog, News, Source
from app.scrapers.base import PoliteClient
from app.scrapers.rss import parse_feed
from tests.fixtures import FEED, article_page


def _server(robots: str = "", fail_feed: int | None = None):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/robots.txt"):
            return httpx.Response(200, text=robots) if robots else httpx.Response(404)
        if url.endswith("/feed.xml"):
            return httpx.Response(fail_feed or 200, text=FEED)
        if "budget-etat" in url:
            return httpx.Response(200, text=article_page("Le budget de l'État augmente", "Budget"))
        if "match-mahamasina" in url:
            return httpx.Response(200, text=article_page("Match de football à Mahamasina", "Football", date=None))
        if "futur" in url:
            return httpx.Response(200, text=article_page("Article daté du futur", "Futur", date="2035-01-01T00:00:00Z"))
        return httpx.Response(404)
    return PoliteClient(transport=httpx.MockTransport(handler))


@pytest.fixture()
def source(db):
    s = Source(name="Journal test", base_url="https://journal.test/", type="rss", feed_url="https://journal.test/feed.xml")
    db.add(s)
    db.commit()
    return s


def test_parse_feed_reads_real_fields():
    items = parse_feed(FEED.encode(), "https://journal.test/")
    assert len(items) == 3
    first = items[0]
    assert first.title == "Le budget de l'État augmente"
    assert first.excerpt == "Les recettes fiscales progressent."
    assert first.image_url == "https://journal.test/img/budget.jpg"
    assert first.published_at.isoformat() == "2026-11-23T05:30:00+00:00"   # +03:00 converti en UTC
    assert items[1].published_at is None                                     # pas de date => None, rien d'inventé


def test_collect_saves_articles_with_honest_dates(db, source):
    with _server() as client:
        log = collect_source(db, source.id, client)
    assert (log.found, log.new, log.duplicates) == (3, 3, 0) and log.status == "success"
    news = {n.title: n for n in db.scalars(select(News))}
    budget = news["Le budget de l'État augmente"]
    assert budget.published_at_origin == "feed" and budget.content_text and not budget.content_is_partial
    assert budget.url_hash and "utm_source" not in budget.canonical_url
    foot = news["Match de football à Mahamasina"]
    assert foot.published_at is None and foot.published_at_origin == "unknown"   # jamais la date de collecte
    assert foot.collected_at is not None
    future = news["Article daté du futur"]
    assert future.published_at is None                                           # date aberrante rejetée
    db.refresh(source)
    assert source.status == "idle" and source.last_success_at and source.consecutive_failures == 0


def test_second_pass_detects_duplicates(db, source):
    with _server() as client:
        collect_source(db, source.id, client)
        second = collect_source(db, source.id, client)
    assert (second.new, second.duplicates) == (0, 3)
    assert db.query(News).count() == 3


def test_robots_txt_blocks_the_feed(db, source):
    with _server(robots="User-agent: *\nDisallow: /") as client:
        log = collect_source(db, source.id, client)
    db.refresh(source)
    assert log.status == "error" and source.status == "error" and source.robots_ok is False
    assert db.query(News).count() == 0
    assert "robots.txt" in (source.last_error or "")


def test_protected_site_is_not_bypassed(db, source):
    with _server(fail_feed=403) as client:
        log = collect_source(db, source.id, client)
    db.refresh(source)
    assert log.status == "error" and source.consecutive_failures == 1 and "403" in source.last_error


def test_claim_is_exclusive_and_due_logic(db, source):
    assert is_due(db, source)                       # jamais collectée
    assert claim_source(db, source.id) is True
    assert claim_source(db, source.id) is False     # déjà en cours : pas de double collecte
    db.refresh(source)
    assert not is_due(db, source)                   # statut « collecting »
    source.status = "idle"
    db.add(CollectionLog(source_id=source.id, status="success"))
    db.commit()
    assert not is_due(db, source)                   # collectée à l'instant, intervalle de 30 min

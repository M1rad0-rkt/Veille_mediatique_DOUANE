from datetime import datetime, timedelta, timezone

from app.utils.dates import parse_date, sane
from app.utils.text import content_hash, strip_html
from app.utils.urls import normalize_url, url_hash


def test_url_normalization_merges_variants():
    a = "https://www.Journal.test/economie/budget/?utm_source=rss&b=2&a=1#haut"
    b = "http://journal.test/economie/budget?a=1&b=2"
    assert normalize_url(a).endswith("/economie/budget?a=1&b=2")
    assert url_hash("https://www.journal.test/x/") == url_hash("https://journal.test/x")
    assert normalize_url(a).split("?")[0] == "https://journal.test/economie/budget"
    assert normalize_url(b).split("?")[1] == "a=1&b=2"


def test_content_hash_ignores_accents_and_punctuation():
    assert content_hash("Le Budget, de l'État !", "Texte") == content_hash("le budget de l etat", "texte")
    assert content_hash("Titre A", "x") != content_hash("Titre B", "x")


def test_strip_html():
    assert strip_html("<p>Bonjour&nbsp;<b>le</b> monde</p>") == "Bonjour le monde"


def test_parse_date_assumes_local_timezone_and_rejects_nonsense():
    assert parse_date("2026-11-23 08:00").hour == 5          # 08:00 à Madagascar (UTC+3) = 05:00 UTC
    assert parse_date("pas une date") is None


def test_sane_rejects_future_and_ancient_dates():
    now = datetime.now(timezone.utc)
    assert sane(now - timedelta(hours=2)) is not None
    assert sane(now + timedelta(days=30)) is None
    assert sane(datetime(1970, 1, 1, tzinfo=timezone.utc)) is None

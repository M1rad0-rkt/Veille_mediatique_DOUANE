"""Tests d'intégration sur une vraie base PostgreSQL (veille_test, créée par scripts/db-init).
Lancer :  docker compose exec api pytest -q
"""
import os
import uuid

os.environ["RATE_LIMIT_ENABLED"] = "false"          # avant l'import de l'application
os.environ["HTTP_DELAY_SECONDS"] = "0"             # pas de pause entre requêtes dans les tests
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["FIRST_ADMIN_EMAIL"] = "admin@test.local"
os.environ["FIRST_ADMIN_PASSWORD"] = "AdminPassword-123"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.base import Base
from app.database.seed import seed
from app.database.session import SessionLocal, engine, get_db
from app.core.security import hash_password
from app.models import News, Role, Source, User
from main import app


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean():
    yield
    with SessionLocal() as db:
        db.execute(text("TRUNCATE user_favorites, user_read_history, news_categories, news_summaries, "
                        "news, collection_logs, agent_requests, sources RESTART IDENTITY CASCADE"))
        db.commit()


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client():
    return TestClient(app)  # sans context manager : le seed de démarrage n'est pas relancé


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client):
    return _login(client, "admin@test.local", "AdminPassword-123")


@pytest.fixture()
def user_headers(client, db):
    email = f"agent-{uuid.uuid4().hex[:8]}@test.local"
    role = db.query(Role).filter_by(name="user").one()
    db.add(User(email=email, full_name="Agent Test", password_hash=hash_password("UserPassword-123"), role_id=role.id))
    db.commit()
    return _login(client, email, "UserPassword-123")


@pytest.fixture()
def make_news(db):
    source = Source(name=f"Source {uuid.uuid4().hex[:6]}", base_url="https://example.org", type="rss")
    db.add(source)
    db.flush()

    def _make(title, published_at=None, **kw):
        n = News(source_id=source.id, title=title, url=f"https://example.org/{uuid.uuid4().hex}",
                 url_hash=uuid.uuid4().hex + uuid.uuid4().hex[:32], published_at=published_at, **kw)
        db.add(n)
        db.commit()
        return n

    return _make

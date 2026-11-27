from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc)


def test_sorted_by_date_desc_and_missing_date_is_not_faked(client, user_headers, make_news):
    make_news("Ancien", NOW - timedelta(days=3))
    make_news("Récent", NOW - timedelta(hours=1))
    make_news("Sans date")  # published_at NULL
    items = client.get("/api/news", headers=user_headers).json()["items"]
    sans = next(i for i in items if i["title"] == "Sans date")
    assert sans["published_at"] is None                      # jamais remplacé par la date de collecte
    assert sans["sort_date"] is not None                     # utilisé seulement pour le tri
    dated = [i for i in items if i["published_at"]]
    assert [i["title"] for i in dated] == ["Récent", "Ancien"]


def test_pagination(client, user_headers, make_news):
    for i in range(5):
        make_news(f"Article {i}", NOW - timedelta(minutes=i))
    page = client.get("/api/news?page_size=2&page=3", headers=user_headers).json()
    assert page["total"] == 5 and page["pages"] == 3 and len(page["items"]) == 1


def test_search_and_duplicates_hidden(client, user_headers, make_news, db):
    original = make_news("Budget de l'État : hausse des recettes fiscales", NOW)
    dup = make_news("Budget de l'État : hausse des recettes fiscales", NOW)
    dup.duplicate_of_id = original.id
    db.commit()
    make_news("Match de football à Mahamasina", NOW)
    res = client.get("/api/news/search?q=budget", headers=user_headers).json()
    assert res["total"] == 1                                  # le doublon est masqué
    assert client.get("/api/news/search", headers=user_headers).status_code == 422


def test_favorite_and_read_state_per_user(client, user_headers, admin_headers, make_news):
    n = make_news("À lire", NOW)
    assert client.post(f"/api/news/{n.id}/favorite", headers=user_headers).status_code == 204
    assert client.post(f"/api/news/{n.id}/read", headers=user_headers).status_code == 204
    mine = client.get(f"/api/news/{n.id}", headers=user_headers).json()
    assert mine["is_favorite"] and mine["is_read"]
    other = client.get(f"/api/news/{n.id}", headers=admin_headers).json()
    assert not other["is_favorite"] and not other["is_read"]   # état propre à chaque utilisateur
    assert client.get("/api/news?read_status=unread", headers=user_headers).json()["total"] == 0
    assert client.get("/api/news/favorites", headers=user_headers).json()["total"] == 1
    assert client.get("/api/news/history", headers=user_headers).json()["total"] == 1
    client.delete(f"/api/news/{n.id}/read", headers=user_headers)
    assert client.get("/api/news?read_status=unread", headers=user_headers).json()["total"] == 1


def test_manual_category_correction(client, user_headers, admin_headers, make_news):
    n = make_news("Article à classer", NOW)
    cats = client.get("/api/categories", headers=admin_headers).json()
    sante = next(c for c in cats if c["slug"] == "sante")
    body = {"category_ids": [sante["id"]], "primary_category_id": sante["id"]}
    assert client.patch(f"/api/news/{n.id}/category", json=body, headers=user_headers).status_code == 403
    r = client.patch(f"/api/news/{n.id}/category", json=body, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["categories"][0]["slug"] == "sante" and r.json()["categories"][0]["origin"] == "manual"
    assert client.get("/api/news?category=sante", headers=user_headers).json()["total"] == 1
    bad = {"category_ids": [sante["id"]], "primary_category_id": 9999}
    assert client.patch(f"/api/news/{n.id}/category", json=bad, headers=admin_headers).status_code == 422


def test_latest_polling(client, user_headers, make_news):
    make_news("Première", NOW)
    first = client.get("/api/news/latest", headers=user_headers).json()
    assert first["count"] == 1
    again = client.get("/api/news/latest", params={"since": first["server_time"]}, headers=user_headers).json()
    assert again["count"] == 0


def test_dashboard(client, user_headers, admin_headers, make_news):
    make_news("Aujourd'hui", NOW)
    d = client.get("/api/dashboard", headers=user_headers).json()
    assert d["total_news"] == 1 and d["unread_news"] == 1 and len(d["daily_series"]) == 30
    assert client.get("/api/admin/dashboard", headers=admin_headers).json()["users_count"] >= 2


def test_agent_endpoints(client, admin_headers, user_headers):
    assert client.post("/api/agent/collect", json={}, headers=user_headers).status_code == 403
    assert client.get("/api/agent/logs", headers=admin_headers).json() == []
    st = client.get("/api/agent/status", headers=admin_headers).json()
    assert st["worker_alive"] is False and st["pending_requests"] == 0 and "configured" in st["ai"]
    assert client.post("/api/agent/collect", json={"source_id": 9999}, headers=admin_headers).status_code == 404
    ok = client.post("/api/agent/collect", json={}, headers=admin_headers)
    assert ok.status_code == 202                         # mise en file ; le worker l'exécute
    assert client.get("/api/agent/status", headers=admin_headers).json()["pending_requests"] == 1

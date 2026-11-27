def test_default_categories_seeded(client, user_headers):
    cats = client.get("/api/categories", headers=user_headers).json()
    assert len(cats) == 14 and cats[0]["slug"] == "economie-finances"


def test_category_crud_admin_only(client, admin_headers, user_headers):
    body = {"slug": "test-cat", "name": "Test"}
    assert client.post("/api/categories", json=body, headers=user_headers).status_code == 403
    created = client.post("/api/categories", json=body, headers=admin_headers)
    assert created.status_code == 201
    cid = created.json()["id"]
    assert client.post("/api/categories", json=body, headers=admin_headers).status_code == 409
    assert client.put(f"/api/categories/{cid}", json={"name": "Renommée"}, headers=admin_headers).json()["name"] == "Renommée"
    assert client.delete(f"/api/categories/{cid}", headers=admin_headers).status_code == 204


def test_fallback_category_cannot_be_deleted(client, admin_headers):
    cats = client.get("/api/categories", headers=admin_headers).json()
    autres = next(c for c in cats if c["slug"] == "autres")
    assert client.delete(f"/api/categories/{autres['id']}", headers=admin_headers).status_code == 409


def test_source_crud_and_validation(client, admin_headers, user_headers):
    body = {"name": "L'Express de Madagascar", "base_url": "https://www.lexpress.mg/", "type": "rss", "interval_minutes": 30}
    assert client.post("/api/sources", json=body, headers=user_headers).status_code == 403
    created = client.post("/api/sources", json=body, headers=admin_headers)
    assert created.status_code == 201 and created.json()["status"] == "idle"
    sid = created.json()["id"]
    assert client.post("/api/sources", json=body, headers=admin_headers).status_code == 409
    assert client.post("/api/sources", headers=admin_headers, json={**body, "name": "Bad", "base_url": "ftp://x"}).status_code == 422
    assert client.post("/api/sources", headers=admin_headers, json={**body, "name": "Fast", "interval_minutes": 1}).status_code == 422
    assert client.put(f"/api/sources/{sid}", json={"is_active": False}, headers=admin_headers).json()["is_active"] is False
    assert len(client.get("/api/sources", headers=user_headers).json()) == 1
    assert client.delete(f"/api/sources/{sid}", headers=admin_headers).status_code == 204

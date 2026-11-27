def test_login_ok_and_me(client, admin_headers):
    r = client.get("/api/auth/me", headers=admin_headers)
    assert r.status_code == 200 and r.json()["role"] == "admin"


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "mauvais-mot-de-passe"})
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/news").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer abc"}).status_code == 401


def test_refresh_cookie_flow(client):
    client.post("/api/auth/login", json={"email": "admin@test.local", "password": "AdminPassword-123"})
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200 and r.json()["access_token"]


def test_rbac_user_cannot_access_admin(client, user_headers):
    assert client.get("/api/admin/users", headers=user_headers).status_code == 403
    assert client.get("/api/admin/dashboard", headers=user_headers).status_code == 403
    assert client.post("/api/auth/register", headers=user_headers,
                       json={"email": "x@test.local", "full_name": "X Y", "password": "LongPassword-1"}).status_code == 403


def test_admin_creates_user_and_weak_password_rejected(client, admin_headers):
    ok = client.post("/api/admin/users", headers=admin_headers,
                     json={"email": "new@test.local", "full_name": "Nouvel Agent", "password": "LongPassword-1"})
    assert ok.status_code == 201 and ok.json()["role"] == "user"
    dup = client.post("/api/admin/users", headers=admin_headers,
                      json={"email": "NEW@test.local", "full_name": "Autre", "password": "LongPassword-1"})
    assert dup.status_code == 409
    weak = client.post("/api/admin/users", headers=admin_headers,
                       json={"email": "w@test.local", "full_name": "Faible", "password": "court"})
    assert weak.status_code == 422


def test_admin_cannot_delete_self(client, admin_headers):
    me = client.get("/api/auth/me", headers=admin_headers).json()
    assert client.delete(f"/api/admin/users/{me['id']}", headers=admin_headers).status_code == 409

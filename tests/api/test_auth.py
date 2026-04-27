def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"email": "a@test.com", "password": "password123"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    assert r.json()["user"]["email"] == "a@test.com"

    r = client.post("/api/auth/login", json={"email": "a@test.com", "password": "password123"})
    assert r.status_code == 200

    r = client.post("/api/auth/login", json={"email": "a@test.com", "password": "wrong"})
    assert r.status_code == 401

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@test.com"


def test_register_duplicate_email(client):
    client.post("/api/auth/register", json={"email": "dup@test.com", "password": "password123"})
    r = client.post("/api/auth/register", json={"email": "dup@test.com", "password": "password456"})
    assert r.status_code == 409


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401

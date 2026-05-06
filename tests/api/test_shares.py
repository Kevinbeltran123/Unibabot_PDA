"""Tests de los endpoints owner-only de share-links."""

from __future__ import annotations


def _create_analysis(client, auth_headers, sample_pdf) -> str:
    with sample_pdf.open("rb") as f:
        r = client.post(
            "/api/analyses",
            headers=auth_headers,
            files={"file": ("tiny.pdf", f, "application/pdf")},
        )
    assert r.status_code == 202, r.text
    aid = r.json()["id"]
    detail = client.get(f"/api/analyses/{aid}", headers=auth_headers).json()
    assert detail["status"] == "done"
    return aid


def test_create_share_returns_token_once(client, auth_headers, sample_pdf):
    aid = _create_analysis(client, auth_headers, sample_pdf)
    r = client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": 30},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["token"]
    assert body["url"].endswith(body["token"])
    assert body["url"].startswith("http")
    assert body["audience"] == "docente"
    assert body["expires_at"] is not None
    assert body["revoked_at"] is None
    assert body["access_count"] == 0


def test_list_shares_does_not_leak_token(client, auth_headers, sample_pdf):
    aid = _create_analysis(client, auth_headers, sample_pdf)
    client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": 7},
    )
    r = client.get(f"/api/analyses/{aid}/shares", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert "token" not in items[0]
    assert "url" not in items[0]


def test_create_share_rejects_running_analysis(client, auth_headers, sample_pdf):
    """Un analisis sin status=done no debe permitirse compartir."""
    aid = _create_analysis(client, auth_headers, sample_pdf)
    # Forzar status pending mediante DB directa
    from src.api.db import SessionLocal
    from src.api.models import Analysis

    db = SessionLocal()
    try:
        a = db.get(Analysis, aid)
        a.status = "running"
        db.commit()
    finally:
        db.close()

    r = client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": 30},
    )
    assert r.status_code == 409


def test_share_isolation_between_users(client, sample_pdf):
    a = client.post(
        "/api/auth/register", json={"email": "alice@t.com", "password": "password123"}
    ).json()
    b = client.post(
        "/api/auth/register", json={"email": "bob@t.com", "password": "password123"}
    ).json()
    headers_a = {"Authorization": f"Bearer {a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {b['access_token']}"}

    with sample_pdf.open("rb") as f:
        aid = client.post(
            "/api/analyses",
            headers=headers_a,
            files={"file": ("x.pdf", f, "application/pdf")},
        ).json()["id"]
    client.get(f"/api/analyses/{aid}", headers=headers_a)

    # Bob no puede crear share del analisis de Alice
    r = client.post(
        f"/api/analyses/{aid}/share",
        headers=headers_b,
        json={"expires_in_days": 30},
    )
    assert r.status_code == 404

    # Bob no puede listar shares del analisis de Alice
    r = client.get(f"/api/analyses/{aid}/shares", headers=headers_b)
    assert r.status_code == 404


def test_revoke_share(client, auth_headers, sample_pdf):
    aid = _create_analysis(client, auth_headers, sample_pdf)
    created = client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": 30},
    ).json()
    share_id = created["id"]

    r = client.delete(f"/api/shares/{share_id}", headers=auth_headers)
    assert r.status_code == 204

    items = client.get(f"/api/analyses/{aid}/shares", headers=auth_headers).json()
    assert items[0]["revoked_at"] is not None


def test_revoke_share_idempotent(client, auth_headers, sample_pdf):
    aid = _create_analysis(client, auth_headers, sample_pdf)
    created = client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": 30},
    ).json()
    share_id = created["id"]

    r1 = client.delete(f"/api/shares/{share_id}", headers=auth_headers)
    r2 = client.delete(f"/api/shares/{share_id}", headers=auth_headers)
    assert r1.status_code == 204
    assert r2.status_code == 204


def test_revoke_share_other_user_404(client, sample_pdf):
    a = client.post(
        "/api/auth/register", json={"email": "a@t.com", "password": "password123"}
    ).json()
    b = client.post(
        "/api/auth/register", json={"email": "b@t.com", "password": "password123"}
    ).json()
    headers_a = {"Authorization": f"Bearer {a['access_token']}"}
    headers_b = {"Authorization": f"Bearer {b['access_token']}"}

    with sample_pdf.open("rb") as f:
        aid = client.post(
            "/api/analyses",
            headers=headers_a,
            files={"file": ("x.pdf", f, "application/pdf")},
        ).json()["id"]
    client.get(f"/api/analyses/{aid}", headers=headers_a)

    share = client.post(
        f"/api/analyses/{aid}/share",
        headers=headers_a,
        json={"expires_in_days": 30},
    ).json()

    r = client.delete(f"/api/shares/{share['id']}", headers=headers_b)
    assert r.status_code == 404


def test_share_cascade_on_analysis_delete(client, auth_headers, sample_pdf):
    aid = _create_analysis(client, auth_headers, sample_pdf)
    client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": 30},
    )

    # Borrar analisis -> los shares cascadean
    r = client.delete(f"/api/analyses/{aid}", headers=auth_headers)
    assert r.status_code == 204

    from src.api.db import SessionLocal
    from src.api.models import ShareToken

    db = SessionLocal()
    try:
        remaining = (
            db.query(ShareToken).filter(ShareToken.analysis_id == aid).count()
        )
        assert remaining == 0
    finally:
        db.close()


def test_share_no_expiration(client, auth_headers, sample_pdf):
    aid = _create_analysis(client, auth_headers, sample_pdf)
    r = client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": None},
    )
    assert r.status_code == 201
    assert r.json()["expires_at"] is None

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


# --- Endpoint publico ---


def _create_with_share(client, auth_headers, sample_pdf, expires_in_days=30):
    aid = _create_analysis(client, auth_headers, sample_pdf)
    created = client.post(
        f"/api/analyses/{aid}/share",
        headers=auth_headers,
        json={"expires_in_days": expires_in_days},
    ).json()
    return aid, created


def test_public_view_works_without_auth(client, auth_headers, sample_pdf):
    _, created = _create_with_share(client, auth_headers, sample_pdf)
    token = created["token"]

    # Sin Authorization header
    r = client.get(f"/api/share/{token}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["audience"] == "docente"
    assert body["shared_by"] == "u@test.com"
    assert "report" in body
    assert "archivo" in body["report"]


def test_public_view_404_for_unknown_token(client):
    r = client.get("/api/share/totally-fake-token-xyz")
    assert r.status_code == 404


def test_public_view_410_for_revoked(client, auth_headers, sample_pdf):
    _, created = _create_with_share(client, auth_headers, sample_pdf)
    client.delete(f"/api/shares/{created['id']}", headers=auth_headers)

    r = client.get(f"/api/share/{created['token']}")
    assert r.status_code == 410


def test_public_view_410_for_expired(client, auth_headers, sample_pdf):
    from datetime import datetime, timedelta, timezone

    from src.api.db import SessionLocal
    from src.api.models import ShareToken

    _, created = _create_with_share(client, auth_headers, sample_pdf)
    db = SessionLocal()
    try:
        row = db.get(ShareToken, created["id"])
        row.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    r = client.get(f"/api/share/{created['token']}")
    assert r.status_code == 410


def test_public_view_410_when_analysis_deleted(client, auth_headers, sample_pdf):
    aid, created = _create_with_share(client, auth_headers, sample_pdf)
    client.delete(f"/api/analyses/{aid}", headers=auth_headers)

    # Cascade borra el share, asi que es 404 (no 410)
    r = client.get(f"/api/share/{created['token']}")
    assert r.status_code == 404


def test_public_view_filters_cumple(client, auth_headers, sample_pdf, monkeypatch):
    """Verifica que el reporte devuelto via /api/share/{token} no contiene CUMPLE."""
    # Mockear el reporte para tener mezcla de hallazgos
    fake_report = {
        "archivo": "test.pdf",
        "modelo": "qwen2.5:14b",
        "codigo_curso": "22A14",
        "dispatcher": "rule",
        "total_secciones": 1,
        "resultados": [
            {
                "seccion": "x",
                "hallazgos": [
                    {
                        "regla_id": "R1",
                        "regla": "ok rule",
                        "estado": "CUMPLE",
                        "evidencia": "ev",
                        "correccion": None,
                    },
                    {
                        "regla_id": "R2",
                        "regla": "fail rule",
                        "estado": "NO CUMPLE",
                        "evidencia": "ev2",
                        "correccion": "fix it",
                    },
                ],
            }
        ],
        "resumenes": {"oficina": "OFICINA SECRETO", "docente": "PARA DOCENTE"},
    }
    from unittest.mock import patch

    with patch("agent.analizar_pda", return_value=fake_report):
        _, created = _create_with_share(client, auth_headers, sample_pdf)
    r = client.get(f"/api/share/{created['token']}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "OFICINA SECRETO" not in str(body)
    assert body["report"]["resumen_docente"] == "PARA DOCENTE"
    assert body["report"]["total_no_cumple"] == 1
    reglas = [h["regla_id"] for s in body["report"]["secciones"] for h in s["hallazgos"]]
    assert reglas == ["R2"]


def test_public_view_uses_original_filename_not_upload_path(
    client, auth_headers, sample_pdf
):
    """No leak del path del upload temporal: el docente ve el filename original."""
    aid, created = _create_with_share(client, auth_headers, sample_pdf)
    r = client.get(f"/api/share/{created['token']}")
    assert r.status_code == 200
    archivo = r.json()["report"]["archivo"]
    assert "/" not in archivo  # no path components
    assert archivo.endswith(".pdf")


def test_public_view_increments_access_count(client, auth_headers, sample_pdf):
    aid, created = _create_with_share(client, auth_headers, sample_pdf)
    token = created["token"]

    client.get(f"/api/share/{token}")
    client.get(f"/api/share/{token}")

    items = client.get(f"/api/analyses/{aid}/shares", headers=auth_headers).json()
    assert items[0]["access_count"] == 2
    assert items[0]["last_accessed_at"] is not None

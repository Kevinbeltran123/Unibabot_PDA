"""Pytest fixtures para tests del backend.

Usa SQLite en memoria + un settings override que activa SYNC_MODE para
no requerir Redis ni worker. Mockea `analizar_pda` para no cargar Ollama.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SYNC_MODE"] = "1"
os.environ["JWT_SECRET"] = "test-secret-not-for-prod"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402


@pytest.fixture
def fake_report() -> dict:
    return {
        "archivo": "test.pdf",
        "modelo": "qwen2.5:14b",
        "codigo_curso": "22A14",
        "dispatcher": "rule",
        "total_secciones": 1,
        "resultados": [
            {
                "seccion": "__estructural_global__",
                "hallazgos": [
                    {
                        "regla_id": "EST-001",
                        "regla": "Test rule",
                        "estado": "CUMPLE",
                        "evidencia": "ok",
                        "correccion": None,
                    }
                ],
            }
        ],
    }


@pytest.fixture
def client(fake_report, tmp_path, monkeypatch):
    """TestClient con DB en memoria y analizar_pda mockeado."""
    from src.api import db as db_module
    from src.api.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "uploads_dir", tmp_path / "uploads")
    monkeypatch.setattr(settings, "reports_dir", tmp_path / "reports")
    monkeypatch.setattr(settings, "sync_mode", True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db_module, "engine", engine)
    monkeypatch.setattr(db_module, "SessionLocal", SessionLocal)

    db_module.Base.metadata.create_all(bind=engine)

    with patch("agent.analizar_pda", return_value=fake_report):
        from src.api.main import app

        # Override get_db dependency para que use el engine de tests
        from src.api.db import get_db as real_get_db

        def _override_get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[real_get_db] = _override_get_db

        with TestClient(app) as c:
            yield c

        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client) -> dict[str, str]:
    resp = client.post(
        "/api/auth/register",
        json={"email": "u@test.com", "password": "password123"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_pdf(tmp_path) -> Path:
    p = tmp_path / "tiny.pdf"
    p.write_bytes(b"%PDF-1.4\n%fake test pdf bytes\n%%EOF\n")
    return p

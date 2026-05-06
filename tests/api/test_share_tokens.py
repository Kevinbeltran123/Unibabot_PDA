"""Tests del modulo share_tokens.py: generacion, hash, lookup."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.api.models import Analysis, ShareToken, User
from src.api.share_tokens import _hash, generate_token, lookup_active


def _seed(client) -> tuple[str, str]:
    """Crea user + analysis en la DB del client. Devuelve (user_id, analysis_id)."""
    from src.api.db import SessionLocal

    db = SessionLocal()
    try:
        user = User(id="u1", email="seed@test.com", password_hash="x")
        analysis = Analysis(
            id="a1",
            user_id="u1",
            filename="x.pdf",
            pdf_sha256="0" * 64,
            status="done",
        )
        db.add_all([user, analysis])
        db.commit()
        return user.id, analysis.id
    finally:
        db.close()


def test_generate_token_returns_pair_and_hashes_match(client):
    plain, h = generate_token()
    assert plain != h
    assert len(plain) >= 32
    assert _hash(plain) == h


def test_generate_token_collision_resistance(client):
    seen = {generate_token()[0] for _ in range(1000)}
    assert len(seen) == 1000


def test_lookup_active_returns_none_when_unknown(client):
    from src.api.db import SessionLocal

    db = SessionLocal()
    try:
        assert lookup_active(db, "nope") is None
    finally:
        db.close()


def test_lookup_active_returns_row_and_increments(client):
    from src.api.db import SessionLocal

    user_id, analysis_id = _seed(client)
    plain, h = generate_token()

    db = SessionLocal()
    try:
        token = ShareToken(
            id="s1",
            token_hash=h,
            analysis_id=analysis_id,
            created_by_user_id=user_id,
        )
        db.add(token)
        db.commit()

        row = lookup_active(db, plain)
        assert row is not None
        assert row.id == "s1"
        assert row.access_count == 1
        assert row.last_accessed_at is not None
        db.commit()

        row2 = lookup_active(db, plain)
        assert row2 is not None
        assert row2.access_count == 2
    finally:
        db.close()


def test_lookup_active_rejects_revoked(client):
    from src.api.db import SessionLocal

    user_id, analysis_id = _seed(client)
    plain, h = generate_token()

    db = SessionLocal()
    try:
        token = ShareToken(
            id="s2",
            token_hash=h,
            analysis_id=analysis_id,
            created_by_user_id=user_id,
            revoked_at=datetime.now(timezone.utc),
        )
        db.add(token)
        db.commit()

        assert lookup_active(db, plain) is None
    finally:
        db.close()


def test_lookup_active_rejects_expired(client):
    from src.api.db import SessionLocal

    user_id, analysis_id = _seed(client)
    plain, h = generate_token()

    db = SessionLocal()
    try:
        token = ShareToken(
            id="s3",
            token_hash=h,
            analysis_id=analysis_id,
            created_by_user_id=user_id,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        db.add(token)
        db.commit()

        assert lookup_active(db, plain) is None
    finally:
        db.close()


def test_lookup_active_accepts_future_expiry(client):
    from src.api.db import SessionLocal

    user_id, analysis_id = _seed(client)
    plain, h = generate_token()

    db = SessionLocal()
    try:
        token = ShareToken(
            id="s4",
            token_hash=h,
            analysis_id=analysis_id,
            created_by_user_id=user_id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        db.add(token)
        db.commit()

        assert lookup_active(db, plain) is not None
    finally:
        db.close()

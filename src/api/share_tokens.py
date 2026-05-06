"""Helpers para tokens de share-link read-only.

Convencion:
- Generamos 32 bytes random (256 bits) y los codificamos base64url -> 43 chars.
- Almacenamos solo SHA-256 en `share_tokens.token_hash`.
- Validacion compara hashes en tiempo constante (`secrets.compare_digest`).
- El token plano solo existe en la respuesta del POST de creacion.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .models import ShareToken

TOKEN_BYTES = 32


def generate_token() -> tuple[str, str]:
    """Devuelve (plano, hash). El plano se entrega una sola vez."""
    plain = secrets.token_urlsafe(TOKEN_BYTES)
    return plain, _hash(plain)


def _hash(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def lookup_active(db: Session, plain_token: str) -> ShareToken | None:
    """Devuelve el ShareToken si existe, no esta revocado y no esta expirado.

    Comparacion por hash en tiempo constante. Actualiza last_accessed_at y
    access_count como side effect (commit responsabilidad del caller).
    """
    candidate_hash = _hash(plain_token)

    row = db.query(ShareToken).filter(ShareToken.token_hash == candidate_hash).first()
    if row is None:
        return None

    if not secrets.compare_digest(row.token_hash, candidate_hash):
        return None

    if row.revoked_at is not None:
        return None

    if row.expires_at is not None:
        # SQLite no preserva tzinfo: tratamos naive como UTC.
        exp = row.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp <= datetime.now(timezone.utc):
            return None

    row.last_accessed_at = datetime.now(timezone.utc)
    row.access_count = (row.access_count or 0) + 1
    return row

"""Endpoints de share-link read-only para vista docente.

Owner-only (con auth):
  POST   /api/analyses/{id}/share        -> crea token, devuelve plano (1 vez)
  GET    /api/analyses/{id}/shares       -> lista shares del analisis
  DELETE /api/shares/{share_id}          -> revoca (no borra fila)

Publico (sin auth) lo agrega step 3:
  GET    /api/share/{token}              -> reporte filtrado para docente
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import get_settings
from ..db import get_db
from ..models import Analysis, ShareToken, User
from ..rate_limit import check_rate_limit
from ..schemas import ShareCreate, ShareCreated, SharePublic, ShareReport, ShareSummary
from ..share_filter import filtrar_para_docente
from ..share_tokens import generate_token, lookup_active

router = APIRouter(tags=["shares"])

settings = get_settings()


def _row_to_summary(row: ShareToken) -> ShareSummary:
    return ShareSummary(
        id=row.id,
        audience=row.audience,
        created_at=row.created_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        last_accessed_at=row.last_accessed_at,
        access_count=row.access_count,
    )


def _get_owned_analysis_or_404(
    analysis_id: str, db: Session, current: User
) -> Analysis:
    row = db.get(Analysis, analysis_id)
    if row is None or row.user_id != current.id:
        raise HTTPException(status_code=404, detail="Analisis no encontrado")
    return row


@router.post(
    "/api/analyses/{analysis_id}/share",
    response_model=ShareCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_share(
    analysis_id: str,
    body: ShareCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> ShareCreated:
    """Crea un share-link para un analisis del usuario actual.

    Solo se permite cuando el analisis esta `done`. El token plano se devuelve
    UNA SOLA VEZ en la respuesta; despues solo queda el hash en DB.
    """
    analysis = _get_owned_analysis_or_404(analysis_id, db, current)
    if analysis.status != "done":
        raise HTTPException(
            status_code=409,
            detail=f"No se puede compartir un analisis en estado {analysis.status}",
        )

    plain, token_hash = generate_token()

    expires_at: datetime | None = None
    if body.expires_in_days is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)

    row = ShareToken(
        id=uuid.uuid4().hex,
        token_hash=token_hash,
        analysis_id=analysis.id,
        created_by_user_id=current.id,
        audience="docente",
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    base = settings.public_base_url.rstrip("/")
    url = f"{base}/share/{plain}"

    return ShareCreated(
        **_row_to_summary(row).model_dump(),
        token=plain,
        url=url,
    )


@router.get(
    "/api/analyses/{analysis_id}/shares",
    response_model=list[ShareSummary],
)
def list_shares(
    analysis_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[ShareSummary]:
    analysis = _get_owned_analysis_or_404(analysis_id, db, current)
    rows = (
        db.query(ShareToken)
        .filter(ShareToken.analysis_id == analysis.id)
        .order_by(ShareToken.created_at.desc())
        .all()
    )
    return [_row_to_summary(r) for r in rows]


@router.delete(
    "/api/shares/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_share(
    share_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = db.get(ShareToken, share_id)
    if row is None or row.created_by_user_id != current.id:
        raise HTTPException(status_code=404, detail="Share no encontrado")
    if row.revoked_at is not None:
        return None
    row.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return None


# --- Endpoint publico (sin auth) ---


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.get("/api/share/{token}", response_model=SharePublic)
def view_shared(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
) -> SharePublic:
    """Vista publica read-only para el docente. Sin auth.

    Rate limited por IP (configurable). Devuelve 410 si el token esta
    expirado o revocado. 404 si no existe.
    """
    ip = _client_ip(request)
    try:
        from ..jobs.queue import get_redis

        redis_client = get_redis()
        allowed = check_rate_limit(
            redis_client,
            key=f"share:{ip}",
            max_requests=settings.share_rate_limit_per_minute,
            window_seconds=60,
        )
        if not allowed:
            raise HTTPException(status_code=429, detail="Demasiados intentos")
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001
        # Sin redis: fail-open (rate_limit ya logea).
        pass

    row = lookup_active(db, token)
    if row is None:
        # Distinguir 410 de 404 sin filtrar info: si el hash existe pero
        # esta revocado/expirado damos 410, en otro caso 404.
        import hashlib

        h = hashlib.sha256(token.encode("utf-8")).hexdigest()
        existing = db.query(ShareToken).filter(ShareToken.token_hash == h).first()
        if existing is None:
            raise HTTPException(status_code=404, detail="Link no encontrado")
        raise HTTPException(status_code=410, detail="Link expirado o revocado")

    db.commit()  # persiste last_accessed_at + access_count

    analysis = db.get(Analysis, row.analysis_id)
    if analysis is None or analysis.status != "done" or not analysis.report_path:
        raise HTTPException(status_code=410, detail="Reporte ya no disponible")

    report_path = Path(analysis.report_path)
    if not report_path.exists():
        raise HTTPException(status_code=410, detail="Reporte ya no disponible")

    try:
        reporte = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail="Reporte corrupto") from exc

    filtrado = filtrar_para_docente(reporte)
    # No filtrar el path crudo del upload temporal: el docente ve el nombre
    # original del PDA tal como lo subio la oficina.
    filtrado["archivo"] = analysis.filename

    owner = db.get(User, row.created_by_user_id)
    shared_by = owner.email if owner else "(usuario desconocido)"

    return SharePublic(
        audience=row.audience,
        shared_by=shared_by,
        analysis_completed_at=analysis.completed_at,
        expires_at=row.expires_at,
        report=ShareReport(**filtrado),
    )

"""Endpoints REST + SSE para analisis de PDAs.

POST   /api/analyses              -> sube PDF, encola job, 202 con id
GET    /api/analyses              -> lista del usuario actual
GET    /api/analyses/{id}         -> detalle (incluye reporte si done)
GET    /api/analyses/{id}/events  -> SSE stream de progreso en vivo
GET    /api/analyses/{id}/download -> descarga JSON crudo del reporte
DELETE /api/analyses/{id}         -> borra fila + archivos asociados
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from ..auth import get_current_user
from ..config import get_settings
from ..db import get_db
from ..models import Analysis, User
from ..schemas import AnalysisCreated, AnalysisDetail, AnalysisStatus, AnalysisSummary

router = APIRouter(prefix="/api/analyses", tags=["analyses"])

settings = get_settings()


def _row_to_summary(row: Analysis) -> AnalysisSummary:
    return AnalysisSummary(
        id=row.id,
        filename=row.filename,
        status=row.status,  # type: ignore[arg-type]
        codigo_curso=row.codigo_curso,
        modelo=row.modelo,
        dispatcher=row.dispatcher,
        enriquecer=row.enriquecer,
        generar_resumen=row.generar_resumen,
        created_at=row.created_at,
        completed_at=row.completed_at,
        duration_s=row.duration_s,
        error=row.error,
    )


def _row_to_detail(row: Analysis) -> AnalysisDetail:
    summary = _row_to_summary(row)
    report = None
    if row.status == "done" and row.report_path:
        try:
            report = json.loads(Path(row.report_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = None
    return AnalysisDetail(**summary.model_dump(), report=report)


@router.post("", response_model=AnalysisCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_analysis(
    file: UploadFile = File(...),
    codigo_curso: str | None = Form(default=None),
    modelo: str = Form(default="qwen2.5:14b"),
    dispatcher: str = Form(default="rule"),
    top_k: int = Form(default=5),
    enriquecer: bool = Form(default=False),
    generar_resumen: bool = Form(default=False),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> AnalysisCreated:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Se requiere un archivo PDF")
    if dispatcher not in ("rule", "rag"):
        raise HTTPException(status_code=400, detail="dispatcher debe ser 'rule' o 'rag'")

    contents = await file.read()
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"PDF excede limite de {settings.max_upload_mb} MB",
        )

    sha = hashlib.sha256(contents).hexdigest()
    analysis_id = uuid.uuid4().hex
    pdf_path = settings.uploads_dir / f"{analysis_id}.pdf"
    pdf_path.write_bytes(contents)

    row = Analysis(
        id=analysis_id,
        user_id=current.id,
        filename=file.filename,
        pdf_sha256=sha,
        status="pending",
        codigo_curso=(codigo_curso or "").strip() or None,
        modelo=modelo,
        dispatcher=dispatcher,
        top_k=top_k,
        enriquecer=enriquecer,
        generar_resumen=generar_resumen,
    )
    db.add(row)
    db.commit()

    if settings.sync_mode:
        from ..jobs.tasks import run_analysis

        try:
            run_analysis(analysis_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Analisis fallo: {exc}")
    else:
        from ..jobs.queue import enqueue_analysis

        enqueue_analysis(analysis_id)

    return AnalysisCreated(id=analysis_id, status="pending")


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> list[AnalysisSummary]:
    rows = (
        db.query(Analysis)
        .filter(Analysis.user_id == current.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
    return [_row_to_summary(r) for r in rows]


def _get_owned_or_404(analysis_id: str, db: Session, current: User) -> Analysis:
    row = db.get(Analysis, analysis_id)
    if row is None or row.user_id != current.id:
        raise HTTPException(status_code=404, detail="Analisis no encontrado")
    return row


@router.get("/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
) -> AnalysisDetail:
    row = _get_owned_or_404(analysis_id, db, current)
    return _row_to_detail(row)


@router.get("/{analysis_id}/download")
def download_report(
    analysis_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = _get_owned_or_404(analysis_id, db, current)
    if row.status != "done" or not row.report_path:
        raise HTTPException(status_code=409, detail=f"Analisis en estado {row.status}")
    path = Path(row.report_path)
    if not path.exists():
        raise HTTPException(status_code=410, detail="Reporte ya no disponible")
    safe_name = (row.filename or "reporte").rsplit(".", 1)[0] + ".json"
    return FileResponse(path, media_type="application/json", filename=safe_name)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    row = _get_owned_or_404(analysis_id, db, current)
    if row.report_path:
        try:
            Path(row.report_path).unlink(missing_ok=True)
        except OSError:
            pass
    pdf_path = settings.uploads_dir / f"{row.id}.pdf"
    pdf_path.unlink(missing_ok=True)
    db.delete(row)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content=None)


# --- SSE stream de progreso ---

async def _progress_stream(analysis_id: str, user_id: str):
    """Async generator de eventos SSE.

    1. Drena la lista de historial (lo que ya paso antes de conectarse).
    2. Suscribe al pub/sub para eventos en vivo.
    3. Termina cuando llega un evento 'complete', 'error', o 'done'.
    """
    from ..jobs.queue import get_redis

    r = get_redis()
    channel = f"analysis:{analysis_id}"
    history_key = f"{channel}:history"

    history = r.lrange(history_key, 0, -1)
    for raw in history:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        yield {"data": raw}
        if _is_terminal_event(raw):
            return

    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel)
    try:
        while True:
            msg = pubsub.get_message(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.05)
                continue
            data = msg.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            yield {"data": data}
            if _is_terminal_event(data):
                return
    finally:
        try:
            pubsub.unsubscribe(channel)
            pubsub.close()
        except Exception:
            pass


def _is_terminal_event(raw: str | bytes | None) -> bool:
    if raw is None:
        return False
    try:
        decoded = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        obj = json.loads(decoded)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    return obj.get("event") in ("complete", "error", "done")


@router.get("/{analysis_id}/events")
async def stream_events(
    analysis_id: str,
    token: str | None = None,
    db: Session = Depends(get_db),
):
    """SSE de progreso. Acepta token via query param porque EventSource del
    browser no soporta headers custom. Validacion manual en lugar de Depends.
    """
    from ..auth import _decode_token

    if not token:
        raise HTTPException(status_code=401, detail="Falta query param token")
    user_id = _decode_token(token)
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Usuario no existe")

    row = _get_owned_or_404(analysis_id, db, user)
    if row.status in ("done", "failed"):
        async def _replay():
            yield {"data": json.dumps({"event": "complete", "data": {"status": row.status}})}

        return EventSourceResponse(_replay())
    return EventSourceResponse(_progress_stream(analysis_id, user.id))

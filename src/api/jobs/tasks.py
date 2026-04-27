"""Tareas RQ: wrapper sobre `analizar_pda` que persiste resultado y publica progreso.

El worker importa este modulo. Para que el import funcione desde un proceso
fresco, fuerza el `sys.path` a incluir `src/` (mismo truco que streamlit_app.py).
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))


def _close_session_safely(db: Session) -> None:
    try:
        db.close()
    except Exception:
        pass


def run_analysis(analysis_id: str) -> str:
    """Ejecuta el pipeline para `analysis_id`.

    Lee la fila `analyses` por id, corre `analizar_pda` con publisher Redis,
    persiste el reporte JSON en `data/reports/{user_id}/{analysis_id}.json`,
    y actualiza la fila a status='done' o 'failed'.

    Retorna el path del reporte (string) cuando exitoso. RQ lo guardara
    en su result store (TTL configurable).
    """
    from agent import analizar_pda  # type: ignore[import-not-found]

    from ..config import get_settings
    from ..db import SessionLocal
    from ..models import Analysis
    from .progress import RedisProgressPublisher

    settings = get_settings()
    if settings.sync_mode:
        publisher = lambda event, data: None  # noqa: E731
    else:
        publisher = RedisProgressPublisher(settings.redis_url, analysis_id)

    db: Session = SessionLocal()
    try:
        analysis = db.get(Analysis, analysis_id)
        if analysis is None:
            raise RuntimeError(f"Analysis {analysis_id} no existe")

        analysis.status = "running"
        analysis.started_at = datetime.now(timezone.utc)
        db.commit()

        pdf_path = settings.uploads_dir / f"{analysis_id}.pdf"
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF no encontrado: {pdf_path}")

        inicio = time.time()
        try:
            reporte = analizar_pda(
                str(pdf_path),
                codigo_curso=analysis.codigo_curso,
                modelo=analysis.modelo,
                top_k=analysis.top_k,
                on_progress=publisher,
                enriquecer_correcciones=analysis.enriquecer,
                generar_resumen=analysis.generar_resumen,
                dispatcher=analysis.dispatcher,
            )
        except Exception as exc:
            publisher("error", {"message": str(exc)})
            analysis.status = "failed"
            analysis.error = str(exc)
            analysis.completed_at = datetime.now(timezone.utc)
            analysis.duration_s = time.time() - inicio
            db.commit()
            try:
                pdf_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise

        duracion = time.time() - inicio

        user_dir = settings.reports_dir / analysis.user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        report_path = user_dir / f"{analysis_id}.json"
        report_path.write_text(
            json.dumps(reporte, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        analysis.report_path = str(report_path)
        analysis.status = "done"
        analysis.completed_at = datetime.now(timezone.utc)
        analysis.duration_s = duracion
        db.commit()

        try:
            pdf_path.unlink(missing_ok=True)
        except Exception:
            pass

        publisher("complete", {"duration_s": duracion})
        return str(report_path)
    finally:
        _close_session_safely(db)

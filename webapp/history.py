"""Persistencia local de reportes generados por la webapp.

Los reportes se guardan en `results/history/{slug}__{timestamp}__{modelo}.json`
con un bloque `_meta` agregado sobre el dict original. No se copia el PDF.

La CLI sigue usando `results/reporte_cumplimiento.json` sin tocar esta carpeta,
para que el historial sea propiedad exclusiva de la UI.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
HISTORY_DIR = ROOT / "results" / "history"
FILENAME_PATTERN = re.compile(r"^(?P<slug>.+?)__(?P<ts>\d{8}-\d{6})__(?P<modelo>.+)\.json$")


@dataclass
class ReporteHistorial:
    """Entrada resumida para listar el historial en la sidebar."""

    path: Path
    pdf_filename: str
    timestamp: datetime
    modelo: str
    total_hallazgos: int
    cumplen: int
    no_cumplen: int


def slug_para_filename(nombre_pdf: str) -> str:
    """Sanitiza un nombre de PDF para usarlo como parte del filename del historial.

    Pasos:
        1. Quita la extension .pdf si esta
        2. Normaliza unicode y elimina acentos
        3. Reemplaza espacios y caracteres no seguros por underscore
        4. Colapsa underscores consecutivos
        5. Limita a 60 caracteres

    Ejemplo:
        "PDA - Intelligent Agents 2026A-01.docx.pdf" -> "PDA_Intelligent_Agents_2026A-01_docx"
    """
    nombre = nombre_pdf
    if nombre.lower().endswith(".pdf"):
        nombre = nombre[:-4]
    nombre_norm = unicodedata.normalize("NFKD", nombre)
    nombre_ascii = nombre_norm.encode("ascii", "ignore").decode("ascii")
    nombre_limpio = re.sub(r"[^a-zA-Z0-9\-]+", "_", nombre_ascii).strip("_")
    nombre_limpio = re.sub(r"_+", "_", nombre_limpio)
    return nombre_limpio[:60] or "reporte"


def _contar(reporte: dict) -> tuple[int, int, int]:
    """(total, cumple, no_cumple) sobre todos los hallazgos del reporte."""
    total = cumple = no_cumple = 0
    for seccion in reporte.get("resultados", []):
        for h in seccion.get("hallazgos", []):
            total += 1
            estado = h.get("estado")
            if estado == "CUMPLE":
                cumple += 1
            elif estado == "NO CUMPLE":
                no_cumple += 1
    return total, cumple, no_cumple


def guardar_reporte(reporte: dict, pdf_filename: str, duracion: float) -> Path:
    """Escribe el reporte en results/history/ con metadatos de la UI.

    Devuelve la ruta del archivo escrito.
    """
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ahora = datetime.now()
    slug = slug_para_filename(pdf_filename)
    modelo_raw = (reporte.get("modelo") or "desconocido").replace(":", "-").replace("/", "-")
    timestamp = ahora.strftime("%Y%m%d-%H%M%S")
    filename = f"{slug}__{timestamp}__{modelo_raw}.json"
    path = HISTORY_DIR / filename

    reporte_con_meta = dict(reporte)
    reporte_con_meta["_meta"] = {
        "timestamp": ahora.isoformat(),
        "pdf_filename": pdf_filename,
        "duration_seconds": round(duracion, 2),
    }
    path.write_text(
        json.dumps(reporte_con_meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def listar_reportes() -> list[ReporteHistorial]:
    """Escanea results/history/ y devuelve los reportes ordenados por fecha desc.

    Lee cada JSON para extraer metricas resumen. Es aceptable porque los
    reportes son de pocos KB y el historial tipicamente tiene <50 entradas.
    """
    if not HISTORY_DIR.exists():
        return []
    entradas: list[ReporteHistorial] = []
    for path in HISTORY_DIR.glob("*.json"):
        match = FILENAME_PATTERN.match(path.name)
        if not match:
            continue
        try:
            with open(path, encoding="utf-8") as f:
                reporte = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        total, cumplen, no_cumplen = _contar(reporte)
        meta = reporte.get("_meta", {})
        try:
            ts = datetime.fromisoformat(meta.get("timestamp", ""))
        except ValueError:
            ts = datetime.strptime(match.group("ts"), "%Y%m%d-%H%M%S")
        entradas.append(
            ReporteHistorial(
                path=path,
                pdf_filename=meta.get("pdf_filename", match.group("slug")),
                timestamp=ts,
                modelo=match.group("modelo"),
                total_hallazgos=total,
                cumplen=cumplen,
                no_cumplen=no_cumplen,
            )
        )
    entradas.sort(key=lambda e: e.timestamp, reverse=True)
    return entradas


def cargar_reporte(path: Path) -> dict:
    """Lee y devuelve el reporte completo desde disco."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)

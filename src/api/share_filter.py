"""Filtra el reporte canonico para la vista publica del docente.

Decision de producto (opcion B): el docente solo ve hallazgos NO CUMPLE,
con su correccion y correccion_enriquecida cuando exista. Las secciones
internas (`__estructural_global__`, `__declaraciones_global__`, etc.) se
mantienen solo si tienen al menos un NO CUMPLE.

NO se incluye `resumenes.oficina` y NO se incluyen hallazgos CUMPLE.
"""

from __future__ import annotations

from typing import Any


def filtrar_para_docente(reporte: dict[str, Any]) -> dict[str, Any]:
    secciones_filtradas: list[dict[str, Any]] = []
    total_no_cumple = 0

    for resultado in reporte.get("resultados", []):
        no_cumple = [
            _filtrar_hallazgo(h)
            for h in resultado.get("hallazgos", [])
            if h.get("estado") == "NO CUMPLE"
        ]
        if not no_cumple:
            continue
        total_no_cumple += len(no_cumple)
        secciones_filtradas.append(
            {
                "seccion": resultado.get("seccion", "(sin nombre)"),
                "hallazgos": no_cumple,
            }
        )

    resumen_docente: str | None = None
    resumenes = reporte.get("resumenes")
    if isinstance(resumenes, dict):
        resumen_docente = resumenes.get("docente")

    return {
        "archivo": reporte.get("archivo", ""),
        "codigo_curso": reporte.get("codigo_curso"),
        "total_no_cumple": total_no_cumple,
        "resumen_docente": resumen_docente,
        "secciones": secciones_filtradas,
    }


def _filtrar_hallazgo(h: dict[str, Any]) -> dict[str, Any]:
    return {
        "regla_id": h.get("regla_id", ""),
        "regla": h.get("regla", ""),
        "evidencia": h.get("evidencia", ""),
        "correccion": h.get("correccion"),
        "correccion_enriquecida": h.get("correccion_enriquecida"),
    }

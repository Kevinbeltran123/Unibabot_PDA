"""Tests del filtro `filtrar_para_docente` (puro, sin DB)."""

from __future__ import annotations

from src.api.share_filter import filtrar_para_docente


def _hallazgo(estado: str, regla_id: str = "R1", **extra) -> dict:
    return {
        "regla_id": regla_id,
        "regla": "regla",
        "estado": estado,
        "evidencia": "ev",
        "correccion": "corr" if estado == "NO CUMPLE" else None,
        **extra,
    }


def test_filter_drops_cumple():
    rep = {
        "archivo": "x.pdf",
        "codigo_curso": None,
        "resultados": [
            {
                "seccion": "estrategia",
                "hallazgos": [
                    _hallazgo("CUMPLE", "R1"),
                    _hallazgo("NO CUMPLE", "R2"),
                ],
            }
        ],
    }
    out = filtrar_para_docente(rep)
    assert out["total_no_cumple"] == 1
    assert len(out["secciones"]) == 1
    assert all(h["regla_id"] != "R1" for h in out["secciones"][0]["hallazgos"])


def test_filter_drops_section_with_zero_no_cumple():
    rep = {
        "archivo": "x.pdf",
        "resultados": [
            {"seccion": "perfecta", "hallazgos": [_hallazgo("CUMPLE")]},
            {"seccion": "fallida", "hallazgos": [_hallazgo("NO CUMPLE")]},
        ],
    }
    out = filtrar_para_docente(rep)
    nombres = [s["seccion"] for s in out["secciones"]]
    assert "fallida" in nombres
    assert "perfecta" not in nombres


def test_filter_keeps_internal_section_with_no_cumple():
    rep = {
        "archivo": "x.pdf",
        "resultados": [
            {
                "seccion": "__estructural_global__",
                "hallazgos": [_hallazgo("NO CUMPLE", "EST-001")],
            }
        ],
    }
    out = filtrar_para_docente(rep)
    assert len(out["secciones"]) == 1
    assert out["secciones"][0]["seccion"] == "__estructural_global__"


def test_filter_excludes_oficina_summary():
    rep = {
        "archivo": "x.pdf",
        "resultados": [],
        "resumenes": {
            "oficina": "EJECUTIVO PARA OFICINA",
            "docente": "DIDACTICO PARA DOCENTE",
        },
    }
    out = filtrar_para_docente(rep)
    assert out["resumen_docente"] == "DIDACTICO PARA DOCENTE"
    assert "oficina" not in out
    assert "EJECUTIVO" not in str(out)


def test_filter_handles_missing_resumenes():
    rep = {"archivo": "x.pdf", "resultados": []}
    out = filtrar_para_docente(rep)
    assert out["resumen_docente"] is None


def test_filter_preserves_correccion_enriquecida():
    rep = {
        "archivo": "x.pdf",
        "resultados": [
            {
                "seccion": "x",
                "hallazgos": [
                    _hallazgo(
                        "NO CUMPLE",
                        correccion="corr base",
                        correccion_enriquecida="corr enriquecida prescriptiva",
                    )
                ],
            }
        ],
    }
    out = filtrar_para_docente(rep)
    h = out["secciones"][0]["hallazgos"][0]
    assert h["correccion_enriquecida"] == "corr enriquecida prescriptiva"
    assert h["correccion"] == "corr base"

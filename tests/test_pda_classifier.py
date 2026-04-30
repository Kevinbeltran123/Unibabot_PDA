"""Tests del clasificador rule-based de PDAs.

Casos sintéticos: el clasificador es puro sobre dict[str, str], sin red,
sin LLM. Verificamos que cada rama de decisión devuelve el código y el
mensaje correctos.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pda_classifier import clasificar_documento  # noqa: E402


def _pda_completo() -> dict[str, str]:
    """Mock de PDA con suficientes señales para >= 6/11 EST = CUMPLE."""
    return {
        "Informacion general": (
            "programa academico Ingenieria de Sistemas "
            "nombre de la asignatura Agentes Inteligentes "
            "tipo de asignatura obligatoria "
            "modalidad presencial "
            "creditos 3 horarios docente Kevin Beltran"
        ),
        "Estrategia pedagogica": (
            "ABP aprendizaje basado en proyectos magistral "
            "estrategia pedagogica metodologia activa flipped"
        ),
        "Contexto de la asignatura": (
            "contexto contexto de la asignatura subject context"
        ),
        "Descripcion": "descripcion de la asignatura description",
        "Resultados de aprendizaje (RAE)": (
            "resultado de aprendizaje aprendiz competencia "
            "RAE 1 RAE 2 learning outcomes"
        ),
        "Competencias": "C1 C2 1c 1h SP5 D4 ABET 1.1",
        "Evaluacion": "criterios de evaluacion 30% 40% 30% porcentaje",
        "Cronograma": (
            "semana 1 semana 2 semana 3 enero febrero marzo "
            "01/02/2026 cronograma de actividades"
        ),
        "Bibliografia": "Russell Norvig 2020 referencias bibliografia",
        "Revisado y aprobado": "revisado y aprobado fecha 2026-01-15",
    }


def test_pda_valido_pasa():
    es_pda, code, mensaje = clasificar_documento(_pda_completo())
    assert es_pda is True
    assert code is None
    assert "secciones canónicas" in mensaje


def test_documento_vacio_es_rechazado():
    es_pda, code, mensaje = clasificar_documento({})
    assert es_pda is False
    assert code == "EMPTY_OR_SCANNED"
    assert "escaneado" in mensaje.lower()


def test_documento_corto_es_rechazado_como_escaneado():
    # Total < 500 chars -> EMPTY_OR_SCANNED
    es_pda, code, _ = clasificar_documento({"intro": "hola mundo"})
    assert es_pda is False
    assert code == "EMPTY_OR_SCANNED"


def test_pdf_con_texto_pero_sin_secciones_es_rechazado():
    # 1 sola seccion grande, sin matches estructurales -> NOT_A_PDA
    contenido = "este es un manual de usuario sin estructura academica " * 30
    es_pda, code, _ = clasificar_documento({"manual": contenido})
    assert es_pda is False
    # 1 seccion >= MIN_SECCIONES (2) es False, asi que pasa por verificar
    # estructurales -> 0/11 CUMPLE -> NOT_A_PDA
    assert code in ("INSUFFICIENT_STRUCTURE", "NOT_A_PDA")


def test_documento_academico_no_pda_es_rechazado():
    # Tiene "informacion general" pero nada mas canonico -> 1/11 EST CUMPLE
    secciones = {
        "Informacion general": (
            "programa nombre tipo modalidad horarios creditos "
            "este es el syllabus del curso de Algebra Lineal"
        ),
        "Temas": "tema 1 vectores tema 2 matrices " * 20,
    }
    es_pda, code, mensaje = clasificar_documento(secciones)
    assert es_pda is False
    assert code in ("INSUFFICIENT_STRUCTURE", "NOT_A_PDA")
    # El mensaje debe mencionar syllabus o academico para guiar al usuario
    assert any(
        kw in mensaje.lower() for kw in ("syllabus", "académico", "no es un pda")
    )


def test_template_viejo_se_distingue():
    # 3-5 / 11 EST CUMPLE -> OLD_TEMPLATE
    # Inflamos el contenido para superar MIN_CHARS_TOTAL=500.
    pad = "lorem ipsum dolor sit amet " * 20
    secciones = {
        "Informacion general": (
            "programa academico nombre de la asignatura "
            "tipo de asignatura modalidad presencial "
            "creditos 3 horarios docente " + pad
        ),
        "Estrategia pedagogica": (
            "metodologia ABP estrategia pedagogica magistral " + pad
        ),
        "Resultados de aprendizaje": (
            "RAE aprendiz resultado de aprendizaje learning outcome " + pad
        ),
    }
    es_pda, code, _ = clasificar_documento(secciones)
    # Puede caer en OLD_TEMPLATE (3-5) o INSUFFICIENT_STRUCTURE (1-2)
    assert es_pda is False
    assert code in ("OLD_TEMPLATE", "INSUFFICIENT_STRUCTURE")


def test_mensaje_es_string_no_vacio_siempre():
    # Cualquier rechazo debe tener mensaje listo para mostrar al usuario
    casos = [
        {},
        {"x": "y"},
        {"x": "y" * 600},
        _pda_completo(),
    ]
    for secciones in casos:
        _, _, mensaje = clasificar_documento(secciones)
        assert isinstance(mensaje, str)
        assert len(mensaje) > 10

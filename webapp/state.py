"""Manejo del session_state de la webapp.

Streamlit re-ejecuta el script entero en cada interaccion del usuario. Para
evitar que cambiar de tab (o cualquier otro widget) relance un analisis de 47
segundos, el resultado y el flujo se persisten en st.session_state.

Claves del estado:
    modo:               "upload" | "resultados"
    reporte_actual:     dict | None - el reporte de la ultima ejecucion
    pdf_filename:       str | None - nombre original del PDF analizado
    duracion_analisis:  float | None - segundos que tardo el analisis
    error_actual:       str | None - mensaje de error si el ultimo intento fallo
"""

import time
from pathlib import Path

import streamlit as st

CLAVES_DEFAULT = {
    "modo": "upload",
    "reporte_actual": None,
    "pdf_filename": None,
    "duracion_analisis": None,
    "error_actual": None,
}


def init_state() -> None:
    """Inicializa las claves de session_state si no existen. Idempotente."""
    for clave, valor in CLAVES_DEFAULT.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


def reset_analisis() -> None:
    """Vuelve al modo upload limpiando el reporte actual."""
    for clave, valor in CLAVES_DEFAULT.items():
        st.session_state[clave] = valor


def guardar_resultado(reporte: dict, pdf_filename: str, duracion: float) -> None:
    """Persiste el resultado de un analisis exitoso en session_state."""
    st.session_state.reporte_actual = reporte
    st.session_state.pdf_filename = pdf_filename
    st.session_state.duracion_analisis = duracion
    st.session_state.error_actual = None
    st.session_state.modo = "resultados"


def guardar_error(mensaje: str) -> None:
    """Persiste un error del ultimo intento de analisis."""
    st.session_state.error_actual = mensaje
    st.session_state.modo = "upload"


def limpiar_uploads_viejos(directorio: Path, edad_max_segundos: int = 3600) -> int:
    """Borra PDFs temporales con mas de `edad_max_segundos` segundos de edad.

    Se llama al inicio de streamlit_app.py. Devuelve cuantos archivos borro.
    """
    if not directorio.exists():
        return 0
    ahora = time.time()
    borrados = 0
    for archivo in directorio.glob("*.pdf"):
        try:
            edad = ahora - archivo.stat().st_mtime
            if edad > edad_max_segundos:
                archivo.unlink()
                borrados += 1
        except OSError:
            continue
    return borrados

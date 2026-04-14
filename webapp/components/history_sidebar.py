"""Sidebar con lista del historial de reportes."""

from datetime import datetime

import streamlit as st

from webapp.history import ReporteHistorial, cargar_reporte, listar_reportes


def _tiempo_relativo(ts: datetime) -> str:
    """Formato humano corto del tiempo transcurrido."""
    delta = datetime.now() - ts
    segundos = int(delta.total_seconds())
    if segundos < 60:
        return "hace segs"
    if segundos < 3600:
        return f"hace {segundos // 60}m"
    if segundos < 86400:
        return f"hace {segundos // 3600}h"
    if segundos < 604800:
        return f"hace {segundos // 86400}d"
    return ts.strftime("%Y-%m-%d")


def _label_entrada(entry: ReporteHistorial) -> str:
    nombre = entry.pdf_filename
    if len(nombre) > 32:
        nombre = nombre[:29] + "..."
    return nombre


def _render_entrada(entry: ReporteHistorial) -> None:
    """Renderiza una entrada del historial como un bloque clickeable."""
    col_btn, col_badge = st.columns([3, 1])
    with col_btn:
        if st.button(
            _label_entrada(entry),
            key=f"hist_{entry.path.name}",
            width="stretch",
        ):
            reporte = cargar_reporte(entry.path)
            st.session_state.reporte_actual = reporte
            st.session_state.pdf_filename = entry.pdf_filename
            st.session_state.duracion_analisis = (
                reporte.get("_meta", {}).get("duration_seconds", 0.0)
            )
            st.session_state.modo = "resultados"
            st.session_state.error_actual = None
            st.rerun()
    with col_badge:
        if entry.total_hallazgos == 0:
            st.caption("sin datos")
        elif entry.no_cumplen == 0:
            st.caption(f":green[{entry.cumplen}/{entry.total_hallazgos}]")
        elif entry.cumplen == 0:
            st.caption(f":red[{entry.no_cumplen}/{entry.total_hallazgos}]")
        else:
            st.caption(f":orange[{entry.cumplen}/{entry.total_hallazgos}]")
    st.caption(f"{_tiempo_relativo(entry.timestamp)} - `{entry.modelo}`")


def render_history_sidebar() -> None:
    """Muestra la lista de reportes en la sidebar, ordenada por mas reciente."""
    entradas = listar_reportes()
    if not entradas:
        st.caption("No hay reportes guardados aun.")
        return

    visibles = entradas[:10]
    resto = entradas[10:]
    for entry in visibles:
        _render_entrada(entry)

    if resto:
        with st.expander(f"Ver {len(resto)} mas"):
            for entry in resto:
                _render_entrada(entry)

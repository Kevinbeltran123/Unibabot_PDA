"""Renderizado de resultados del analisis en Streamlit.

Presenta el dict que devuelve analizar_pda como:
    1. Header con metricas globales + descarga del JSON
    2. Tab "Estructural": hallazgos de la entrada __estructural_global__
    3. Tab "Por seccion": expanders, uno por seccion del PDA
    4. Tab "Resumen": tabla pivot con todos los hallazgos para filtrar/ordenar

La clave especial "__estructural_global__" se separa del resto porque proviene
del rule-based checker, no del LLM, y conviene mostrarla aparte.
"""

import json

import streamlit as st

SECCION_ESTRUCTURAL = "__estructural_global__"


def _contar_hallazgos(resultados: list[dict]) -> tuple[int, int, int]:
    """Cuenta total / cumple / no_cumple sobre todos los hallazgos del reporte."""
    total = cumple = no_cumple = 0
    for seccion in resultados:
        for h in seccion.get("hallazgos", []):
            total += 1
            if h.get("estado") == "CUMPLE":
                cumple += 1
            elif h.get("estado") == "NO CUMPLE":
                no_cumple += 1
    return total, cumple, no_cumple


def _badge_estado(estado: str) -> str:
    """Devuelve un badge Markdown nativo de Streamlit segun el estado.

    Usa la sintaxis `:color[texto]` (Streamlit >=1.30) que se renderiza como
    un pill coloreado sin necesidad de HTML custom.
    """
    if estado == "CUMPLE":
        return ":green-background[CUMPLE]"
    if estado == "NO CUMPLE":
        return ":red-background[NO CUMPLE]"
    return f":gray-background[{estado or '?'}]"


def _render_hallazgo(hallazgo: dict) -> None:
    """Renderiza un hallazgo individual como bloque visual."""
    estado = hallazgo.get("estado", "")
    regla_id = hallazgo.get("regla_id", "")
    regla = hallazgo.get("regla", "")
    evidencia = hallazgo.get("evidencia", "")
    correccion = hallazgo.get("correccion") or ""

    header = _badge_estado(estado)
    if regla_id:
        header += f" &nbsp;&nbsp;`{regla_id}`"
    st.markdown(header)
    st.markdown(f"**{regla}**")
    if evidencia:
        st.markdown(f"> _Evidencia:_ {evidencia}")
    if estado == "NO CUMPLE" and correccion:
        st.info(f"**Correccion sugerida:** {correccion}")
    st.divider()


def _render_seccion_expander(seccion_dict: dict) -> None:
    """Un expander por seccion real (no la estructural)."""
    nombre = seccion_dict.get("seccion", "?")
    hallazgos = seccion_dict.get("hallazgos", [])
    total = len(hallazgos)
    cumple = sum(1 for h in hallazgos if h.get("estado") == "CUMPLE")
    no_cumple = sum(1 for h in hallazgos if h.get("estado") == "NO CUMPLE")

    if total == 0:
        badge = ":gray-background[sin hallazgos]"
    elif no_cumple == 0:
        badge = f":green-background[{cumple}/{total} cumple]"
    elif cumple == 0:
        badge = f":red-background[{no_cumple}/{total} no cumple]"
    else:
        badge = f":orange-background[{cumple}/{total} cumple]"

    with st.expander(f"{nombre}  —  {badge}"):
        if "error" in seccion_dict:
            st.warning(f"Error al evaluar: {seccion_dict['error']}")
            if "respuesta_cruda" in seccion_dict:
                st.code(seccion_dict["respuesta_cruda"])
            return
        for h in hallazgos:
            _render_hallazgo(h)


def _render_tab_resumen(resultados: list[dict]) -> None:
    """Tabla pivot con todos los hallazgos, filtrable por el usuario."""
    filas = []
    for seccion in resultados:
        nombre = seccion.get("seccion", "?")
        for h in seccion.get("hallazgos", []):
            filas.append({
                "regla_id": h.get("regla_id", ""),
                "seccion": nombre,
                "estado": h.get("estado", ""),
                "regla": (h.get("regla", "") or "")[:120],
            })
    if not filas:
        st.info("Sin hallazgos en el reporte.")
        return
    st.dataframe(filas, width="stretch", hide_index=True)


def render_results(reporte: dict) -> None:
    """Renderiza el reporte completo."""
    resultados = reporte.get("resultados", [])
    seccion_estructural = next(
        (s for s in resultados if s.get("seccion") == SECCION_ESTRUCTURAL),
        None,
    )
    secciones_pda = [s for s in resultados if s.get("seccion") != SECCION_ESTRUCTURAL]

    total, cumple, no_cumple = _contar_hallazgos(resultados)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Reglas evaluadas", total)
    col2.metric("Cumple", cumple)
    col3.metric("No cumple", no_cumple, delta=None)
    col4.metric("Secciones PDA", len(secciones_pda))

    col_meta, col_download = st.columns([3, 1])
    with col_meta:
        meta_parts = []
        if reporte.get("codigo_curso"):
            meta_parts.append(f"Curso: **{reporte['codigo_curso']}**")
        if reporte.get("modelo"):
            meta_parts.append(f"Modelo: `{reporte['modelo']}`")
        if meta_parts:
            st.caption(" &nbsp;|&nbsp; ".join(meta_parts))
    with col_download:
        st.download_button(
            "Descargar JSON",
            data=json.dumps(reporte, ensure_ascii=False, indent=2),
            file_name="reporte_cumplimiento.json",
            mime="application/json",
            width="stretch",
        )

    tab_estructural, tab_secciones, tab_resumen = st.tabs([
        f"Estructural ({len(seccion_estructural['hallazgos']) if seccion_estructural else 0})",
        f"Por seccion ({len(secciones_pda)})",
        f"Resumen ({total})",
    ])

    with tab_estructural:
        if not seccion_estructural or not seccion_estructural.get("hallazgos"):
            st.info("Sin hallazgos estructurales.")
        else:
            for h in seccion_estructural["hallazgos"]:
                _render_hallazgo(h)

    with tab_secciones:
        if not secciones_pda:
            st.info("No hay secciones del PDA evaluadas por el LLM.")
        else:
            for seccion in secciones_pda:
                _render_seccion_expander(seccion)

    with tab_resumen:
        _render_tab_resumen(resultados)

"""UnibaBot PDA - interfaz web Streamlit.

Entry point: `streamlit run streamlit_app.py`

Orquesta el flujo completo: upload PDF -> analisis -> resultados -> historial.
La logica pesada vive en webapp/; este archivo solo hace routing segun
st.session_state.modo.
"""

import sys
import time
import uuid
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

from common.logging_config import setup_logging

setup_logging()

from agent import (
    MODELO_DEFAULT,
    MODELO_QWEN,
    analizar_pda,
)
from webapp.components.history_sidebar import render_history_sidebar
from webapp.components.results_view import render_results
from webapp.history import guardar_reporte
from webapp.progress_adapter import seguimiento_analisis
from webapp.state import (
    guardar_error,
    guardar_resultado,
    init_state,
    limpiar_uploads_viejos,
    reset_analisis,
)

TMP_UPLOADS = ROOT / "tmp" / "uploads"
TMP_UPLOADS.mkdir(parents=True, exist_ok=True)

MODELOS_UI = {
    "Qwen 2.5 14B (m15, accuracy 1.000)": MODELO_QWEN,
}


def guardar_pdf_temporal(uploaded_file) -> Path:
    """Escribe el PDF subido a tmp/uploads/{uuid}.pdf y devuelve la ruta."""
    path = TMP_UPLOADS / f"{uuid.uuid4().hex}.pdf"
    path.write_bytes(uploaded_file.getvalue())
    return path


def render_sidebar() -> None:
    with st.sidebar:
        st.header("UnibaBot PDA")
        st.caption("Verificador de PDAs")
        if st.button("Nuevo analisis", width="stretch"):
            reset_analisis()
            st.rerun()
        st.divider()
        st.subheader("Historial")
        render_history_sidebar()


def render_upload() -> None:
    st.title("UnibaBot PDA")
    st.caption("Verificador de cumplimiento de Planes de Desarrollo Academico")

    if st.session_state.error_actual:
        st.error(st.session_state.error_actual)

    with st.form("upload_form"):
        uploaded_file = st.file_uploader(
            "Sube un PDA en PDF",
            type=["pdf"],
            accept_multiple_files=False,
        )
        col1, col2 = st.columns(2)
        with col1:
            codigo_curso = st.text_input(
                "Codigo del curso (opcional)",
                placeholder="ej: 22A14",
                help="Activa las reglas de dimension especificas del curso",
            )
        with col2:
            modelo_label = st.selectbox(
                "Modelo",
                options=list(MODELOS_UI.keys()),
                index=0,
            )
        st.markdown("**Enriquecimientos LLM (opcionales)**")
        col_enriq, col_resumen = st.columns(2)
        with col_enriq:
            enriquecer = st.toggle(
                "Correcciones enriquecidas",
                value=False,
                help=(
                    "Genera texto prescriptivo con codigo literal entre "
                    "comillas para cada NO CUMPLE. Cacheado: la segunda "
                    "corrida del mismo PDA es instantanea. +15s primera vez."
                ),
            )
        with col_resumen:
            resumen = st.toggle(
                "Resumenes ejecutivo y didactico",
                value=False,
                help=(
                    "Anade dos resumenes al inicio del reporte: uno para "
                    "la oficina del programa y otro para el docente. "
                    "Cacheado. +15s primera vez."
                ),
            )

        with st.expander("Opciones avanzadas"):
            top_k = st.slider("top_k (lineamientos por seccion)", 3, 10, 5)

        submitted = st.form_submit_button(
            "Analizar PDA",
            type="primary",
        )

    if submitted:
        if uploaded_file is None:
            st.warning("Debes subir un PDF antes de analizar.")
        else:
            ejecutar_analisis(
                uploaded_file=uploaded_file,
                codigo=codigo_curso.strip() or None,
                modelo=MODELOS_UI[modelo_label],
                top_k=top_k,
                enriquecer=enriquecer,
                generar_resumen=resumen,
            )


def ejecutar_analisis(
    uploaded_file,
    codigo: str | None,
    modelo: str,
    top_k: int,
    enriquecer: bool = False,
    generar_resumen: bool = False,
) -> None:
    """Dispara analizar_pda con progreso en vivo y rerun al modo resultados."""
    pdf_path = guardar_pdf_temporal(uploaded_file)
    inicio = time.time()

    with seguimiento_analisis(uploaded_file.name) as (status, on_progress):
        try:
            reporte = analizar_pda(
                str(pdf_path),
                codigo_curso=codigo,
                modelo=modelo,
                top_k=top_k,
                on_progress=on_progress,
                enriquecer_correcciones=enriquecer,
                generar_resumen=generar_resumen,
            )
        except Exception as exc:
            pdf_path.unlink(missing_ok=True)
            status.update(label=f"Error: {exc}", state="error")
            guardar_error(f"Error al analizar: {exc}")
            st.rerun()
            return
        else:
            duracion = time.time() - inicio
            status.update(
                label=f"Analisis completado en {duracion:.1f}s",
                state="complete",
            )

    pdf_path.unlink(missing_ok=True)
    duracion = time.time() - inicio
    try:
        guardar_reporte(reporte, uploaded_file.name, duracion)
    except OSError as exc:
        st.warning(f"No se pudo guardar en el historial: {exc}")
    guardar_resultado(reporte, uploaded_file.name, duracion)
    st.rerun()


def render_resultados() -> None:
    reporte = st.session_state.reporte_actual
    if reporte is None:
        reset_analisis()
        st.rerun()
        return

    col_title, col_back = st.columns([5, 1])
    with col_title:
        st.title("Reporte de cumplimiento")
        st.caption(
            f"{st.session_state.pdf_filename}  —  "
            f"tiempo: {st.session_state.duracion_analisis:.1f}s"
        )
    with col_back:
        if st.button("Volver", width="stretch"):
            reset_analisis()
            st.rerun()

    render_results(reporte)


def main() -> None:
    st.set_page_config(
        page_title="UnibaBot PDA",
        page_icon=None,
        layout="wide",
    )
    init_state()
    limpiar_uploads_viejos(TMP_UPLOADS)

    render_sidebar()

    if st.session_state.modo == "resultados":
        render_resultados()
    else:
        render_upload()


if __name__ == "__main__":
    main()

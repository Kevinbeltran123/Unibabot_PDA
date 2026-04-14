"""Puente entre los eventos del callback de `analizar_pda` y la UI de Streamlit.

El agente emite eventos estructurados (parsing_start, section_eval_start, etc).
Este modulo los traduce a updates visuales: label del st.status, barra de
progreso y texto de estado. Toda la logica de UI vive aqui para mantener
streamlit_app.py corto.

Uso desde streamlit_app.py:

    with seguimiento_analisis(nombre_pdf) as (status, on_progress):
        try:
            reporte = analizar_pda(..., on_progress=on_progress)
            status.update(label=f"Analisis completado", state="complete")
        except Exception:
            status.update(label="Error", state="error")
            raise
"""

from contextlib import contextmanager
from typing import Iterator

import streamlit as st


@contextmanager
def seguimiento_analisis(nombre_pdf: str) -> Iterator[tuple]:
    """Context manager que crea los widgets de progreso y expone un callback.

    Yields una tupla `(status, on_progress)`:
        status: el objeto st.status (para cerrar con update(state="complete"))
        on_progress: callable compatible con la firma ProgressCallback de agent.py

    Los widgets se crean dentro del context manager para que Streamlit los
    coloque en el lugar correcto del flujo del script.
    """
    with st.status(f"Analizando {nombre_pdf}...", expanded=True) as status:
        progress_bar = st.progress(0, text="Iniciando...")
        status_text = st.empty()

        def on_progress(event: str, data: dict) -> None:
            """Traduce eventos del agente a updates visuales.

            Contrato de eventos (ver agent.py para la lista completa):
                parsing_start       {pdf_path, modelo}
                parsing_done        {num_secciones}
                structural_start    {}
                structural_done     {hallazgos}
                llm_prep_start      {}
                llm_prep_done       {num_evaluaciones}
                section_eval_start  {index, total, name}
                section_eval_done   {index, total, name, cumple, no_cumple}
                done                {total_secciones}
            """
            if event == "parsing_start":
                status.update(label=f"Parseando {nombre_pdf}...")
                status_text.write(f"Modelo: {data['modelo']}")
            elif event == "parsing_done":
                status_text.write(f"PDF parseado: {data['num_secciones']} secciones encontradas")
            elif event == "structural_start":
                status.update(label="Verificando reglas estructurales...")
            elif event == "structural_done":
                status_text.write(f"Reglas estructurales: {data['hallazgos']} hallazgos")
            elif event == "llm_prep_start":
                status.update(label="Preparando evaluacion LLM...")
            elif event == "llm_prep_done":
                total = data["num_evaluaciones"]
                status_text.write(f"Secciones a evaluar: {total}")
                progress_bar.progress(0, text=f"0 / {total}")
            elif event == "section_eval_start":
                idx = data["index"]
                total = data["total"]
                nombre = data["name"]
                status.update(label=f"Evaluando {idx}/{total}: {nombre}")
                progress_bar.progress((idx - 1) / total, text=f"{idx - 1} / {total}")
            elif event == "section_eval_done":
                idx = data["index"]
                total = data["total"]
                progress_bar.progress(idx / total, text=f"{idx} / {total}")
            elif event == "done":
                progress_bar.progress(1.0, text="Completado")

        yield status, on_progress

"""
RAG dispatcher: contrapartida semantica de rule_dispatcher.py para benchmarks.

Mismo contrato de salida que `reglas_aplicables()` pero el conjunto de reglas
se obtiene via retrieval semantico contra ChromaDB (pre-m11), no via iteracion
exhaustiva.

Uso: comparar head-to-head rule-driven vs RAG semantico aislando la variable
"como se selecciona el conjunto de reglas a evaluar". El extractor+matcher
deterministico que viene despues es identico para ambos pipelines.

Limitacion conocida: el retriever solo devuelve top_k por seccion. Las reglas
que no caen en el top_k de ninguna seccion del PDA NUNCA se evaluan, por lo
que aparecen como `not_found` en evaluate.py. Esa es exactamente la metrica
de cobertura que queremos medir.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.retriever import recuperar_lineamientos
from rag.rule_dispatcher import cargar_reglas


def recuperar_reglas_aplicables(
    secciones: dict[str, str],
    codigo_curso: str | None,
    top_k: int = 5,
    use_reranker: bool = True,
) -> list[dict]:
    """Drop-in replacement de `reglas_aplicables()` que usa retrieval semantico.

    Para cada seccion del PDA (excluyendo PREAMBULO y secciones triviales),
    consulta el retriever con el contenido + nombre + filtro por curso.
    Une todas las reglas recuperadas (deduplicadas por id).

    Returns:
        Lista de reglas en el formato de reglas.json (id, tipo, descripcion,
        aplica_a, seccion_pda). Solo se devuelven reglas no-estructurales
        para mantener paridad con `reglas_aplicables()`.
    """
    if not codigo_curso:
        return []

    # Indexamos reglas.json por id para enriquecer los resultados del retriever
    # (que solo devuelve id, descripcion, tipo, seccion_pda y distancia).
    reglas_full = {r["id"]: r for r in cargar_reglas()}

    ids_recuperados: set[str] = set()
    for nombre, contenido in secciones.items():
        if nombre == "PREAMBULO":
            continue
        if len(contenido or "") < 50:
            continue
        resultados = recuperar_lineamientos(
            texto=contenido,
            top_k=top_k,
            codigo_curso=codigo_curso,
            nombre_seccion=nombre,
            use_reranker=use_reranker,
        )
        for r in resultados:
            ids_recuperados.add(r["id"])

    # Filtrar a no-estructurales y devolver el objeto regla completo desde reglas.json.
    return [
        reglas_full[rid]
        for rid in ids_recuperados
        if rid in reglas_full and reglas_full[rid].get("tipo") != "estructural"
    ]


if __name__ == "__main__":
    # Smoke test contra el PDA bilingue donde el RAG historicamente fallaba
    from pdf_parser import parsear_pda

    pdf = Path(__file__).parent.parent.parent / "PDAs" / "PDA - Intelligent Agents 2026A-01.docx.pdf"
    secciones = parsear_pda(str(pdf))
    reglas = recuperar_reglas_aplicables(secciones, codigo_curso="22A14", top_k=5)
    print(f"Reglas recuperadas via RAG (22A14): {len(reglas)}")

    # Comparar con rule-driven
    from rag.rule_dispatcher import reglas_aplicables
    reglas_rule = reglas_aplicables("22A14")
    print(f"Reglas via rule-driven (22A14): {len(reglas_rule)}")

    ids_rag = {r["id"] for r in reglas}
    ids_rule = {r["id"] for r in reglas_rule}
    perdidas = ids_rule - ids_rag
    print(f"Reglas que el RAG NO recupero: {len(perdidas)}")
    if perdidas:
        print(f"  IDs: {sorted(perdidas)[:20]}")

"""
Rescate semantico para encontrar la seccion destino de una regla cuando
el match por nombre del rule_dispatcher falla.

Reemplaza FALLBACK_KEYWORDS_POR_SECCION_PDA: en lugar de mantener un
diccionario hardcoded de keywords por categoria de seccion_pda, usa el
cross-encoder multilingue del reranker para puntuar (rule_descripcion,
section_content) y devolver la seccion con mejor ranking.

Sin threshold absoluto: el cross-encoder de MS-MARCO devuelve logits
crudos (no probabilidades calibradas), por lo que un threshold como
"score > 0" no aplica. El modelo es bueno rankeando relativamente,
asi que se devuelve siempre el top-1. Si la sección elegida no contiene
declaracion relevante, el LLM downstream lo refleja en su veredicto:
no hay false positive silencioso porque la verificacion final es
deterministica (extractor + matcher).

El cross-encoder se carga lazy (lru_cache en reranker.py): si todas las
reglas pasan por el match por nombre del paso 1, este modulo nunca paga
el costo de ~280 MB en RAM ni los ~5-10s de carga inicial.
"""

from __future__ import annotations

from rag.reranker import rerank_candidatos

# Coherente con el filtro que ya aplicaba rule_dispatcher al evaluar
# secciones candidatas (linea 134 antes del refactor): por debajo de
# 50 chars no hay contenido evaluable.
MIN_SECCION_LEN = 50


def encontrar_seccion_via_semantica(
    regla: dict,
    secciones_pda: dict[str, str],
) -> str | None:
    """Devuelve el nombre de la seccion del PDA que mejor matchea la
    descripcion de la regla via cross-encoder, o None si no hay
    candidatos validos (todas las secciones son PREAMBULO o demasiado
    cortas).
    """
    candidatos = [
        {"nombre": nombre, "descripcion": contenido}
        for nombre, contenido in secciones_pda.items()
        if nombre != "PREAMBULO" and len(contenido) >= MIN_SECCION_LEN
    ]
    if not candidatos:
        return None

    rankeados = rerank_candidatos(regla["descripcion"], candidatos, top_k=1)
    if not rankeados:
        return None
    return rankeados[0]["nombre"]

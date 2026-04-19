"""
Cross-encoder reranker multilingue para refinar resultados del bi-encoder.

Usa un CrossEncoder de sentence-transformers que puntua pares (query, documento)
completos, mas preciso que cosine similarity de embeddings separados.

Parametrizable via variable de entorno UNIBABOT_RERANKER_MODEL.
Se puede desactivar con UNIBABOT_RERANKER_ENABLED=0.
"""

import os
from functools import lru_cache
from typing import Iterable


DEFAULT_RERANKER = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


def _resolver_modelo() -> str:
    return os.environ.get("UNIBABOT_RERANKER_MODEL", DEFAULT_RERANKER)


def _resolver_device() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def reranker_disponible() -> bool:
    """Permite activar reranker globalmente via env var.

    Desactivado por default tras el analisis m9: sobre este corpus en
    particular, el stack mpnet+reranker regresa vs all-MiniLM-L6-v2 solo.
    Activar explicitamente con UNIBABOT_RERANKER_ENABLED=1 para
    experimentar o si se cambia el embedding a uno multilingue mas fuerte.
    """
    flag = os.environ.get("UNIBABOT_RERANKER_ENABLED", "0")
    return flag not in ("0", "false", "False", "no")


@lru_cache(maxsize=1)
def _cargar_cross_encoder():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(_resolver_modelo(), device=_resolver_device())


def rerank_candidatos(query: str, candidatos: list[dict], top_k: int = 5) -> list[dict]:
    """Re-rankea candidatos con cross-encoder y devuelve top_k.

    Args:
        query: texto de consulta (ej: contenido de una seccion del PDA).
        candidatos: lista de dicts con al menos "descripcion". Los otros campos
            (id, tipo, seccion_pda, distancia) se preservan.
        top_k: cuantos candidatos devolver tras rerank.

    Returns:
        Lista re-ordenada de dicts, cada uno con campo extra "rerank_score".
    """
    if not candidatos:
        return []

    model = _cargar_cross_encoder()
    pares = [(query, c["descripcion"]) for c in candidatos]
    scores = model.predict(pares, show_progress_bar=False)

    for cand, score in zip(candidatos, scores):
        cand["rerank_score"] = float(score)

    ordenados = sorted(candidatos, key=lambda c: c["rerank_score"], reverse=True)
    return ordenados[:top_k]


def describir_configuracion() -> dict:
    return {
        "model_name": _resolver_modelo(),
        "device": _resolver_device(),
        "enabled": reranker_disponible(),
    }


if __name__ == "__main__":
    print("Configuracion actual:", describir_configuracion())
    if not reranker_disponible():
        print("Reranker desactivado via env var.")
    else:
        candidatos = [
            {"id": "A", "descripcion": "El PDA debe declarar competencia SABER PRO SP5 (Ingles)."},
            {"id": "B", "descripcion": "Todo PDA debe incluir cronograma."},
            {"id": "C", "descripcion": "Se requiere estrategia pedagogica declarada."},
        ]
        out = rerank_candidatos("Ingles SABER PRO", candidatos, top_k=3)
        for c in out:
            print(f"{c['id']} score={c['rerank_score']:.3f} :: {c['descripcion'][:60]}")

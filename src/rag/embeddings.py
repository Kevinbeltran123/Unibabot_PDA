"""
Embedding function personalizada para ChromaDB.

Por default usa all-MiniLM-L6-v2 (384d), que es el modelo que produjo la
config m8b de produccion (accuracy 1.000, matched 45/48). Se puede cambiar
a multilingue (ej. paraphrase-multilingual-mpnet-base-v2, 768d) via
variable de entorno UNIBABOT_EMBEDDING_MODEL, pero la evaluacion m9/m9.1
demostro que mpnet regresa sobre este corpus especifico (ver
results/evaluation_report.md seccion "Iteracion 4").
"""

import os
from functools import lru_cache
from typing import Sequence

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _resolver_modelo() -> str:
    return os.environ.get("UNIBABOT_EMBEDDING_MODEL", DEFAULT_MODEL)


def _resolver_device() -> str:
    """Detecta el mejor device disponible: cuda > mps > cpu."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


class SBERTEmbeddingFunction(EmbeddingFunction[Documents]):
    """EmbeddingFunction de ChromaDB que envuelve sentence-transformers.

    Normaliza L2 los embeddings (requerido para cosine distance con mpnet).
    Carga perezosa del modelo; el singleton vive en get_embedding_function().
    """

    def __init__(self, model_name: str, device: str):
        self.model_name = model_name
        self.device = device
        self._model: SentenceTransformer | None = None

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    def __call__(self, input: Documents) -> Embeddings:
        model = self._get_model()
        vectors = model.encode(
            list(input),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


@lru_cache(maxsize=1)
def get_embedding_function() -> SBERTEmbeddingFunction:
    """Singleton de la embedding function. Usado por ingest.py y retriever.py."""
    model_name = _resolver_modelo()
    device = _resolver_device()
    return SBERTEmbeddingFunction(model_name=model_name, device=device)


def describir_configuracion() -> dict:
    """Util para debugging: reporta modelo y device activos."""
    ef = get_embedding_function()
    return {
        "model_name": ef.model_name,
        "device": ef.device,
        "loaded": ef._model is not None,
    }


if __name__ == "__main__":
    print("Configuracion actual:", describir_configuracion())
    ef = get_embedding_function()
    vectors = ef(["Hola mundo", "Competencia generica SABER PRO"])
    print(f"Dimension: {len(vectors[0])}")
    print(f"Num vectores: {len(vectors)}")

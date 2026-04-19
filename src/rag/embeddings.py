"""
Embedding function personalizada para ChromaDB (opt-in).

Por default NO se usa esta clase: ChromaDB aplica su embedding function
default (ONNX all-MiniLM-L6-v2) que fue la que produjo la config m8b de
produccion (accuracy 1.000, matched 45/48).

Esta clase existe para permitir experimentos opt-in con embeddings
multilingues via la variable de entorno UNIBABOT_EMBEDDING_MODEL. Si la
variable no esta definida, get_embedding_function() devuelve None y
ChromaDB usa su default ONNX.

Importante: cargar all-MiniLM-L6-v2 via sentence-transformers con
normalize_embeddings=True NO produce los mismos vectores que el ONNX
interno de ChromaDB (m9.2 tuvo accuracy 0.973 / recall NC 0.000
exactamente por esa divergencia). Por eso la ruta default es "no
instanciar embedding function personalizada".
"""

import os
from functools import lru_cache
from typing import Sequence

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from sentence_transformers import SentenceTransformer


# Si UNIBABOT_EMBEDDING_MODEL esta definida, se usa el modelo indicado.
# Si no, get_embedding_function() devuelve None y ChromaDB usa su default.
ENV_VAR_MODEL = "UNIBABOT_EMBEDDING_MODEL"


def _resolver_modelo() -> str | None:
    """Devuelve el modelo si esta en env var, None si se debe usar el default de ChromaDB."""
    return os.environ.get(ENV_VAR_MODEL) or None


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
def get_embedding_function() -> SBERTEmbeddingFunction | None:
    """Singleton de la embedding function opt-in.

    Devuelve None si la env var UNIBABOT_EMBEDDING_MODEL no esta definida;
    en ese caso los consumidores (ingest.py, retriever.py) deben NO pasar
    embedding_function al crear/abrir la coleccion para que ChromaDB use
    su default ONNX (equivalente m8b).
    """
    model_name = _resolver_modelo()
    if not model_name:
        return None
    device = _resolver_device()
    return SBERTEmbeddingFunction(model_name=model_name, device=device)


def describir_configuracion() -> dict:
    """Util para debugging: reporta modelo y device activos."""
    ef = get_embedding_function()
    if ef is None:
        return {"model_name": "(ChromaDB default ONNX)", "device": "n/a", "loaded": False}
    return {
        "model_name": ef.model_name,
        "device": ef.device,
        "loaded": ef._model is not None,
    }


if __name__ == "__main__":
    print("Configuracion actual:", describir_configuracion())
    ef = get_embedding_function()
    if ef is None:
        print("No hay embedding function custom; se usara ChromaDB default.")
    else:
        vectors = ef(["Hola mundo", "Competencia generica SABER PRO"])
        print(f"Dimension: {len(vectors[0])}")
        print(f"Num vectores: {len(vectors)}")

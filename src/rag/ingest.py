"""
Carga las reglas de data/lineamientos/reglas.json en ChromaDB.

Cada regla se almacena como un documento independiente con metadata
para permitir filtrado por tipo, seccion, y curso.
"""

import json
import chromadb
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
REGLAS_PATH = ROOT / "data" / "lineamientos" / "reglas.json"
CHROMA_PATH = ROOT / "data" / "chroma_db"


def cargar_reglas() -> list[dict]:
    with open(REGLAS_PATH, encoding="utf-8") as f:
        return json.load(f)


def crear_coleccion(reset: bool = False) -> chromadb.Collection:
    """Crea o abre la coleccion de reglas en ChromaDB.

    Args:
        reset: Si True, borra la coleccion existente y la recrea.
    """
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))

    if reset:
        try:
            client.delete_collection("lineamientos")
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name="lineamientos",
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def ingestar_reglas(reset: bool = True):
    """Pipeline de ingesta: reglas.json -> ChromaDB con embeddings."""
    reglas = cargar_reglas()
    collection = crear_coleccion(reset=reset)

    # Preparar datos en batch
    ids = []
    documents = []
    metadatas = []

    for regla in reglas:
        ids.append(regla["id"])
        documents.append(regla["descripcion"])
        metadatas.append({
            "tipo": regla["tipo"],
            "seccion_pda": regla["seccion_pda"],
            "aplica_a": regla["aplica_a"],
        })

    # ChromaDB genera los embeddings automaticamente con su modelo default
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"Ingesta completada: {len(reglas)} reglas en ChromaDB")
    print(f"Persistido en: {CHROMA_PATH}")
    return collection


if __name__ == "__main__":
    ingestar_reglas()

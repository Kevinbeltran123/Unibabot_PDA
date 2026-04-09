"""
Recupera lineamientos relevantes de ChromaDB dado un fragmento de texto.
"""

import chromadb
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CHROMA_PATH = ROOT / "data" / "chroma_db"


def obtener_coleccion() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection("lineamientos")


def recuperar_lineamientos(
    texto: str,
    top_k: int = 5,
    codigo_curso: str | None = None,
) -> list[dict]:
    """Busca las reglas mas relevantes para un fragmento de texto.
    Returns:
        Lista de diccionarios con las reglas recuperadas y su distancia.
    """
    
    collection = obtener_coleccion()

    #Armar filtro de metadata
    if codigo_curso:
        where = {"$or": [{"aplica_a": codigo_curso}, {"aplica_a": "todos"}]}
    else:
        where = None
    
    #Hacer la busqueda semántica
    result = collection.query(
        query_texts=[texto],
        n_results=top_k,
        where=where,
    )

    #Transformar resultado a lista de dicts
    lineamientos = []
    for i in range (len(result["documents"][0])):
        lineamientos.append({
            "descripcion": result["documents"][0][i],
            "distancia": result["distances"][0][i],
            "tipo": result["metadatas"][0][i]["tipo"],
        })

    return lineamientos



# --- Para probar manualmente ---
if __name__ == "__main__":
    import sys

    texto = sys.argv[1] if len(sys.argv) > 1 else "resultados de aprendizaje esperados"
    codigo = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Query: '{texto}'")
    if codigo:
        print(f"Filtro curso: {codigo}")
    print()

    resultados = recuperar_lineamientos(texto, top_k=5, codigo_curso=codigo)

    if resultados is None:
        print("La funcion recuperar_lineamientos() aun no esta implementada.")
    else:
        for i, r in enumerate(resultados):
            print(f"[{i+1}] (distancia: {r['distancia']:.3f}) [{r['tipo']}]")
            print(f"    {r['descripcion'][:120]}")
            print()

"""
Recupera lineamientos relevantes de ChromaDB dado un fragmento de texto.
"""

import chromadb
from pathlib import Path

from rag.seccion_mapping import secciones_pda_validas
from rag.embeddings import get_embedding_function
from rag.reranker import rerank_candidatos, reranker_disponible

ROOT = Path(__file__).parent.parent.parent
CHROMA_PATH = ROOT / "data" / "chroma_db"


def obtener_coleccion() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_collection(
        "lineamientos",
        embedding_function=get_embedding_function(),
    )


def _construir_filtro(codigo_curso: str | None, nombre_seccion: str | None) -> dict | None:
    """Construye el filtro `where` de ChromaDB combinando curso + seccion_pda.

    - Si hay codigo_curso: filtra por aplica_a == codigo_curso OR aplica_a == "todos"
    - Si hay nombre_seccion: filtra por seccion_pda en la lista mapeada
    - Si hay ambos: combina con $and
    - Si hay ninguno: devuelve None (sin filtro)
    """
    filtros = []

    if codigo_curso:
        filtros.append({"$or": [{"aplica_a": codigo_curso}, {"aplica_a": "todos"}]})

    if nombre_seccion:
        secciones_validas = secciones_pda_validas(nombre_seccion)
        if secciones_validas:
            if len(secciones_validas) == 1:
                filtros.append({"seccion_pda": secciones_validas[0]})
            else:
                filtros.append({"$or": [{"seccion_pda": s} for s in secciones_validas]})

    if not filtros:
        return None
    if len(filtros) == 1:
        return filtros[0]
    return {"$and": filtros}


def recuperar_dimension_rules(codigo_curso: str) -> list[dict]:  # noqa: D401

    """Recupera todas las reglas de dimension para un curso directamente por metadata.

    Se usa para garantizar que las reglas de dimension siempre aparezcan en el
    contexto de secciones de competencias, independiente del ranking semantico.
    """
    collection = obtener_coleccion()
    result = collection.get(
        where={"$and": [{"tipo": "dimension"}, {"aplica_a": codigo_curso}]}
    )
    lineamientos = []
    for i in range(len(result["documents"])):
        lineamientos.append({
            "id": result["ids"][i],
            "descripcion": result["documents"][i],
            "distancia": 0.0,
            "tipo": result["metadatas"][i]["tipo"],
            "seccion_pda": result["metadatas"][i]["seccion_pda"],
        })
    return lineamientos


def recuperar_lineamientos(
    texto: str,
    top_k: int = 5,
    codigo_curso: str | None = None,
    nombre_seccion: str | None = None,
    use_reranker: bool = True,
    retrieve_k: int = 15,
) -> list[dict]:
    """Busca las reglas mas relevantes para un fragmento de texto.

    Args:
        texto: contenido a buscar (se usa para busqueda semantica)
        top_k: cuantos resultados devolver tras rerank
        codigo_curso: codigo del curso (ej: "22A14") para filtrar reglas por aplica_a
        nombre_seccion: nombre de la seccion detectada por el parser para filtrar
            reglas por seccion_pda via MAPPING_SECCIONES
        use_reranker: si True, recupera retrieve_k candidatos con bi-encoder
            y los re-rankea con cross-encoder multilingue, devolviendo top_k.
        retrieve_k: tamanio del pool inicial antes del rerank (ignorado si
            use_reranker=False).

    Returns:
        Lista de diccionarios con las reglas recuperadas.
    """
    collection = obtener_coleccion()

    where = _construir_filtro(codigo_curso, nombre_seccion)

    n_initial = retrieve_k if (use_reranker and reranker_disponible()) else top_k

    result = collection.query(
        query_texts=[texto],
        n_results=n_initial,
        where=where,
    )

    lineamientos = []
    for i in range(len(result["documents"][0])):
        lineamientos.append({
            "id": result["ids"][0][i],
            "descripcion": result["documents"][0][i],
            "distancia": result["distances"][0][i],
            "tipo": result["metadatas"][0][i]["tipo"],
            "seccion_pda": result["metadatas"][0][i]["seccion_pda"],
        })

    if use_reranker and reranker_disponible() and lineamientos:
        lineamientos = rerank_candidatos(texto, lineamientos, top_k=top_k)

    return lineamientos[:top_k]



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
            print(f"[{i+1}] {r['id']} (distancia: {r['distancia']:.3f}) [{r['tipo']}]")
            print(f"    {r['descripcion'][:120]}")
            print()

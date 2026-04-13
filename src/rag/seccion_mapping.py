"""
Mapeo de nombres de seccion del PDF (detectados por el parser) a los valores
de `seccion_pda` en la metadata de ChromaDB.

Permite filtrar reglas por tipo de seccion en el retriever, evitando que
reglas de competencias aparezcan al evaluar informacion general y viceversa.
"""

# Mapeo: keyword del nombre de seccion (lowercase, normalizado) -> lista de seccion_pda validas
# El matching es por substring: si el nombre de seccion CONTIENE alguno de estos keywords,
# se consideran validas las secciones_pda listadas.
MAPPING_SECCIONES = {
    # Informacion general / datos basicos del curso
    "informacion general": ["Informacion general"],
    "general information": ["Informacion general"],
    "syllabus": ["Informacion general"],
    "professor's information": ["Informacion general"],
    "plan de estudios": ["Informacion general"],

    # Estrategia pedagogica y metodologia
    "estrategia": ["Estrategia pedagogica"],
    "pedagogical strategy": ["Estrategia pedagogica"],
    "metodologia": ["Estrategia pedagogica"],
    "methodology": ["Estrategia pedagogica"],
    "how will my students learn": ["Estrategia pedagogica"],
    "what methodology": ["Estrategia pedagogica"],
    "what characterizes": ["Estrategia pedagogica"],
    "classroom typology": ["Estrategia pedagogica"],
    "tipologia del salon": ["Estrategia pedagogica"],

    # Contexto de la asignatura
    "contexto de la asignatura": ["Contexto de la asignatura"],
    "context of the subject": ["Contexto de la asignatura"],

    # Descripcion y proposito
    "descripcion y proposito": ["Descripcion y proposito"],
    "description and purpose": ["Descripcion y proposito"],
    "descripcion del curso": ["Descripcion y proposito"],

    # Resultados de aprendizaje y competencias
    "resultados de aprendizaje": [
        "Resultados de Aprendizaje Esperados",
        "Competencias",
        "Competencias / Resultados de Aprendizaje",
    ],
    "learning outcomes": [
        "Resultados de Aprendizaje Esperados",
        "Competencias",
        "Competencias / Resultados de Aprendizaje",
    ],
    "rae": [
        "Resultados de Aprendizaje Esperados",
        "Competencias",
        "Competencias / Resultados de Aprendizaje",
    ],
    "competencias especificas": ["Competencias", "Competencias / Resultados de Aprendizaje"],
    "competencias genericas": ["Competencias", "Competencias / Resultados de Aprendizaje"],
    "competencia": ["Competencias", "Competencias / Resultados de Aprendizaje"],

    # Criterios de evaluacion
    "criterios": ["Criterios de evaluacion"],
    "valoracion": ["Criterios de evaluacion"],
    "retroalimentacion": ["Criterios de evaluacion"],
    "feedback": ["Criterios de evaluacion"],
    "assessment": ["Criterios de evaluacion"],

    # Cronograma
    "cronograma": ["Cronograma"],
    "schedule": ["Cronograma"],
    "calendar": ["Cronograma"],
    "actividades": ["Cronograma"],

    # Bibliografia
    "bibliografia": ["Bibliografia"],
    "bibliography": ["Bibliografia"],
    "referencias": ["Bibliografia"],
    "references": ["Bibliografia"],

    # Politicas y acuerdos
    "politicas": ["Politicas y acuerdos"],
    "policies": ["Politicas y acuerdos"],
    "acuerdos": ["Politicas y acuerdos"],
    "agreements": ["Politicas y acuerdos"],

    # Encuadre pedagogico
    "encuadre pedagogico": ["Encuadre pedagogico"],
    "pedagogical agreement": ["Encuadre pedagogico"],
    "revisado y aprobado": ["Encuadre pedagogico"],
    "reviewed and approved": ["Encuadre pedagogico"],
    "fecha del encuadre": ["Encuadre pedagogico"],
    "date of pedagogical": ["Encuadre pedagogico"],
}


def normalizar_nombre(nombre: str) -> str:
    """Quita acentos y pasa a minusculas para matching."""
    texto = nombre.lower().strip()
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for original, reemplazo in reemplazos.items():
        texto = texto.replace(original, reemplazo)
    return texto


def secciones_pda_validas(nombre_seccion: str) -> list[str] | None:
    """Devuelve la lista de valores seccion_pda validos para un nombre de seccion.

    Args:
        nombre_seccion: nombre de la seccion detectada por el parser

    Returns:
        Lista de secciones_pda validas, o None si no hay mapping (en cuyo
        caso el retriever no debe filtrar por seccion).
    """
    nombre_norm = normalizar_nombre(nombre_seccion)

    # Intentar match con cada keyword del mapping
    for keyword, secciones_validas in MAPPING_SECCIONES.items():
        if keyword in nombre_norm:
            return secciones_validas

    return None

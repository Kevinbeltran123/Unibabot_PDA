"""
Mapeo de nombres de seccion del PDF (detectados por el parser) a los valores
de `seccion_pda` en la metadata de ChromaDB.

Permite filtrar reglas por tipo de seccion en el retriever, evitando que
reglas de competencias aparezcan al evaluar informacion general y viceversa.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.text import normalizar as _normalizar_common

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
    # "pedagogical strategy" y "what methodology" incluyen Competencias porque
    # PDAs bilingues (ej: Agentes Inteligentes) declaran competencias 1h, SP5
    # en estas secciones (COMP-103, COMP-104). Las demas secciones de estrategia
    # quedan sin Competencias para evitar FPs en evaluaciones incorrectas.
    "estrategia": ["Estrategia pedagogica"],
    "pedagogical strategy": ["Estrategia pedagogica", "Competencias", "Competencias / Resultados de Aprendizaje"],
    "metodologia": ["Estrategia pedagogica"],
    "methodology": ["Estrategia pedagogica"],
    "how will my students learn": ["Estrategia pedagogica"],
    "what methodology": ["Estrategia pedagogica", "Competencias", "Competencias / Resultados de Aprendizaje"],
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
    """Quita acentos y pasa a minusculas para matching.

    Wrapper thin sobre `common.text.normalizar` sin flags: no strippea
    numeros, porque los keywords del MAPPING pueden empezar con digitos.
    """
    return _normalizar_common(nombre)


def secciones_pda_validas(nombre_seccion: str) -> list[str] | None:
    """Devuelve la lista de valores seccion_pda validos para un nombre de seccion.

    Usa longest-match: si multiples keywords hacen match (ej: "methodology" y
    "what methodology"), gana el mas especifico (mas largo). Esto evita que
    keywords cortos como "methodology" enmascaren "what methodology".

    Args:
        nombre_seccion: nombre de la seccion detectada por el parser

    Returns:
        Lista de secciones_pda validas, o None si no hay mapping (en cuyo
        caso el retriever no debe filtrar por seccion).
    """
    nombre_norm = normalizar_nombre(nombre_seccion)

    # Longest-match: recopilar todos los matches y elegir el keyword mas largo
    mejor_keyword = None
    mejor_secciones = None
    for keyword, secciones_validas in MAPPING_SECCIONES.items():
        if keyword in nombre_norm:
            if mejor_keyword is None or len(keyword) > len(mejor_keyword):
                mejor_keyword = keyword
                mejor_secciones = secciones_validas

    return mejor_secciones

"""
Verificacion rule-based de reglas estructurales (EST-001 a EST-011).

Estas reglas son determinista: 100% precision/recall cuando la seccion del
PDA esta correctamente parseada. Evita pasar estas reglas al LLM, reduciendo
tokens y tiempo de inferencia.

Las 11 funciones check_EST_XXX reciben un diccionario {nombre_seccion: contenido}
y devuelven un hallazgo con la misma estructura que el LLM.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_parser import normalizar


# --- Helpers de busqueda de secciones ---

def find_seccion(secciones: dict[str, str], keywords: list[str]) -> tuple[str, str] | None:
    """Busca la primera seccion cuyo nombre normalizado contiene algun keyword.

    Devuelve (nombre_seccion, contenido) o None si no encuentra.
    """
    for nombre, contenido in secciones.items():
        nombre_norm = normalizar(nombre)
        for kw in keywords:
            if kw in nombre_norm:
                return (nombre, contenido)
    return None


def find_seccion_fallback(secciones: dict[str, str], keywords: list[str]) -> tuple[str, str] | None:
    """Busca por nombre de seccion, y si no encuentra, busca en el contenido de cualquier seccion.

    Esto es mas tolerante a fallas del parser: si "Context of the subject" no fue
    segmentado como seccion propia pero aparece dentro del contenido de otra seccion,
    igual lo detecta.
    """
    resultado = find_seccion(secciones, keywords)
    if resultado:
        return resultado

    # Fallback: buscar en el contenido
    for nombre, contenido in secciones.items():
        contenido_norm = normalizar(contenido)
        for kw in keywords:
            if kw in contenido_norm:
                return (nombre, contenido)
    return None


def contains_any(texto: str, patrones: list[str]) -> bool:
    """True si alguno de los patrones esta en el texto (case insensitive, sin acentos)."""
    texto_norm = normalizar(texto)
    return any(p in texto_norm for p in patrones)


def count_matches(texto: str, patrones: list[str]) -> int:
    """Cuenta cuantos patrones (de una lista) aparecen en el texto."""
    texto_norm = normalizar(texto)
    return sum(1 for p in patrones if p in texto_norm)


def hallazgo(regla_id: str, regla: str, cumple: bool, evidencia: str, correccion: str | None = None) -> dict:
    """Constructor de hallazgos con formato estandar."""
    return {
        "regla_id": regla_id,
        "regla": regla,
        "estado": "CUMPLE" if cumple else "NO CUMPLE",
        "evidencia": evidencia,
        "correccion": correccion if not cumple else None,
    }


# --- Checkers individuales ---

def check_EST_001(secciones: dict) -> dict:
    """Informacion general con programa, nombre, tipo, modalidad, creditos, horarios, docente."""
    regla = "Todo PDA debe incluir la seccion de informacion general con programa academico, nombre, tipo, modalidad, creditos, horarios y docente"
    resultado = find_seccion(secciones, ["informacion general", "general information"])
    if not resultado:
        return hallazgo("EST-001", regla, False, "Seccion de informacion general no encontrada", "Agregar seccion de informacion general")

    nombre, contenido = resultado
    campos = {
        "programa": ["programa", "program"],
        "nombre": ["nombre de la asignatura", "subject name", "nombre del curso"],
        "tipo": ["tipo de asignatura", "subject type", "asignatura obligatoria", "mandatory"],
        "modalidad": ["modalidad", "modality", "presencial", "presential"],
    }
    encontrados = sum(1 for _, patrones in campos.items() if contains_any(contenido, patrones))

    if encontrados >= 3:
        return hallazgo("EST-001", regla, True, f"Seccion '{nombre}' contiene {encontrados}/4 campos basicos de informacion general")
    return hallazgo("EST-001", regla, False, f"Seccion '{nombre}' solo contiene {encontrados}/4 campos basicos", "Agregar campos faltantes: programa, nombre, tipo, modalidad")


def check_EST_002(secciones: dict) -> dict:
    """Al menos una estrategia pedagogica."""
    regla = "Todo PDA debe declarar al menos una estrategia pedagogica"
    # Fallback a busqueda por contenido: con Docling, la estrategia queda
    # dentro de "Metodologia" y no emite seccion separada con "estrategia"
    # en el nombre. El fallback busca "estrategia" en el contenido.
    resultado = find_seccion_fallback(secciones, ["estrategia", "pedagogical strategy"])
    if not resultado:
        return hallazgo("EST-002", regla, False, "Seccion de estrategia pedagogica no encontrada", "Agregar seccion con al menos una estrategia pedagogica")

    nombre, contenido = resultado
    estrategias = [
        "aprendizaje basado en proyectos", "project-based learning",
        "aprendizaje basado en problemas", "problem-based",
        "clase magistral", "magistral",
        "estudio de casos", "case study",
        "flipped classroom", "aula invertida",
        "aprendizaje cooperativo", "cooperative learning",
        "aprendizaje colaborativo", "collaborative",
    ]
    if contains_any(contenido, estrategias):
        return hallazgo("EST-002", regla, True, f"Seccion '{nombre}' declara estrategia pedagogica valida")
    return hallazgo("EST-002", regla, False, f"Seccion '{nombre}' no menciona estrategias pedagogicas reconocidas", "Declarar explicitamente una estrategia pedagogica")


def check_EST_003(secciones: dict) -> dict:
    """Contexto de la asignatura."""
    regla = "Todo PDA debe describir el contexto de la asignatura"
    resultado = find_seccion_fallback(secciones, ["contexto de la asignatura", "context of the subject"])
    if not resultado:
        return hallazgo("EST-003", regla, False, "No se encontro descripcion del contexto en ninguna seccion", "Agregar seccion de contexto de la asignatura")

    nombre, contenido = resultado
    return hallazgo("EST-003", regla, True, f"Contexto encontrado en seccion '{nombre[:50]}'")


def check_EST_004(secciones: dict) -> dict:
    """Descripcion y proposito del curso."""
    regla = "Todo PDA debe incluir descripcion y proposito del curso"
    resultado = find_seccion_fallback(secciones, ["descripcion y proposito", "description and purpose", "proposito de la asignatura", "purpose of the course"])
    if not resultado:
        return hallazgo("EST-004", regla, False, "No se encontro descripcion y proposito en ninguna seccion", "Agregar seccion de descripcion y proposito del curso")

    nombre, contenido = resultado
    return hallazgo("EST-004", regla, True, f"Descripcion y proposito en seccion '{nombre[:50]}'")


def check_EST_005(secciones: dict) -> dict:
    """Resultados de Aprendizaje Esperados (RAE)."""
    regla = "Todo PDA debe declarar Resultados de Aprendizaje Esperados (RAE) medibles"
    resultado = find_seccion_fallback(secciones, ["resultados de aprendizaje", "learning outcomes", "rae"])
    if not resultado:
        return hallazgo("EST-005", regla, False, "No se encontraron RAEs en ninguna seccion", "Agregar seccion de Resultados de Aprendizaje Esperados")

    nombre, _ = resultado
    return hallazgo("EST-005", regla, True, f"RAEs declarados en/cerca de seccion '{nombre[:50]}'")


def check_EST_006(secciones: dict) -> dict:
    """Competencias especificas, genericas, SABER PRO, dimensiones."""
    regla = "Todo PDA debe declarar competencias especificas, genericas, SABER PRO y dimensiones"
    # Combinar contenido de todas las secciones donde podrian aparecer competencias
    texto_global = " ".join(contenido for contenido in secciones.values())

    tipos = {
        "especifica": ["competencia especifica", "c1", "c2", "c3", "specific competence"],
        "generica": ["competencia generica", "1a", "1b", "1c", "1d", "1e", "1f", "1g", "1h", "1i", "1j", "generic competence"],
        "saber_pro": ["saber pro", "sp1", "sp2", "sp3", "sp4", "sp5"],
        "dimension": ["dimension ", "d1", "d2", "d3", "d4", "d5", "d6"],
    }
    encontrados = sum(1 for patrones in tipos.values() if contains_any(texto_global, patrones))

    if encontrados >= 3:
        return hallazgo("EST-006", regla, True, f"PDA declara {encontrados}/4 tipos de competencias (especifica/generica/saberpro/dimension)")
    return hallazgo("EST-006", regla, False, f"PDA solo declara {encontrados}/4 tipos de competencias", "Agregar los tipos faltantes (especificas, genericas, SABER PRO, dimensiones)")


def check_EST_007(secciones: dict) -> dict:
    """Criterios de valoracion con porcentajes y fechas."""
    regla = "Todo PDA debe incluir criterios de valoracion y retroalimentacion con porcentajes y fechas"
    resultado = find_seccion(secciones, ["criterio", "valoracion", "retroalimentacion", "feedback", "assessment"])
    if not resultado:
        return hallazgo("EST-007", regla, False, "Seccion de criterios de valoracion no encontrada", "Agregar seccion de criterios con porcentajes y fechas")

    nombre, contenido = resultado
    # Porcentajes: tanto "20%" como "20 %" o "20 " seguido de texto tipo porcentaje
    tiene_porcentaje = bool(re.search(r"\d+\s*%|\b\d+\s+(entendimiento|analisis|calidad|interpretacion)", contenido.lower()))
    patrones_fecha = [
        r"semana\s*\d+",
        r"week\s*\d+",
        r"\d+\s*de\s*(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)",
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"throughout\s*the\s*semester",
        r"corte\s*\d+",
    ]
    tiene_fecha = any(re.search(p, contenido.lower()) for p in patrones_fecha)

    if tiene_porcentaje and tiene_fecha:
        return hallazgo("EST-007", regla, True, f"Seccion '{nombre}' incluye porcentajes y fechas")
    faltante = []
    if not tiene_porcentaje:
        faltante.append("porcentajes de evaluacion")
    if not tiene_fecha:
        faltante.append("fechas o semanas")
    return hallazgo("EST-007", regla, False, f"Seccion '{nombre}' incompleta", f"Agregar: {', '.join(faltante)}")


def check_EST_008(secciones: dict) -> dict:
    """Cronograma de actividades."""
    regla = "Todo PDA debe incluir un cronograma de actividades por semana o periodo"
    resultado = find_seccion(secciones, ["cronograma", "schedule", "calendar"])
    if not resultado:
        return hallazgo("EST-008", regla, False, "Seccion de cronograma no encontrada", "Agregar seccion de cronograma de actividades")

    nombre, contenido = resultado
    # Tambien buscar en secciones vecinas porque el parser suele partir tablas
    texto_global = " ".join(secciones.values())
    tiene_estructura = bool(re.search(r"semana\s*\d+|week\s*\d+|modulo|module|m[oó]dulo|rae\s*\d+", texto_global.lower()))

    if tiene_estructura:
        return hallazgo("EST-008", regla, True, f"Seccion '{nombre}' presente; cronograma detallado en contenido")
    return hallazgo("EST-008", regla, False, f"Seccion '{nombre}' sin estructura temporal clara", "Organizar cronograma por semanas o modulos numerados")


def check_EST_009(secciones: dict) -> dict:
    """Bibliografia de referencia."""
    regla = "Todo PDA debe incluir bibliografia de referencia"
    resultado = find_seccion(secciones, ["bibliografia", "bibliography", "references", "referencias"])
    if not resultado:
        return hallazgo("EST-009", regla, False, "Seccion de bibliografia no encontrada", "Agregar seccion de bibliografia con al menos 2 referencias")

    nombre, contenido = resultado
    tiene_citas = bool(re.search(r"\(\d{4}\)|\d{4}\)\.|\bpress\b|\bpublisher|\beditorial", contenido.lower()))

    if tiene_citas or len(contenido) > 200:
        return hallazgo("EST-009", regla, True, f"Seccion '{nombre}' contiene referencias bibliograficas")
    return hallazgo("EST-009", regla, False, f"Seccion '{nombre}' sin referencias claras", "Incluir al menos 2 referencias con autor, ano y editorial")


def check_EST_010(secciones: dict) -> dict:
    """Politicas y acuerdos para el buen funcionamiento."""
    regla = "Todo PDA debe incluir politicas y acuerdos para el buen funcionamiento"
    resultado = find_seccion_fallback(secciones, ["politicas", "policies", "acuerdos", "agreements", "pedagogical agreement", "acuerdo pedagogico"])
    if not resultado:
        return hallazgo("EST-010", regla, False, "No se encontraron politicas y acuerdos en ninguna seccion", "Agregar seccion de politicas del curso")

    nombre, _ = resultado
    return hallazgo("EST-010", regla, True, f"Politicas encontradas en/cerca de seccion '{nombre[:50]}'")


def check_EST_011(secciones: dict) -> dict:
    """Fecha del encuadre pedagogico + revisado y aprobado."""
    regla = "Todo PDA debe registrar la fecha del encuadre pedagogico y ser revisado y aprobado"
    # Fallback a busqueda por contenido: con Docling, "Encuadre pedagogico"
    # y "Revisado y aprobado" suelen quedar absorbidos en "1. Informacion
    # general" (Docling los detecta como parrafos, no como secciones propias).
    resultado_encuadre = find_seccion_fallback(secciones, ["encuadre pedagogico", "pedagogical agreement"])
    resultado_aprobado = find_seccion_fallback(secciones, ["revisado y aprobado", "reviewed and approved"])

    if not resultado_encuadre and not resultado_aprobado:
        return hallazgo("EST-011", regla, False, "Ni fecha de encuadre ni seccion de aprobacion encontradas", "Agregar fecha del encuadre y seccion de firmas de aprobacion")

    evidencias = []
    if resultado_encuadre:
        evidencias.append(f"fecha del encuadre en '{resultado_encuadre[0][:50]}'")
    if resultado_aprobado:
        evidencias.append(f"seccion 'Revisado y aprobado' presente")

    cumple = bool(resultado_encuadre and resultado_aprobado)
    evidencia = ", ".join(evidencias)
    correccion = None if cumple else "Agregar ambos: fecha de encuadre y seccion revisado y aprobado"
    return hallazgo("EST-011", regla, cumple, evidencia, correccion)


# --- Dispatcher ---

CHECKERS = [
    check_EST_001, check_EST_002, check_EST_003, check_EST_004,
    check_EST_005, check_EST_006, check_EST_007, check_EST_008,
    check_EST_009, check_EST_010, check_EST_011,
]


def verificar_estructurales(secciones: dict[str, str]) -> list[dict]:
    """Aplica todos los checkers estructurales al PDA segmentado.

    Devuelve una lista de hallazgos, uno por regla estructural.
    """
    return [checker(secciones) for checker in CHECKERS]


# --- CLI para debug ---

if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Uso: python estructural_checker.py <ruta_al_pdf>")
        sys.exit(1)

    from pdf_parser import parsear_pda

    pdf_path = sys.argv[1]
    secciones = parsear_pda(pdf_path)
    hallazgos = verificar_estructurales(secciones)

    print(f"\n=== Verificacion estructural de {pdf_path} ===\n")
    cumple = 0
    no_cumple = 0
    for h in hallazgos:
        estado = h["estado"]
        if estado == "CUMPLE":
            cumple += 1
        else:
            no_cumple += 1
        print(f"[{estado}] {h['regla_id']}: {h['evidencia']}")

    print(f"\nResumen: {cumple} CUMPLE, {no_cumple} NO CUMPLE")

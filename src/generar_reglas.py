"""
Genera data/lineamientos/reglas.json a partir de los JSONs en JSON_archives/.

Tipos de reglas:
- Estructurales: secciones obligatorias en todo PDA
- De contenido: competencias que cada curso debe declarar
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
JSON_DIR = ROOT / "JSON_archives"
OUTPUT = ROOT / "data" / "lineamientos" / "reglas.json"


def cargar_json(nombre: str) -> dict:
    with open(JSON_DIR / nombre, encoding="utf-8") as f:
        return json.load(f)


def generar_reglas_estructurales() -> list[dict]:
    """Reglas que aplican a TODO PDA, sin importar el curso."""
    secciones_obligatorias = [
        ("Informacion general", "Todo PDA debe incluir la seccion de informacion general con: programa academico, nombre de la asignatura, tipo, modalidad, creditos, horarios, y datos del docente."),
        ("Estrategia pedagogica", "Todo PDA debe declarar al menos una estrategia pedagogica (ej: aprendizaje basado en proyectos, clase magistral, estudio de casos)."),
        ("Contexto de la asignatura", "Todo PDA debe describir el contexto de la asignatura dentro del plan de estudios y su relacion con otras materias."),
        ("Descripcion y proposito", "Todo PDA debe incluir una descripcion del curso y su proposito formativo."),
        ("Resultados de Aprendizaje Esperados", "Todo PDA debe declarar Resultados de Aprendizaje Esperados (RAE) medibles y alineados con las competencias del curso."),
        ("Competencias", "Todo PDA debe declarar las competencias especificas, genericas, SABER PRO y dimensiones institucionales que desarrolla."),
        ("Criterios de evaluacion", "Todo PDA debe incluir criterios de valoracion y retroalimentacion con porcentajes y fechas."),
        ("Cronograma", "Todo PDA debe incluir un cronograma de actividades por semana o periodo."),
        ("Bibliografia", "Todo PDA debe incluir bibliografia de referencia."),
        ("Politicas y acuerdos", "Todo PDA debe incluir politicas y acuerdos para el buen funcionamiento del curso."),
        ("Encuadre pedagogico", "Todo PDA debe registrar la fecha del encuadre pedagogico y ser revisado y aprobado."),
    ]

    reglas = []
    for seccion, descripcion in secciones_obligatorias:
        reglas.append({
            "id": f"EST-{len(reglas)+1:03d}",
            "tipo": "estructural",
            "seccion_pda": seccion,
            "descripcion": descripcion,
            "aplica_a": "todos",
        })
    return reglas


def generar_reglas_competencias() -> list[dict]:
    """Reglas de competencias especificas por curso."""
    competencias = cargar_json("competencias.json")
    abet_es = cargar_json("abet_es.json")
    cursos = cargar_json("cursos.json")["cursos"]
    comp_cursos = cargar_json("competenciascursos.json")

    # Mapeo codigo -> nombre del curso
    codigo_a_nombre = {c["Codigo"]: c["Asignatura"] for c in cursos}

    reglas = []
    contador = 1

    for codigo, reqs in comp_cursos.items():
        nombre_curso = codigo_a_nombre.get(codigo, codigo)

        # Competencias especificas
        for comp_id in reqs.get("especificas", []):
            desc = competencias["competencias especificas"].get(comp_id, "")
            reglas.append({
                "id": f"COMP-{contador:03d}",
                "tipo": "competencia_especifica",
                "seccion_pda": "Competencias / Resultados de Aprendizaje",
                "descripcion": f"El PDA de {nombre_curso} ({codigo}) debe declarar la competencia especifica {comp_id}: {desc}",
                "aplica_a": codigo,
            })
            contador += 1

        # Competencias genericas
        for gen_id in reqs.get("genericas", []):
            desc = competencias["competencias genericas"].get(gen_id, "")
            reglas.append({
                "id": f"COMP-{contador:03d}",
                "tipo": "competencia_generica",
                "seccion_pda": "Competencias / Resultados de Aprendizaje",
                "descripcion": f"El PDA de {nombre_curso} ({codigo}) debe declarar la competencia generica {gen_id}: {desc}",
                "aplica_a": codigo,
            })
            contador += 1

        # SABER PRO
        for sp_id in reqs.get("saberpro", []):
            desc = competencias["SABER PRO"].get(sp_id, "")
            reglas.append({
                "id": f"COMP-{contador:03d}",
                "tipo": "saber_pro",
                "seccion_pda": "Competencias / Resultados de Aprendizaje",
                "descripcion": f"El PDA de {nombre_curso} ({codigo}) debe declarar SABER PRO {sp_id}: {desc}",
                "aplica_a": codigo,
            })
            contador += 1

        # Indicadores ABET
        for abet_id in reqs.get("abet", []):
            # Buscar el indicador en abet_es.json
            outcome_key = f"O{abet_id.split('.')[0]}"
            outcome = abet_es.get(outcome_key, {})
            indicador_desc = outcome.get("indicadores", {}).get(abet_id, "")
            reglas.append({
                "id": f"COMP-{contador:03d}",
                "tipo": "abet",
                "seccion_pda": "Competencias / Resultados de Aprendizaje",
                "descripcion": f"El PDA de {nombre_curso} ({codigo}) debe cubrir el indicador ABET {abet_id}: {indicador_desc}",
                "aplica_a": codigo,
            })
            contador += 1

        # Dimensiones
        for dim_id in reqs.get("dimension", []):
            desc = competencias["dimensiones"].get(dim_id, "")
            reglas.append({
                "id": f"COMP-{contador:03d}",
                "tipo": "dimension",
                "seccion_pda": "Informacion general / Competencias",
                "descripcion": f"El PDA de {nombre_curso} ({codigo}) debe declarar la dimension {dim_id}: {desc}",
                "aplica_a": codigo,
            })
            contador += 1

    return reglas


def main():
    reglas = generar_reglas_estructurales() + generar_reglas_competencias()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(reglas, f, ensure_ascii=False, indent=2)

    # Resumen
    tipos = {}
    for r in reglas:
        tipos[r["tipo"]] = tipos.get(r["tipo"], 0) + 1

    print(f"Reglas generadas: {len(reglas)}")
    for tipo, count in tipos.items():
        print(f"  {tipo}: {count}")
    print(f"Guardado en: {OUTPUT}")


if __name__ == "__main__":
    main()

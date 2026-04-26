"""
Rule dispatcher: mapeo rule -> seccion del PDA via metadata.

Reemplaza el retrieval semantico para COMP rules con iteracion
deterministica sobre todas las reglas aplicables al curso (m11).

Flujo:
1. Cargar reglas.json, filtrar a las aplicables al curso (aplica_a match)
   y no estructurales (EST se maneja via rule-based determinista).
2. Para cada regla, localizar la seccion real del PDA cuyo keyword
   mapee al regla.seccion_pda (inverso de MAPPING_SECCIONES).
3. Agrupar reglas por seccion destino -> {seccion: [reglas]}.
4. Reglas cuya seccion destino no existe -> clave especial
   "__seccion_no_presente__" para emitir NO CUMPLE deterministico.

Ventaja: cobertura 100% por construccion. Ninguna regla aplicable es
omitida, sin importar si el retrieval semantico la habria priorizado.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.seccion_mapping import secciones_pda_validas
from rag.semantic_fallback import encontrar_seccion_via_semantica

ROOT = Path(__file__).parent.parent.parent
REGLAS_PATH = ROOT / "data" / "lineamientos" / "reglas.json"

# Clave especial para reglas cuya seccion destino no existe en el PDA parseado.
# El orquestador (agent.py) emite hallazgos NO CUMPLE deterministicos.
SECCION_AUSENTE = "__seccion_no_presente__"


def cargar_reglas() -> list[dict]:
    with open(REGLAS_PATH, encoding="utf-8") as f:
        return json.load(f)


def reglas_aplicables(codigo_curso: str | None) -> list[dict]:
    """Todas las reglas no-estructurales que aplican al curso (incluye 'todos')."""
    todas = cargar_reglas()
    return [
        r for r in todas
        if r.get("tipo") != "estructural"
        and r.get("aplica_a") in (codigo_curso, "todos")
    ]


def encontrar_seccion_destino(
    regla: dict,
    secciones_pda: dict[str, str],
) -> str | None:
    """Localiza la seccion real del PDA donde debe evaluarse esta regla.

    Estrategia en 2 pasos:
    1. Match por nombre via MAPPING_SECCIONES invertido (rapido, preciso).
    2. Si falla, rescate semantico via cross-encoder: puntua
       (regla.descripcion, contenido) para cada seccion del PDA y
       devuelve la mejor si pasa el threshold del modelo. Reemplaza
       el diccionario hardcoded de keywords pre-refactor.

    Devuelve el nombre real de la seccion o None si ninguna matchea.
    """
    seccion_pda_target = regla.get("seccion_pda")
    if not seccion_pda_target:
        return None

    # Paso 1: match por nombre
    candidatas_nombre = []
    for nombre_pda in secciones_pda:
        if nombre_pda == "PREAMBULO":
            continue
        mapeadas = secciones_pda_validas(nombre_pda)
        if mapeadas and seccion_pda_target in mapeadas:
            candidatas_nombre.append(nombre_pda)

    if candidatas_nombre:
        # Preferir la seccion con contenido no trivial mas corta (mas especifica)
        con_contenido = [
            c for c in candidatas_nombre if len(secciones_pda.get(c, "")) >= 20
        ]
        if not con_contenido:
            con_contenido = candidatas_nombre
        return min(con_contenido, key=lambda n: len(n))

    # Paso 2: rescate semantico (modelo se carga lazy en la primera invocacion)
    return encontrar_seccion_via_semantica(regla, secciones_pda)


def agrupar_reglas_por_seccion(
    reglas: list[dict],
    secciones_pda: dict[str, str],
) -> dict[str, list[dict]]:
    """Agrupa reglas por la seccion real del PDA donde deben evaluarse.

    Reglas cuya seccion destino no existe se agrupan bajo SECCION_AUSENTE.
    El caller debe emitir hallazgos NO CUMPLE deterministicos para esas.

    Returns:
        dict {nombre_seccion: [reglas...]}. La clave SECCION_AUSENTE
        contiene las reglas sin seccion destino en el PDA.
    """
    grupos: dict[str, list[dict]] = {}
    for r in reglas:
        destino = encontrar_seccion_destino(r, secciones_pda)
        if destino is None:
            grupos.setdefault(SECCION_AUSENTE, []).append(r)
        else:
            grupos.setdefault(destino, []).append(r)
    return grupos


def formatear_regla_como_lineamiento(regla: dict) -> dict:
    """Adapta el formato reglas.json al formato que espera evaluar_seccion().

    evaluar_seccion espera lineamientos con campos id, tipo, descripcion.
    """
    return {
        "id": regla["id"],
        "tipo": regla["tipo"],
        "descripcion": regla["descripcion"],
        "seccion_pda": regla.get("seccion_pda", ""),
    }


if __name__ == "__main__":
    # Smoke test
    from pdf_parser import parsear_pda

    pdf = ROOT / "PDAs" / "PDA - Gestión TI 2026A.pdf"
    secciones = parsear_pda(pdf)
    reglas = reglas_aplicables("22A32")
    grupos = agrupar_reglas_por_seccion(reglas, secciones)

    print(f"Reglas aplicables a 22A32: {len(reglas)}")
    print(f"Grupos: {len(grupos)}")
    for nombre, rs in grupos.items():
        print(f"  [{nombre[:50]}] -> {len(rs)} reglas: {[r['id'] for r in rs]}")

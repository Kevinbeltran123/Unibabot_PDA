"""
Matcher determinista: compara codigos declarados (via extractor) vs
codigos requeridos (en metadata de reglas.json).

Cero LLM calls. Regex + set operations. Complementa a:
- estructural_checker (EST-001..EST-011)
- declaracion_extractor (extrae declaraciones del PDA)
"""

from __future__ import annotations

import re

# Patrones para extraer el codigo canonico desde descripcion de regla.
# Orden: primero busca el codigo tipico con marcador ("C1:", "1b:", etc.)
# Fallback a patrones mas laxos.
PATRONES_CODIGO_POR_TIPO = {
    "competencia_especifica": [
        r"competencia especifica\s+(C\d+)",
        r"(C\d+):",
        r"\b(C\d+)\b",
    ],
    "competencia_generica": [
        r"competencia generica\s+(\d+[a-l])",
        r"(\d+[a-l]):",
        r"\b(\d+[a-l])\b",
    ],
    "saber_pro": [
        r"SABER PRO\s+(SP\d+)",
        r"(SP\d+):",
        r"\b(SP\d+)\b",
    ],
    "dimension": [
        r"dimension\s+(D\d+)",
        r"(D\d+):",
        r"\b(D\d+)\b",
    ],
    "abet": [
        r"ABET\s+(\d+\.\d+)",
        r"indicador\s+ABET\s+(\d+\.\d+)",
        r"(\d+\.\d+):",
    ],
}

# Mapeo tipo de regla -> key en declaraciones dict
TIPO_A_KEY = {
    "competencia_especifica": "competencias_especificas",
    "competencia_generica": "competencias_genericas",
    "saber_pro": "saber_pro",
    "dimension": "dimensiones",
    "abet": "abet",
}


def extraer_codigo_de_regla(regla: dict) -> str | None:
    """Extrae el codigo canonico (C2, 1b, SP5, D4, 5.1) desde regla.descripcion.

    Devuelve None si el tipo no es canonico o no se puede extraer.
    """
    tipo = regla.get("tipo", "")
    patrones = PATRONES_CODIGO_POR_TIPO.get(tipo)
    if not patrones:
        return None

    descripcion = regla.get("descripcion", "")
    for patron in patrones:
        match = re.search(patron, descripcion, re.IGNORECASE)
        if match:
            codigo = match.group(1)
            # Normalizar: e.g. "c2" -> "C2", "sp5" -> "SP5"
            if tipo == "competencia_especifica":
                return codigo.upper()
            if tipo == "saber_pro":
                return codigo.upper()
            if tipo == "dimension":
                return codigo.upper()
            return codigo
    return None


def tiene_codigo_canonico(regla: dict) -> bool:
    return extraer_codigo_de_regla(regla) is not None


def _hallazgo(regla_id: str, regla_desc: str, cumple: bool, evidencia: str, correccion: str | None = None) -> dict:
    return {
        "regla_id": regla_id,
        "regla": regla_desc[:200],
        "estado": "CUMPLE" if cumple else "NO CUMPLE",
        "evidencia": evidencia,
        "correccion": correccion if not cumple else None,
    }


def verificar_declaraciones(
    reglas_aplicables: list[dict],
    declaraciones: dict[str, list[str]],
) -> list[dict]:
    """Produce hallazgos deterministicos comparando reglas vs declaraciones.

    Para cada regla con codigo canonico extraible:
    - Si el codigo esta en la lista de declaraciones correspondiente: CUMPLE.
    - Si no: NO CUMPLE.

    Reglas sin codigo canonico se omiten (caller las manda al LLM fallback).
    """
    hallazgos = []
    for regla in reglas_aplicables:
        codigo = extraer_codigo_de_regla(regla)
        if codigo is None:
            continue

        tipo = regla["tipo"]
        key = TIPO_A_KEY.get(tipo)
        declarados = set(declaraciones.get(key, []))

        cumple = codigo in declarados
        if cumple:
            evidencia = f"PDA declara {codigo} (detectado por extractor en seccion competencias/RAE)"
        else:
            evidencia = (
                f"PDA no declara {codigo}. Declaraciones encontradas para {key}: "
                f"{sorted(declarados) or 'ninguna'}"
            )
        correccion = f"Agregar declaracion explicita de {codigo} en la seccion correspondiente" if not cumple else None
        hallazgos.append(_hallazgo(regla["id"], regla["descripcion"], cumple, evidencia, correccion))
    return hallazgos


if __name__ == "__main__":
    # Quick unit test
    reglas_test = [
        {"id": "COMP-114", "tipo": "dimension", "descripcion": "debe declarar la dimension D1: Transdisciplinar"},
        {"id": "COMP-109", "tipo": "competencia_generica", "descripcion": "debe declarar la competencia generica 1j: Espiritu emprendedor"},
        {"id": "COMP-003", "tipo": "competencia_generica", "descripcion": "debe declarar la competencia generica 1g: Aprender a aprender"},
        {"id": "COMP-005", "tipo": "saber_pro", "descripcion": "debe declarar SABER PRO SP5: Ingles"},
    ]
    declaraciones_test = {
        "competencias_especificas": ["C1"],
        "competencias_genericas": ["1a", "1e", "1j"],
        "saber_pro": ["SP2"],
        "dimensiones": ["D1", "D6"],
        "abet": [],
    }

    for r in reglas_test:
        print(f"[{r['id']}] codigo extraido: {extraer_codigo_de_regla(r)}")

    print()
    hs = verificar_declaraciones(reglas_test, declaraciones_test)
    for h in hs:
        print(f"{h['regla_id']} -> {h['estado']}: {h['evidencia']}")

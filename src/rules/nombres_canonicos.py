"""
Catalogo central de nombres canonicos por codigo de competencia.

Fuente unica de verdad. Hoy la misma informacion esta duplicada en:
- src/prompts/extraccion_prompt.txt (para que el LLM infiera)
- src/generar_reglas.py (para construir la descripcion de reglas)

Este modulo centraliza la tabla para que el validador de declaraciones
pueda cruzar el snippet extraido contra el nombre canonico esperado,
sin depender del LLM ni del prompt.

Si la universidad agrega un nuevo codigo, solo se actualiza este archivo.
"""

from __future__ import annotations

# codigo -> lista de nombres canonicos validos (minimos; el validador
# tolera variaciones con acentos y case via normalizacion).
# Incluye variantes en espanol e ingles: PDAs bilingues (ej. programa de
# Agentes Inteligentes) usan los nombres en ingles; el validador no debe
# exigir una traduccion literal para aceptarlos como declaracion.
NOMBRES_CANONICOS: dict[str, list[str]] = {
    # Competencias especificas (las 3 primeras del curso; el nombre
    # completo es especifico al curso y viene en la descripcion de la regla,
    # asi que no las listamos aqui a nivel catalogo).

    # Competencias genericas (universales, 1a-1l).
    "1a": ["Comunicacion en lengua materna", "Communication in native language"],
    "1b": ["Comprension lectora en ingles", "Reading comprehension in English"],
    "1c": ["Comunicacion en segunda lengua", "Second language communication"],
    "1d": ["Pensamiento matematico", "Mathematical thinking"],
    "1e": ["Cultura cientifica y tecnologica", "Scientific and technological culture"],
    "1f": ["Ciudadania", "Citizenship"],
    "1g": ["Aprender a aprender", "Learning to learn"],
    "1h": ["Pensamiento critico", "Critical thinking"],
    "1i": ["Trabajo en equipo", "Teamwork"],
    "1j": ["Espiritu emprendedor", "Entrepreneurship"],
    "1k": ["Habilidades blandas", "Soft skills"],
    "1l": ["Pensamiento sistemico", "Systemic thinking"],

    # SABER PRO (SP1-SP5).
    "SP1": ["Comunicacion escrita", "Written communication"],
    "SP2": ["Lectura critica", "Critical reading"],
    "SP3": ["Razonamiento cuantitativo", "Quantitative reasoning"],
    "SP4": ["Competencias ciudadanas", "Citizenship competencies"],
    "SP5": ["Ingles", "English"],

    # Dimensiones (D1-D6).
    "D1": ["Transdisciplinar", "Transdisciplinary"],
    "D2": ["Etica", "Ethics"],
    "D3": ["Investigacion", "Research"],
    "D4": ["Internacional", "International"],
    "D5": ["Espiritu emprendedor", "Entrepreneurship"],
    "D6": ["Regional"],  # misma en EN
}


def normalizar_texto(texto: str) -> str:
    """Strip acentos + lowercase + colapsar whitespace y separadores
    tabulares para comparacion flexible.

    Wrapper thin sobre `common.text.normalizar(..., collapse_whitespace=True)`.
    Preservado como funcion modulo-local porque
    `src/rules/declaracion_extractor.py` la importa desde aqui.
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from common.text import normalizar
    return normalizar(texto, collapse_whitespace=True)


def nombre_canonico_en_snippet(codigo: str, snippet: str) -> bool:
    """True si algun nombre canonico del codigo aparece en el snippet
    (insensitive a acentos y case). Si el codigo no tiene catalogo
    (ej. C1/C2/C3 especificas del curso), devuelve False — esos solo
    se validan literalmente.
    """
    nombres = NOMBRES_CANONICOS.get(codigo, [])
    if not nombres:
        return False
    snippet_norm = normalizar_texto(snippet)
    return any(normalizar_texto(n) in snippet_norm for n in nombres)

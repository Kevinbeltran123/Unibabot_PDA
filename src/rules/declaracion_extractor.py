"""
Extractor de declaraciones de competencias de un PDA.

Una sola llamada al LLM (Qwen 2.5 14B) por PDA que produce JSON con
los codigos declarados (literales o por nombre canonico). Tarea de
extraccion, no de razonamiento: el LLM es fuerte en esto.

El output se usa con declaracion_checker.verificar_declaraciones()
para producir hallazgos determinista (set intersection).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ollama

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT = Path(__file__).parent.parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "extraccion_prompt.txt"

# Keywords que identifican secciones relevantes por nombre.
KEYWORDS_SECCIONES_RELEVANTES = [
    "competencia", "competence", "competency",
    "resultado", "result",
    "rae", "learning outcome",
    "aprendiz", "learning",
    "estrategia", "strategy",
    "pedagogic",
    "plan de estudios",
    "dimension",
    "saber pro", "saber-pro",
    "methodology", "methodolog",
    "professor", "profesor",  # caso Intelligent Agents
    "purpose", "proposito",
    "description", "descripcion",
    "context", "contexto",
]

# Fallback: si una seccion contiene codigos canonicos literales, incluir
# aunque no matchee keywords de nombre.
PATRON_CODIGO_EN_CONTENIDO = r"\b(C[1-9]|SP[1-5]|D[1-6]|1[a-l])\b|\bABET\b"

# Secciones a excluir siempre (no importa lo que contengan).
KEYWORDS_SECCIONES_EXCLUIR = [
    "bibliografia",
    "bibliography",
    "referencias",
    "references",
    "firmas",
    "reviewed and approved",
    "revisado y aprobado",
    "schedules and",
    "horarios y salones",
    "fecha del encuadre",
    "cronograma",  # largo y no aporta declaraciones
    "schedule",
]

# Codigos validos por tipo. Usamos sets para validacion rapida.
CODIGOS_VALIDOS = {
    "competencias_especificas": {f"C{i}" for i in range(1, 10)},
    "competencias_genericas": {f"1{c}" for c in "abcdefghijkl"},
    "saber_pro": {f"SP{i}" for i in range(1, 6)},
    "dimensiones": {f"D{i}" for i in range(1, 7)},
    # ABET son codigos X.Y variables; validamos con regex en vez de enumeracion.
}

DECLARACIONES_VACIAS: dict[str, list[str]] = {
    "competencias_especificas": [],
    "competencias_genericas": [],
    "saber_pro": [],
    "dimensiones": [],
    "abet": [],
}


def _seleccionar_texto_relevante(secciones: dict[str, str], max_chars: int = 9000) -> str:
    """Concatena secciones relevantes para el extractor.

    Estrategia en dos niveles:
    1. Inclusion por nombre: seccion cuyo nombre matchea keywords relevantes
       (competencia, resultado, estrategia, etc., bilingue).
    2. Fallback por contenido: seccion cuyo nombre no matchea pero cuyo
       contenido contiene codigos canonicos literales (C1, SP5, D4, etc.).
       Maneja PDAs donde el parser asigna contenido a secciones con
       nombres inesperados.

    Exclusiones duras (no pasan aunque contengan codigos):
    bibliografia, cronograma, firmas -- son largos y solo ruido.
    """
    # Dos listas: bloques con match de nombre (prioritarios) y bloques que
    # solo matchean por contenido (fallback). Se emiten en ese orden para que
    # si el budget max_chars se agota, lo haga en el fallback y no en un bloque
    # de alta relevancia. Necesario con Docling porque 'Informacion general'
    # puede contener 40K+ chars de tabla extraida que matchea el patron de
    # codigos canonicos por accidente (1a, C1, etc. dentro del texto).
    bloques_nombre = []
    bloques_fallback = []
    for nombre, contenido in secciones.items():
        nombre_norm = nombre.lower()

        if nombre == "PREAMBULO" or len(contenido) < 30:
            continue
        if any(kw in nombre_norm for kw in KEYWORDS_SECCIONES_EXCLUIR):
            continue

        if any(kw in nombre_norm for kw in KEYWORDS_SECCIONES_RELEVANTES):
            bloques_nombre.append(f"=== {nombre} ===\n{contenido}")
        elif re.search(PATRON_CODIGO_EN_CONTENIDO, contenido):
            # Fallback: extraer solo lineas con codigos + 1 linea de contexto.
            # Necesario con Docling porque "Informacion general" puede tener
            # 43K chars de tabla donde la unica info relevante (ej. fila
            # "Dimension: D1 ... D6") esta al medio. Volcar la seccion
            # entera truncaria los codigos antes de que lleguen al LLM.
            lineas = contenido.split("\n")
            relevantes = []
            for i, linea in enumerate(lineas):
                if re.search(PATRON_CODIGO_EN_CONTENIDO, linea):
                    if i > 0 and (not relevantes or relevantes[-1] != lineas[i - 1]):
                        relevantes.append(lineas[i - 1])
                    relevantes.append(linea)
            snippet = "\n".join(relevantes)
            if snippet:
                bloques_fallback.append(f"=== {nombre} (snippets) ===\n{snippet}")

    texto = "\n\n".join(bloques_nombre + bloques_fallback)
    if len(texto) > max_chars:
        texto = texto[:max_chars] + "\n...[texto truncado]"
    return texto


def _validar_codigo_abet(codigo: str) -> bool:
    return bool(re.fullmatch(r"\d+\.\d+", codigo))


def _limpiar_declaraciones(raw: dict) -> dict[str, list[str]]:
    """Filtra codigos invalidos que el LLM pudiera haber alucinado."""
    limpio = {k: [] for k in DECLARACIONES_VACIAS}
    for key in DECLARACIONES_VACIAS:
        items = raw.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, str):
                continue
            codigo = item.strip()
            if key == "abet":
                if _validar_codigo_abet(codigo):
                    limpio[key].append(codigo)
            else:
                if codigo in CODIGOS_VALIDOS.get(key, set()):
                    limpio[key].append(codigo)
        limpio[key] = sorted(set(limpio[key]))
    return limpio


def _extraer_json_de_respuesta(texto: str) -> dict | None:
    """Busca el primer bloque JSON en la respuesta del LLM."""
    # Normalizar: el LLM a veces devuelve {{...}} (sintaxis de template)
    # o bloques markdown ```json ... ```. Limpiar.
    limpio = texto.strip()
    if limpio.startswith("```"):
        limpio = re.sub(r"^```(?:json)?\s*", "", limpio)
        limpio = re.sub(r"\s*```\s*$", "", limpio)
    limpio = limpio.replace("{{", "{").replace("}}", "}")

    # Intentar como JSON directo
    try:
        return json.loads(limpio)
    except json.JSONDecodeError:
        pass
    # Buscar bloque {...} con braces balanceados
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", limpio, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def cargar_prompt() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def extraer_declaraciones(
    secciones: dict[str, str],
    modelo: str = "qwen2.5:14b",
) -> dict[str, list[str]]:
    """Extrae declaraciones de competencias del PDA en 1 LLM call.

    Returns un dict con las 5 listas de codigos. Vacias si el LLM falla
    (fallback robusto: mejor devolver "nada declarado" que alucinaciones).
    """
    texto_relevante = _seleccionar_texto_relevante(secciones)
    if not texto_relevante.strip():
        return dict(DECLARACIONES_VACIAS)

    template = cargar_prompt()
    prompt = template.replace("{texto_pda}", texto_relevante)

    try:
        response = ollama.chat(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.0,
                "num_predict": 600,
                "stop": ["<|eot_id|>", "<|end_of_text|>"],
            },
        )
        texto_respuesta = response["message"]["content"]
    except Exception as e:
        print(f"[extraer_declaraciones] Error LLM: {e}")
        return dict(DECLARACIONES_VACIAS)

    raw = _extraer_json_de_respuesta(texto_respuesta)
    if raw is None:
        print(f"[extraer_declaraciones] No se pudo parsear JSON. Respuesta: {texto_respuesta[:200]}")
        return dict(DECLARACIONES_VACIAS)

    return _limpiar_declaraciones(raw)


if __name__ == "__main__":
    # Smoke test
    from pdf_parser import parsear_pda
    import sys as _sys

    if len(_sys.argv) < 2:
        pdf = ROOT / "PDAs" / "PDA - Gestión TI 2026A.pdf"
    else:
        pdf = Path(_sys.argv[1])

    print(f"Extrayendo declaraciones de: {pdf.name}")
    secciones = parsear_pda(pdf)
    decl = extraer_declaraciones(secciones)
    print(json.dumps(decl, ensure_ascii=False, indent=2))

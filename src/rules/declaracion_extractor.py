"""
Extractor de declaraciones de competencias de un PDA.

Una sola llamada al LLM (Qwen 2.5 14B) por PDA que produce JSON con
codigos declarados + evidencia estructurada (snippet, seccion, tipo).
Un validador post-extraccion cruza la evidencia contra el texto real del
PDA y descarta alucinaciones o declaraciones en secciones no-formales.

El output se usa con declaracion_checker.verificar_declaraciones() para
producir hallazgos deterministas con evidencia auditable.

Formato de cada declaracion:
    {
        "codigo": "SP5",
        "snippet": "Saber PRO: Ingles",
        "seccion": "4. Resultados de Aprendizaje Esperados (RAE)",
        "tipo": "literal" | "nombre_canonico",
        "valida": bool,                  # llenado por validador
        "motivo_rechazo": str | None,    # llenado por validador si valida=False
    }
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import ollama

sys.path.insert(0, str(Path(__file__).parent.parent))

from rules.nombres_canonicos import nombre_canonico_en_snippet, normalizar_texto

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

# Secciones donde una declaracion formal de competencia es academicamente
# valida. Subset estricto de KEYWORDS_SECCIONES_RELEVANTES: ni "context",
# ni "proposito", ni "strategy/methodology" cuentan como seccion formal.
# "informacion general" SI cuenta: en la plantilla de la Universidad de
# Ibague la tabla de datos generales incluye una columna "Dimension" donde
# se codifican D1..D6 como parte de la ficha oficial del curso, y eso
# constituye declaracion formal para esos codigos.
KEYWORDS_SECCIONES_FORMALES = [
    "competencia", "competence", "competency",
    "resultado", "result",
    "rae", "learning outcome",
    "informacion general", "general information",
]

DECLARACIONES_VACIAS: dict[str, list[dict]] = {
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


def _codigo_valido_para_tipo(key: str, codigo: str) -> bool:
    """Codigo sintacticamente bien formado para su tipo."""
    if key == "abet":
        return _validar_codigo_abet(codigo)
    return codigo in CODIGOS_VALIDOS.get(key, set())


def _seccion_es_formal(nombre_seccion: str) -> bool:
    """True si el nombre de seccion matchea el whitelist de secciones
    formales de declaracion de competencias."""
    if not nombre_seccion:
        return False
    nombre_norm = normalizar_texto(nombre_seccion)
    return any(kw in nombre_norm for kw in KEYWORDS_SECCIONES_FORMALES)


def _seccion_formal_mas_cercana(
    seccion_reportada: str,
    secciones_pda: dict[str, str],
) -> tuple[str, str] | None:
    """Localiza la seccion en secciones_pda que mejor matchea la reportada
    Y es formal. Devuelve (nombre_real, contenido) o None.

    Tolera que el LLM truncue el nombre ("4. Resultados de Aprendizaje E")
    o lo varie levemente. El filtro adicional de seccion_es_formal asegura
    que no aceptemos cualquier seccion casual que comparta un substring.
    """
    if not seccion_reportada:
        return None
    rep_norm = normalizar_texto(seccion_reportada)
    # exact match si existe
    if seccion_reportada in secciones_pda and _seccion_es_formal(seccion_reportada):
        return seccion_reportada, secciones_pda[seccion_reportada]
    # match por substring normalizado
    for nombre, contenido in secciones_pda.items():
        nombre_norm = normalizar_texto(nombre)
        if rep_norm and (rep_norm in nombre_norm or nombre_norm in rep_norm):
            if _seccion_es_formal(nombre):
                return nombre, contenido
    return None


def _validar_declaracion(
    key: str,
    decl: dict,
    secciones_pda: dict[str, str],
    secciones_con_literales: set[str],
) -> tuple[bool, str | None]:
    """Checks sobre una declaracion extraida por el LLM.

    Returns (valida, motivo_rechazo). motivo_rechazo=None si valida.

    Pasos:
    1. Codigo bien formado para su tipo (descarta "XYZ" o codigos fuera
       del catalogo).
    2. Seccion elegible: debe matchear KEYWORDS_SECCIONES_FORMALES. Esto
       descarta declaraciones inferidas desde secciones de contexto o
       metodologia donde una mencion casual no cuenta como declaracion
       formal.
    3. Consistencia tipo ↔ snippet:
       - tipo="literal": el codigo string debe aparecer en el snippet
         (el LLM dice "aqui esta el codigo").
       - tipo="nombre_canonico": el nombre canonico del codigo debe
         aparecer en el snippet (tabla centralizada en nombres_canonicos).
    4. Verificacion contra texto real: la EVIDENCIA CLAVE (codigo o nombre
       canonico, segun tipo) debe aparecer literalmente en la seccion
       formal correspondiente del PDA. Esto rechaza alucinaciones donde
       el LLM inventa un codigo que no existe en el texto, pero tolera
       pequenas variaciones del LLM al sintetizar el snippet (ej. agregar
       prefijos de columna que no estaban en la celda real).
    """
    codigo = (decl.get("codigo") or "").strip()
    snippet = (decl.get("snippet") or "").strip()
    seccion = (decl.get("seccion") or "").strip()
    tipo = (decl.get("tipo") or "").strip().lower()

    if not _codigo_valido_para_tipo(key, codigo):
        return False, f"codigo '{codigo}' invalido para tipo {key}"

    if not snippet:
        return False, "sin snippet de evidencia"

    # Consistencia tipo ↔ snippet
    snippet_norm = normalizar_texto(snippet)
    codigo_norm = normalizar_texto(codigo)
    if tipo == "literal":
        if codigo_norm not in snippet_norm:
            return False, f"tipo=literal pero codigo '{codigo}' no esta en snippet"
    elif tipo == "nombre_canonico":
        if not nombre_canonico_en_snippet(codigo, snippet):
            return False, f"tipo=nombre_canonico pero nombre de '{codigo}' no esta en snippet"
    else:
        return False, f"tipo '{tipo}' desconocido"

    # Politica de seccion depende del tipo:
    # - Literal: el codigo string ES declaracion formal por si mismo,
    #   independientemente de donde aparezca (siempre que este en el PDA).
    # - Nombre canonico: cuenta como declaracion si aparece en una
    #   seccion formal (Competencias/RAE/Informacion general) O si la
    #   seccion ya contiene codigos literales (el PDA demuestra usar esa
    #   seccion para declaraciones formales, asi que nombres canonicos
    #   en esa misma seccion tambien cuentan).
    if tipo == "nombre_canonico" and not _seccion_es_formal(seccion):
        if seccion not in secciones_con_literales:
            return False, (
                f"nombre canonico en seccion no formal '{seccion[:60]}' "
                f"sin codigos literales que la legitimen"
            )

    # Verificacion contra texto real: la evidencia clave (codigo o nombre)
    # debe existir literalmente en la seccion reportada del PDA (o en alguna
    # seccion si la seccion reportada no se encuentra).
    contenido_relevante = secciones_pda.get(seccion, "")
    if not contenido_relevante:
        # fallback: buscar en todo el PDA concatenado (tolera que el LLM
        # reporte un nombre de seccion ligeramente distinto al real)
        contenido_relevante = "\n".join(secciones_pda.values())
    contenido_norm = normalizar_texto(contenido_relevante)

    if tipo == "literal":
        if not re.search(rf"(?<![\w]){re.escape(codigo_norm)}(?![\w])", contenido_norm):
            return False, f"codigo literal '{codigo}' no aparece en el PDA"
    else:  # nombre_canonico
        if not nombre_canonico_en_snippet(codigo, contenido_relevante):
            return False, f"nombre canonico de '{codigo}' no aparece en el PDA"

    return True, None


def _limpiar_declaraciones(
    raw: dict,
    secciones_pda: dict[str, str],
) -> dict[str, list[dict]]:
    """Procesa la respuesta cruda del LLM. Dos pasadas:

    1. Normaliza entradas y las convierte a dict con campos estandar.
    2. Computa `secciones_con_literales`: conjunto de secciones donde el PDA
       declara al menos un codigo literal. Estas secciones quedan
       "legitimadas" como secciones de declaracion formal para este PDA
       especifico — sin hardcodear que seccion es formal, lo infiere de
       la evidencia: si la seccion contiene literales, el PDA la usa
       para declarar competencias.
    3. Valida cada declaracion con ese contexto. Declaraciones invalidas
       se conservan con flag y motivo para que el matcher pueda emitir
       evidencia informativa en NO CUMPLE.
    """
    # Pasada 1: normalizar entradas
    todas_entradas: list[tuple[str, dict]] = []
    vistos: set[tuple[str, str, str]] = set()
    for key in DECLARACIONES_VACIAS:
        items = raw.get(key, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, str):
                item = {"codigo": item, "snippet": "", "seccion": "", "tipo": "literal"}
            if not isinstance(item, dict):
                continue
            decl = {
                "codigo": str(item.get("codigo", "")).strip(),
                "snippet": str(item.get("snippet", "")).strip(),
                "seccion": str(item.get("seccion", "")).strip(),
                "tipo": str(item.get("tipo", "literal")).strip().lower(),
            }
            dedupe = (key, decl["codigo"], decl["snippet"][:60])
            if dedupe in vistos:
                continue
            vistos.add(dedupe)
            todas_entradas.append((key, decl))

    # Pasada 2: identificar secciones con declaraciones literales verificadas
    # contra el texto. Esto es el signal data-driven: si la seccion tiene un
    # literal, el PDA usa esa seccion para declarar.
    secciones_con_literales: set[str] = set()
    for key, decl in todas_entradas:
        if decl["tipo"] != "literal":
            continue
        codigo_norm = normalizar_texto(decl["codigo"])
        snippet_norm = normalizar_texto(decl["snippet"])
        if not codigo_norm or codigo_norm not in snippet_norm:
            continue
        if not _codigo_valido_para_tipo(key, decl["codigo"]):
            continue
        # verificar que el codigo realmente aparece en la seccion reportada
        contenido = secciones_pda.get(decl["seccion"], "")
        if not contenido:
            continue
        contenido_norm = normalizar_texto(contenido)
        if re.search(rf"(?<![\w]){re.escape(codigo_norm)}(?![\w])", contenido_norm):
            secciones_con_literales.add(decl["seccion"])

    # Pasada 3: validacion final con contexto de secciones_con_literales
    limpio: dict[str, list[dict]] = {k: [] for k in DECLARACIONES_VACIAS}
    for key, decl in todas_entradas:
        valida, motivo = _validar_declaracion(
            key, decl, secciones_pda, secciones_con_literales
        )
        decl["valida"] = valida
        decl["motivo_rechazo"] = motivo
        limpio[key].append(decl)
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
) -> dict[str, list[dict]]:
    """Extrae declaraciones de competencias del PDA en 1 LLM call y
    las valida contra el texto del PDA.

    Returns un dict con 5 listas. Cada entrada es un dict con metadata
    (codigo, snippet, seccion, tipo, valida, motivo_rechazo). El matcher
    downstream decide CUMPLE/NO CUMPLE usando solo las validas, y usa las
    invalidas para enriquecer la evidencia del NO CUMPLE.

    Devuelve DECLARACIONES_VACIAS si el LLM falla o no emite JSON parseable.
    """
    texto_relevante = _seleccionar_texto_relevante(secciones)
    if not texto_relevante.strip():
        return {k: [] for k in DECLARACIONES_VACIAS}

    template = cargar_prompt()
    prompt = template.replace("{texto_pda}", texto_relevante)

    try:
        response = ollama.chat(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.0,
                "num_predict": 1200,  # schema enriquecido necesita mas tokens
                "stop": ["<|eot_id|>", "<|end_of_text|>"],
            },
        )
        texto_respuesta = response["message"]["content"]
    except Exception as e:
        print(f"[extraer_declaraciones] Error LLM: {e}")
        return {k: [] for k in DECLARACIONES_VACIAS}

    raw = _extraer_json_de_respuesta(texto_respuesta)
    if raw is None:
        print(f"[extraer_declaraciones] No se pudo parsear JSON. Respuesta: {texto_respuesta[:200]}")
        return {k: [] for k in DECLARACIONES_VACIAS}

    return _limpiar_declaraciones(raw, secciones)


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

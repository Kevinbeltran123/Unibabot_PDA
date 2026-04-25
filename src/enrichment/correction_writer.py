"""Generador de correccion prescriptiva enriquecida por LLM.

Para cada hallazgo NO CUMPLE, una llamada LLM produce texto literal
que el docente puede aplicar directamente al PDA. Mantiene la
correccion templada original (`hallazgo['correccion']`) intacta y
agrega el campo `correccion_enriquecida`.

Si la llamada LLM falla, el campo simplemente no se agrega: el
reporte sigue 100% usable con la correccion templada.

Anti-alucinacion:
- El prompt incluye la SECCION_ACTUAL del PDA (texto real) para que
  el LLM sugiera texto consistente con el estilo existente.
- El prompt prohibe inventar codigos no presentes en la regla.
- El validador de salida es trivial (texto plano, no JSON), pero
  filtra respuestas vacias o sospechosamente largas.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.exceptions import LLMError
from common.logging_config import get_logger
from common.ollama_client import chat as llm_chat
from enrichment.cache import cache_get, cache_put, compute_cache_key
from rag.rule_dispatcher import cargar_reglas
from rag.seccion_mapping import secciones_pda_validas
from rules.declaracion_checker import extraer_codigo_de_regla

logger = get_logger(__name__)

ROOT = Path(__file__).parent.parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "correccion_prescriptiva.txt"

# Limite superior para la respuesta LLM. Si excede, se descarta como
# probable hallucinacion / loop. El prompt pide max 3 oraciones.
MAX_RESPUESTA_CHARS = 1200
# Limite inferior: respuestas demasiado cortas no aportan valor.
MIN_RESPUESTA_CHARS = 30


def _cargar_prompt() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _buscar_regla(regla_id: str) -> dict | None:
    """Busca el dict completo de la regla en reglas.json por id.

    Devuelve None si no se encuentra (pasa cuando regla_id es de un
    hallazgo estructural EST-* que no esta en reglas.json o cuando el
    matcher uso un id sintetico).
    """
    for r in cargar_reglas():
        if r.get("id") == regla_id:
            return r
    return None


def _seleccionar_contexto_seccion(
    seccion_destino_esperada: str,
    secciones: dict[str, str],
) -> tuple[str, str]:
    """Encuentra la seccion del PDA que corresponde a seccion_destino.

    Usa el inverso del MAPPING_SECCIONES: para cada seccion real del
    PDA, calcula que valores `seccion_pda` validos puede asumir, y
    matchea contra el target.

    Returns:
        (nombre_seccion_real, texto_seccion). Si no hay match, devuelve
        ("(no encontrada)", marker explicativo).
    """
    if not seccion_destino_esperada:
        return ("(no aplica)", "(esta regla no tiene seccion destino especifica)")

    for nombre_real, texto in secciones.items():
        validas = secciones_pda_validas(nombre_real) or []
        if seccion_destino_esperada in validas:
            # Truncamos a 2000 chars: contexto suficiente para style
            # reference sin saturar el prompt.
            return (nombre_real, texto[:2000])

    return (
        "(no encontrada)",
        f"(el PDA no contiene una seccion mapeable a '{seccion_destino_esperada}')",
    )


def enriquecer_correccion(
    hallazgo: dict,
    secciones: dict[str, str],
    modelo: str,
) -> str | None:
    """Una llamada LLM produce correccion prescriptiva. Cacheada en disco.

    Devuelve None si:
    - El hallazgo no es NO CUMPLE (no tiene sentido enriquecer CUMPLE).
    - La regla no tiene codigo canonico extraible.
    - La llamada LLM falla.
    - La respuesta esta vacia, demasiado corta o demasiado larga.

    None es la senal para el caller de NO agregar el campo
    `correccion_enriquecida` al hallazgo.
    """
    if hallazgo.get("estado") != "NO CUMPLE":
        return None

    regla_id = hallazgo.get("regla_id", "")
    regla = _buscar_regla(regla_id)
    if regla is None:
        # Hallazgos estructurales (EST-*) no estan en reglas.json y no
        # tienen codigo canonico. Skip por ahora.
        logger.debug("enriquecer_skip_regla_no_encontrada", regla_id=regla_id)
        return None

    codigo_canonico = extraer_codigo_de_regla(regla)
    if codigo_canonico is None:
        logger.debug("enriquecer_skip_sin_codigo_canonico", regla_id=regla_id)
        return None

    seccion_destino_esperada = regla.get("seccion_pda", "")
    nombre_real, contexto = _seleccionar_contexto_seccion(
        seccion_destino_esperada, secciones,
    )

    template = _cargar_prompt()

    # Cache key: cualquier cambio en estos inputs invalida la entrada.
    cache_key = compute_cache_key(
        "correccion_v1",
        modelo,
        template,
        regla_id,
        codigo_canonico,
        hallazgo.get("evidencia", ""),
        seccion_destino_esperada,
        contexto,
    )
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("correccion_cache_hit", regla_id=regla_id, key=cache_key[:12])
        return cached if isinstance(cached, str) else None

    prompt = template.format(
        regla=regla.get("descripcion", hallazgo.get("regla", "")),
        codigo_canonico=codigo_canonico,
        evidencia=hallazgo.get("evidencia", ""),
        seccion_destino_esperada=seccion_destino_esperada or "(no especificada)",
        seccion_actual=contexto,
    )

    try:
        respuesta = llm_chat(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.1,
                "num_predict": 400,
            },
        )
    except LLMError as e:
        logger.warning("correccion_llm_fail", regla_id=regla_id, error=str(e))
        return None

    texto = respuesta.strip()
    if len(texto) < MIN_RESPUESTA_CHARS:
        logger.warning(
            "correccion_respuesta_corta", regla_id=regla_id, len=len(texto),
        )
        return None
    if len(texto) > MAX_RESPUESTA_CHARS:
        logger.warning(
            "correccion_respuesta_larga", regla_id=regla_id, len=len(texto),
        )
        # Truncamos pero conservamos. Mejor algo recortado que nada.
        texto = texto[:MAX_RESPUESTA_CHARS].rsplit(".", 1)[0] + "."

    cache_put(
        cache_key,
        texto,
        metadata={
            "modelo": modelo,
            "regla_id": regla_id,
            "codigo": codigo_canonico,
            "seccion_real_usada": nombre_real,
        },
    )
    logger.info(
        "correccion_generated",
        regla_id=regla_id,
        codigo=codigo_canonico,
        seccion=nombre_real,
        chars=len(texto),
    )
    return texto

"""Generador de resumenes ejecutivo + didactico para un reporte completo.

Una sola llamada LLM por PDA produce ambos resumenes en un dict
{oficina, docente}. Validacion via schemas.Resumenes; cache en disco
para idempotencia bit-a-bit cuando los inputs no cambian.

Si la llamada LLM o el parseo fallan, devuelve None: el reporte
continua sin el campo `resumenes`. El pipeline NO aborta.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.exceptions import LLMError
from common.logging_config import get_logger
from common.ollama_client import chat as llm_chat
from enrichment.cache import cache_get, cache_put, compute_cache_key
from schemas import Resumenes

logger = get_logger(__name__)

ROOT = Path(__file__).parent.parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "resumenes.txt"


def _cargar_prompt() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _extraer_hallazgos_planos(reporte: dict) -> list[dict]:
    """Aplana todos los hallazgos del reporte en una lista plana.

    Ignora campos non-deterministicos del reporte (modelo, archivo path).
    El orden se preserva tal como agent.py los inserto en `resultados`.
    """
    hallazgos = []
    for resultado in reporte.get("resultados", []):
        for h in resultado.get("hallazgos", []):
            hallazgos.append(h)
    return hallazgos


def _formatear_lista_no_cumple(hallazgos: list[dict]) -> str:
    """Formatea las entradas NO CUMPLE para inyectar en el prompt.

    Cada linea: "- [regla_id] regla. Evidencia: ..."
    Si no hay NO CUMPLE: devuelve "(ninguna no conformidad)".
    """
    no_cumple = [h for h in hallazgos if h.get("estado") == "NO CUMPLE"]
    if not no_cumple:
        return "(ninguna no conformidad)"

    lineas = []
    for h in no_cumple:
        regla_id = h.get("regla_id", "?")
        regla = h.get("regla", "")
        evidencia = h.get("evidencia", "")
        lineas.append(f"- [{regla_id}] {regla}. Evidencia: {evidencia}")
    return "\n".join(lineas)


def _serializar_hallazgos_canonico(hallazgos: list[dict]) -> str:
    """Serializacion estable para el cache key.

    Solo incluye campos que afectan el output del LLM (regla_id, estado,
    evidencia, correccion). Ordena por regla_id para que el orden de
    iteracion en agent.py no afecte la key.
    """
    canonico = sorted(
        [
            {
                "regla_id": h.get("regla_id", ""),
                "estado": h.get("estado", ""),
                "evidencia": h.get("evidencia", ""),
                "correccion": h.get("correccion") or "",
            }
            for h in hallazgos
        ],
        key=lambda x: x["regla_id"],
    )
    return json.dumps(canonico, ensure_ascii=False, sort_keys=True)


def generar_resumenes(
    reporte: dict,
    modelo: str,
) -> dict | None:
    """Una llamada LLM produce {oficina: str, docente: str}.

    Args:
        reporte: el dict producido por agent.analizar_pda hasta el
            momento (con `resultados` ya completo).
        modelo: nombre del modelo ollama (ej. "qwen2.5:14b").

    Returns:
        Dict {oficina, docente} si el LLM responde y el JSON valida
        contra schemas.Resumenes. None si algo falla.
    """
    template = _cargar_prompt()
    hallazgos = _extraer_hallazgos_planos(reporte)
    cumple_count = sum(1 for h in hallazgos if h.get("estado") == "CUMPLE")
    no_cumple_count = sum(1 for h in hallazgos if h.get("estado") == "NO CUMPLE")
    total_reglas = cumple_count + no_cumple_count
    codigo_curso = reporte.get("codigo_curso") or "(sin codigo)"

    # Cache key: model + prompt content + canonical hallazgos + codigo
    cache_key = compute_cache_key(
        "resumenes_v1",
        modelo,
        template,
        codigo_curso,
        _serializar_hallazgos_canonico(hallazgos),
    )
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("resumenes_cache_hit", key=cache_key[:12])
        return cached

    prompt = template.format(
        codigo_curso=codigo_curso,
        total_reglas=total_reglas,
        cumple_count=cumple_count,
        no_cumple_count=no_cumple_count,
        lista_no_cumple=_formatear_lista_no_cumple(hallazgos),
    )

    try:
        respuesta = llm_chat(
            model=modelo,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": 0.1,
                "num_predict": 800,
            },
        )
    except LLMError as e:
        logger.warning("resumenes_llm_fail", error=str(e))
        return None

    # Extraer y validar JSON.
    try:
        inicio = respuesta.find("{")
        fin = respuesta.rfind("}") + 1
        if inicio < 0 or fin <= inicio:
            logger.warning("resumenes_no_json", respuesta_preview=respuesta[:200])
            return None
        data = json.loads(respuesta[inicio:fin])
        validado = Resumenes(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning("resumenes_parse_fail", error=str(e))
        return None

    resultado = validado.model_dump()
    cache_put(
        cache_key,
        resultado,
        metadata={
            "modelo": modelo,
            "codigo_curso": codigo_curso,
            "no_cumple_count": no_cumple_count,
        },
    )
    logger.info("resumenes_generated", key=cache_key[:12], no_cumple=no_cumple_count)
    return resultado

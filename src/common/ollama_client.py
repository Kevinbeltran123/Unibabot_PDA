"""
Wrapper tipado para ollama.Client.chat con timeout y excepciones
especificas.

En vez de `except Exception` amplio en los call sites, este modulo
traduce errores genericos (ConnectionError, TimeoutException,
ResponseError) a los tipos definidos en `common.exceptions`:

- LLMUnavailableError: ollama no corre / modelo no instalado (fatal).
- LLMTimeoutError: LLM excedio el timeout (recuperable con reintento).
- LLMResponseError: LLM devolvio algo que no podemos usar (recuperable).

Config via env var: UNIBABOT_LLM_TIMEOUT (default 120s).
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Sequence

import httpx
import ollama

from .exceptions import (
    LLMResponseError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from .logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = int(os.environ.get("UNIBABOT_LLM_TIMEOUT", "120"))


def chat(
    model: str,
    messages: Sequence[Mapping[str, Any]],
    options: Mapping[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    host: str | None = None,
) -> str:
    """Llama `ollama.chat` con timeout y traduce errores a excepciones tipadas.

    Returns:
        El content del response (`response.message.content`).

    Raises:
        LLMUnavailableError: ollama no responde o el modelo no esta
            instalado. Incluye mensaje accionable al usuario.
        LLMTimeoutError: la llamada tardo mas de `timeout` segundos.
        LLMResponseError: respuesta sin content o JSON mal formado.
    """
    opts = dict(options or {})
    logger.debug(
        "llm_request",
        model=model,
        timeout_s=timeout,
        option_keys=list(opts.keys()),
    )

    try:
        client = ollama.Client(host=host, timeout=httpx.Timeout(timeout))
        response = client.chat(model=model, messages=messages, options=opts)
    except ollama.ResponseError as e:
        msg = str(e).lower()
        if "not found" in msg or "pull" in msg or "does not exist" in msg:
            raise LLMUnavailableError(
                f"Modelo '{model}' no esta instalado en ollama. "
                f"Ejecutar: ollama pull {model}"
            ) from e
        raise LLMResponseError(f"ollama rechazo la request: {e}") from e
    except (httpx.ConnectError, ConnectionError) as e:
        # El SDK de ollama traduce httpx.ConnectError a builtin
        # ConnectionError internamente (ver ollama._client._request_raw).
        raise LLMUnavailableError(
            "ollama no responde. Verificar que `ollama serve` este corriendo."
        ) from e
    except httpx.TimeoutException as e:
        raise LLMTimeoutError(
            f"ollama excedio timeout de {timeout}s para modelo '{model}'. "
            f"Considerar aumentar UNIBABOT_LLM_TIMEOUT o revisar carga del host."
        ) from e

    # El response puede ser un ChatResponse con atributo .message o
    # un dict legacy; normalizamos acceso.
    try:
        content = (
            response.message.content
            if hasattr(response, "message")
            else response.get("message", {}).get("content")
        )
    except AttributeError as e:
        raise LLMResponseError(f"Respuesta ollama inesperada: {e}") from e

    if not content:
        raise LLMResponseError("Respuesta ollama sin 'message.content'")

    return content

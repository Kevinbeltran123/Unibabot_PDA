"""
Logging estructurado con structlog.

Provee:
- `setup_logging()`: configuracion idempotente del logger con nivel y
  formato (ConsoleRenderer con colores para dev, JSONRenderer para prod)
  controlados por variables de entorno.
- `get_logger(name)`: obtiene un logger con namespace `unibabot.<name>`.
- `@timed(event)`: decorator que mide duracion y loggea `<event>_done`
  con `duration_s` o `<event>_failed` con exception info.

Variables de entorno:
- UNIBABOT_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR (default INFO)
- UNIBABOT_LOG_JSON: 1 para JSONRenderer, cualquier otro valor usa
  ConsoleRenderer (default dev-friendly)
"""

from __future__ import annotations

import logging
import os
import sys
import time
from functools import wraps
from typing import Callable, TypeVar

import structlog

_CONFIGURED = False

F = TypeVar("F", bound=Callable)


def setup_logging(
    level: str | None = None,
    json_output: bool | None = None,
) -> None:
    """Configura structlog. Idempotente: invocaciones repetidas son no-op."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = (level or os.environ.get("UNIBABOT_LOG_LEVEL", "INFO")).upper()
    if json_output is None:
        json_output = os.environ.get("UNIBABOT_LOG_JSON") == "1"

    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    if json_output:
        processors.append(structlog.processors.JSONRenderer(ensure_ascii=False))
    else:
        processors.append(
            structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level, logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    _CONFIGURED = True


def get_logger(name: str | None = None):
    """Obtiene un logger con namespace `unibabot.<name>`.

    Si `name` ya empieza con `unibabot`, se usa tal cual. De lo contrario
    se prefija para que todos los logs del proyecto queden bajo un
    namespace comun y sean filtrables.
    """
    if name and not name.startswith("unibabot"):
        name = f"unibabot.{name}"
    return structlog.get_logger(name or "unibabot")


def timed(event: str) -> Callable[[F], F]:
    """Decorator que mide duracion de la funcion y emite evento estructurado.

    Sobre success: `logger.info("<event>_done", duration_s=<float>)`.
    Sobre exception: `logger.exception("<event>_failed", duration_s=<float>)`
    y re-raise (no tragamos la excepcion).
    """
    def decorator(fn: F) -> F:
        log = get_logger(fn.__module__)

        @wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = fn(*args, **kwargs)
                log.info(
                    f"{event}_done",
                    duration_s=round(time.monotonic() - start, 3),
                )
                return result
            except Exception:
                log.exception(
                    f"{event}_failed",
                    duration_s=round(time.monotonic() - start, 3),
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator

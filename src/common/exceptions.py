"""
Jerarquia de excepciones tipadas para el pipeline UnibaBot PDA.

Usar en vez de `Exception` generico para que los callers puedan:
- Distinguir fallos recuperables (ej. LLMResponseError: devolver vacio)
  de fatales (ej. LLMUnavailableError: abortar el PDA).
- Atrapar por categoria con `except LLMError` o `except UnibabotError`.
- Dar mensajes accionables al auditor (p.ej. "correr ollama serve").
"""

from __future__ import annotations


class UnibabotError(Exception):
    """Base para todos los errores del pipeline unibabot.

    Callers externos (ej. evaluate.py) pueden capturar esta clase para
    distinguir errores del pipeline de errores genericos de Python.
    """


class LLMError(UnibabotError):
    """Errores relacionados con el LLM (ollama, modelo, respuesta)."""


class LLMUnavailableError(LLMError):
    """ollama no responde o el modelo solicitado no esta instalado.

    Mensaje tipico: "correr `ollama serve`" o "correr `ollama pull X`".
    Es fatal: el pipeline no puede continuar sin LLM funcional.
    """


class LLMTimeoutError(LLMError):
    """El LLM excedio el timeout configurado.

    Puede indicar prompt demasiado largo, modelo bajo carga, o un
    problema con el host. Recuperable devolviendo resultado vacio pero
    worth investigar.
    """


class LLMResponseError(LLMError):
    """El LLM devolvio una respuesta invalida.

    Casos: JSON mal formado, schema incorrecto, message.content vacio.
    Generalmente recuperable devolviendo resultado vacio (el caller
    decide).
    """


class PDFParseError(UnibabotError):
    """Docling fallo al parsear el PDF.

    Casos: PDF corrupto, demasiado grande para la memoria disponible,
    formato no soportado, OCR fallido cuando esta habilitado.
    """

"""
Normalizacion canonica de texto para comparacion.

Funcion unica con flags que consolida las 3 variantes que existian
dispersas en el codebase:

- pdf_parser.normalizar (strip_numbering=True): para nombres de seccion
  del PDA, que suelen venir con prefijos "1." "2)" "3. ".
- seccion_mapping.normalizar_nombre (sin flags): para matching de keywords
  contra nombres normalizados, donde los numeros son parte del nombre.
- nombres_canonicos.normalizar_texto (collapse_whitespace=True): para
  comparar snippets LLM contra texto extraido de tablas markdown, donde
  los pipes y whitespace pueden diferir.
"""

from __future__ import annotations

import re

_ACCENTS: dict[str, str] = {
    "á": "a",
    "é": "e",
    "í": "i",
    "ó": "o",
    "ú": "u",
    "ñ": "n",
}


def normalizar(
    texto: str,
    *,
    strip_numbering: bool = False,
    collapse_whitespace: bool = False,
) -> str:
    """Normaliza texto para comparacion tolerante.

    Siempre aplica: lowercase + strip + remocion de acentos.

    Flags (aditivos, independientes):
    - strip_numbering: remueve prefijos "1." "2)" "3. " al inicio del texto.
      Usa para matching de nombres de seccion cuando el prefijo numerico
      no es semanticamente relevante.
    - collapse_whitespace: trata pipes (|) y tabs como whitespace y colapsa
      cualquier secuencia de whitespace a un solo espacio. Usa para comparar
      snippets LLM contra texto de tablas markdown, donde la estructura de
      celdas introduce pipes y saltos de linea.
    """
    texto = texto.lower().strip()
    if strip_numbering:
        texto = re.sub(r"^\d+[.)]\s*", "", texto)
    for orig, rep in _ACCENTS.items():
        texto = texto.replace(orig, rep)
    if collapse_whitespace:
        texto = re.sub(r"[|\t]+", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
    return texto

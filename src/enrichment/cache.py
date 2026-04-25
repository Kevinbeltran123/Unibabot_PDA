"""Cache en disco para outputs LLM de enrichment.

Decision arquitectonica: SHA-256 sobre inputs canonicos como key.
Cualquier cambio en modelo, prompt template o input invalida la
entrada automaticamente. Esto da reproducibilidad bit-a-bit cuando
nada cambia, y cache miss limpio cuando algo cambia.

Estructura en disco:
    cache/enrichment/<key>.json
        { "value": str | dict, "metadata": {...} }

Escritura atomica: tmp + rename para evitar lecturas parciales si
dos procesos corren en paralelo.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.logging_config import get_logger

logger = get_logger(__name__)

ROOT = Path(__file__).parent.parent.parent
CACHE_DIR = ROOT / "cache" / "enrichment"


def compute_cache_key(*parts: str | bytes) -> str:
    """Hash SHA-256 de la concatenacion de todas las partes.

    Cada parte puede ser str (se codifica utf-8) o bytes. Las partes
    se separan por b'\\x00' para evitar colisiones por concatenacion
    accidental ("ab" + "c" vs "a" + "bc").

    Returns:
        Hex digest de 64 chars, usable como nombre de archivo.
    """
    h = hashlib.sha256()
    for i, p in enumerate(parts):
        if i > 0:
            h.update(b"\x00")
        if isinstance(p, str):
            h.update(p.encode("utf-8"))
        elif isinstance(p, bytes):
            h.update(p)
        else:
            raise TypeError(f"compute_cache_key: parte {i} no es str/bytes: {type(p)}")
    return h.hexdigest()


def _ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_get(key: str) -> Any | None:
    """Lee cache/enrichment/<key>.json. Devuelve el valor o None.

    No lanza excepciones: cualquier IOError, JSON corrupto, etc.,
    se trata como cache miss y se loguea como warning.
    """
    path = CACHE_DIR / f"{key}.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            entry = json.load(f)
        return entry.get("value")
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("cache_read_fail", key=key[:12], error=str(e))
        return None


def cache_put(key: str, value: Any, metadata: dict | None = None) -> None:
    """Escribe atomicamente cache/enrichment/<key>.json.

    Usa tmp + rename para evitar lecturas parciales por procesos
    concurrentes. No lanza si la escritura falla; loguea warning.
    """
    _ensure_cache_dir()
    path = CACHE_DIR / f"{key}.json"
    entry = {"value": value, "metadata": metadata or {}}
    try:
        # delete=False para que el archivo persista despues del close;
        # luego renombramos atomicamente sobre el target.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=CACHE_DIR,
            prefix=f".{key[:12]}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            json.dump(entry, tmp, ensure_ascii=False, indent=2)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, path)
    except OSError as e:
        logger.warning("cache_write_fail", key=key[:12], error=str(e))

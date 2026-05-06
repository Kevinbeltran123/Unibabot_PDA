"""Rate limiter minimo basado en Redis INCR + EXPIRE.

Buckets por minuto: la primera llamada en una ventana setea el contador a
1 con expiracion de 60s; subsiguientes incrementan. Si el contador supera
`max_requests` antes de que expire la clave, denegamos.

No depende de slowapi para mantener el footprint pequeno. Falla abierto
(allow) si Redis esta caido para no romper la API por un blip de cache.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("unibabot.rate_limit")


def check_rate_limit(
    redis_client,
    key: str,
    max_requests: int,
    window_seconds: int = 60,
) -> bool:
    """Devuelve True si el request esta permitido, False si excede.

    `redis_client` es el cliente sincrono de redis-py. Intencionalmente no
    fuerza tipo: tests pueden inyectar un fake con la misma interfaz.
    """
    full_key = f"ratelimit:{key}"
    try:
        count = redis_client.incr(full_key)
        if count == 1:
            redis_client.expire(full_key, window_seconds)
        return count <= max_requests
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate_limit_redis_error", extra={"error": str(exc)})
        return True

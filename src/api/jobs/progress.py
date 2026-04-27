"""Publisher de eventos de progreso a Redis pub/sub.

Implementa la firma `ProgressCallback` (ver src/agent.py:62) y publica
cada evento como un JSON al canal `analysis:{id}`. El endpoint SSE en
routes/analyses.py se suscribe al canal y reenvia los eventos al cliente.
"""

import json
from typing import Any

import redis


class RedisProgressPublisher:
    """Callable compatible con `ProgressCallback`.

    Cada evento se publica al canal `analysis:{analysis_id}` Y se anade
    a una lista `analysis:{analysis_id}:history` para que un cliente que
    se conecte tarde pueda recuperar lo perdido.
    """

    def __init__(self, redis_url: str, analysis_id: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._channel = f"analysis:{analysis_id}"
        self._history_key = f"{self._channel}:history"

    def __call__(self, event: str, data: dict[str, Any]) -> None:
        payload = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        pipe = self._client.pipeline()
        pipe.rpush(self._history_key, payload)
        pipe.expire(self._history_key, 60 * 60 * 24)  # 24h TTL
        pipe.publish(self._channel, payload)
        pipe.execute()

"""Entry point del worker RQ.

Uso:
    python -m src.api.jobs.worker

El worker corre en proceso separado de la API. Procesa jobs encolados
con `enqueue_analysis`. Si el sistema corre en modo sincrono (UNIBABOT_API_SYNC_MODE=1),
no se necesita worker.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    from rq import Worker

    from src.api.config import get_settings
    from src.api.db import init_db
    from src.api.jobs.queue import get_queue, get_redis

    init_db()
    settings = get_settings()
    print(f"[worker] cola={settings.rq_queue_name} redis={settings.redis_url}")
    worker = Worker([get_queue()], connection=get_redis())
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()

"""Entry point del worker RQ.

Uso:
    python -m src.api.jobs.worker

El worker corre en proceso separado de la API. Procesa jobs encolados
con `enqueue_analysis`.

Seleccion de WorkerCls por plataforma:

- macOS (Darwin): SimpleWorker. Las librerias Cocoa-bound de Docling /
  torch / numpy crashean con `os.fork()` (objc fork-safety).
- Windows: SimpleWorker. Windows no soporta `os.fork()` en absoluto.
  Recomendado: en Windows levantar el stack con `docker-compose up` para
  que el worker corra en un contenedor Linux (fork natural) sin las
  limitaciones del sistema host.
- Linux: Worker estandar. Forkear es lo normal y mas eficiente.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    from rq import SimpleWorker, Worker

    from src.api.config import get_settings
    from src.api.db import init_db
    from src.api.jobs.queue import get_queue, get_redis

    init_db()
    settings = get_settings()

    sistema = platform.system()
    WorkerCls = SimpleWorker if sistema in ("Darwin", "Windows") else Worker
    print(
        f"[worker] cola={settings.rq_queue_name} redis={settings.redis_url} "
        f"sistema={sistema} using={WorkerCls.__name__}"
    )
    worker = WorkerCls([get_queue()], connection=get_redis())
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()

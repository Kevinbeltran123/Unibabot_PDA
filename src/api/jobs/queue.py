"""RQ queue factory + helper para encolar analisis."""

from functools import lru_cache

import redis
from rq import Queue

from ..config import get_settings


@lru_cache
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url)


@lru_cache
def get_queue() -> Queue:
    settings = get_settings()
    return Queue(
        name=settings.rq_queue_name,
        connection=get_redis(),
        default_timeout=settings.rq_job_timeout_s,
    )


def enqueue_analysis(analysis_id: str) -> str:
    """Encola la tarea `run_analysis` y retorna el job_id de RQ.

    El analysis_id se usa tambien como job_id para garantizar idempotencia
    (no se encolan dos jobs para el mismo analisis si el caller reintenta).
    """
    from .tasks import run_analysis

    settings = get_settings()
    job = get_queue().enqueue(
        run_analysis,
        analysis_id,
        job_id=analysis_id,
        result_ttl=settings.rq_result_ttl_s,
        failure_ttl=settings.rq_result_ttl_s,
    )
    return job.id

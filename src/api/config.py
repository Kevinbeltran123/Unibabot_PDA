"""Configuracion del backend leida desde variables de entorno.

Convencion: nombres prefijados `UNIBABOT_API_` salvo los estandar
(DATABASE_URL, REDIS_URL) que respetan la convencion del ecosistema.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Settings tipados. Cualquier campo se sobreescribe via env var."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = f"sqlite:///{ROOT / 'data' / 'unibabot.db'}"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-only-change-me-with-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: str = "http://localhost:3000"

    uploads_dir: Path = ROOT / "tmp" / "uploads"
    reports_dir: Path = ROOT / "data" / "reports"

    max_upload_mb: int = 20

    rq_queue_name: str = "unibabot"
    rq_job_timeout_s: int = 60 * 30
    rq_result_ttl_s: int = 60 * 60 * 24

    sync_mode: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    return settings

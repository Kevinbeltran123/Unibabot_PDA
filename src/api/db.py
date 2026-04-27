"""SQLAlchemy 2.x setup: engine, session factory, declarative base."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

settings = get_settings()

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """Crea las tablas si no existen. Llamado al arrancar la app."""
    from . import models  # noqa: F401  garantiza registro en metadata

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """Dependency de FastAPI: yield una session y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

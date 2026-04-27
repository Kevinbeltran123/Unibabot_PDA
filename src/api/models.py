"""Modelos SQLAlchemy: usuarios y analisis.

Los reportes JSON viven en disco (`data/reports/`); aqui solo guardamos
metadata indexable y status del job.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Analysis(Base):
    """Una corrida de `analizar_pda` para un usuario.

    Estados validos: pending, running, done, failed.
    """

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    pdf_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    codigo_curso: Mapped[str | None] = mapped_column(String(20), default=None)
    modelo: Mapped[str] = mapped_column(String(100), default="qwen2.5:14b", nullable=False)
    dispatcher: Mapped[str] = mapped_column(String(20), default="rule", nullable=False)
    top_k: Mapped[int] = mapped_column(default=5, nullable=False)
    enriquecer: Mapped[bool] = mapped_column(default=False, nullable=False)
    generar_resumen: Mapped[bool] = mapped_column(default=False, nullable=False)

    report_path: Mapped[str | None] = mapped_column(String(500), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    duration_s: Mapped[float | None] = mapped_column(Float, default=None)

    user: Mapped["User"] = relationship(back_populates="analyses")

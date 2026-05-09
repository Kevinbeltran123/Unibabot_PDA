"""Tipos personalizados de SQLAlchemy.

`UtcDateTime` normaliza el contrato de fechas frente a SQLite, que descarta
el offset al persistir. Centraliza la garantia de que todo datetime que
sale del ORM lleva tzinfo=UTC, eliminando la ambiguedad ISO 8601 sin offset
que JavaScript interpreta como hora local.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """DateTime que garantiza tzinfo=UTC al cruzar la frontera del ORM.

    Contrato:
    - Escritura: rechaza datetimes naive. Forzar al codigo de aplicacion a
      ser explicito previene insertar datos ambiguos. Si llega un datetime
      con offset distinto, se normaliza a UTC.
    - Lectura: si la DB devuelve naive (SQLite descarta offset al guardar),
      se asume UTC. Es seguro porque toda escritura paso por el bind, que
      ya valido tzinfo.

    Si en el futuro se migra a Postgres (timestamptz), el decorator sigue
    siendo correcto: `astimezone(utc)` es identidad para valores ya en UTC.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "UtcDateTime no acepta datetimes naive. "
                "Usa datetime.now(timezone.utc) o .astimezone(timezone.utc)."
            )
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

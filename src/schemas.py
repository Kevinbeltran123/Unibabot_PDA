"""
Schemas Pydantic para validacion estricta de la salida del LLM.

Se usan en agent.py dentro de parsear_y_validar_o_reintentar() para
garantizar que cada respuesta del LLM tenga la estructura esperada
antes de incluirla en el reporte.
"""

from typing import Literal
from pydantic import BaseModel, field_validator


class Hallazgo(BaseModel):
    """Una evaluacion de cumplimiento para una regla especifica."""

    regla_id: str
    regla: str
    estado: Literal["CUMPLE", "NO CUMPLE"]
    evidencia: str
    correccion: str | None = None

    @field_validator("correccion", mode="before")
    @classmethod
    def _normalizar_null(cls, v):
        """Acepta tanto None como la cadena 'null' (el baseline a veces la emite)."""
        if v in ("null", "", "None", None):
            return None
        return v

    @field_validator("estado", mode="before")
    @classmethod
    def _normalizar_estado(cls, v):
        """Acepta variaciones como 'Cumple', 'no cumple', 'NOT COMPLIANT', etc."""
        if isinstance(v, str):
            v = v.strip().upper()
            if v in ("CUMPLE", "YES", "SI", "COMPLIANT"):
                return "CUMPLE"
            if v in ("NO CUMPLE", "NO", "NOT COMPLIANT", "NO-CUMPLE", "NONCUMPLE"):
                return "NO CUMPLE"
        return v


class ReporteSeccion(BaseModel):
    """Evaluacion completa de una seccion del PDA."""

    seccion: str
    hallazgos: list[Hallazgo]

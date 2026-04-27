"""Pydantic schemas de request/response del backend.

No confundir con `src/schemas.py`, que valida la salida del LLM.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserPublic


class AnalysisParams(BaseModel):
    """Parametros opcionales del analisis (todos los campos son query/form)."""

    codigo_curso: str | None = None
    modelo: str = "qwen2.5:14b"
    dispatcher: Literal["rule", "rag"] = "rule"
    top_k: int = Field(default=5, ge=3, le=10)
    enriquecer: bool = False
    generar_resumen: bool = False


AnalysisStatus = Literal["pending", "running", "done", "failed"]


class AnalysisSummary(BaseModel):
    """Vista de listado: sin el reporte completo."""

    id: str
    filename: str
    status: AnalysisStatus
    codigo_curso: str | None
    modelo: str
    dispatcher: str
    enriquecer: bool
    generar_resumen: bool
    created_at: datetime
    completed_at: datetime | None
    duration_s: float | None
    error: str | None


class AnalysisDetail(AnalysisSummary):
    """Vista de detalle: incluye el reporte completo si status='done'."""

    report: dict | None = None


class AnalysisCreated(BaseModel):
    """Respuesta de POST /analyses."""

    id: str
    status: AnalysisStatus

"""Entry point del backend FastAPI.

Uso:
    uvicorn src.api.main:app --reload --port 8000

En produccion:
    uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 2
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from .config import get_settings  # noqa: E402
from .db import init_db  # noqa: E402
from .routes import analyses, auth  # noqa: E402

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="UnibaBot PDA API",
    description="Backend REST + SSE para verificacion de PDAs",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(analyses.router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}

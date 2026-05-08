#!/usr/bin/env bash
# Levanta los 4 procesos del stack en background y muestra los logs.
# Uso: bash scripts/dev.sh
# Requiere: redis corriendo, venv en ~/.venvs/unibabot, deps de web instaladas.

set -euo pipefail

VENV="${VENV:-$HOME/.venvs/unibabot}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v redis-cli &>/dev/null || ! redis-cli ping &>/dev/null; then
    echo "ERROR: Redis no esta corriendo. Inicialo con:"
    echo "  macOS:  brew services start redis"
    echo "  Linux:  sudo systemctl start redis"
    exit 1
fi

if [[ ! -f "$VENV/bin/python" ]]; then
    echo "ERROR: venv no encontrado en $VENV"
    echo "  python3 -m venv $VENV"
    echo "  $VENV/bin/pip install -r requirements-api.txt"
    exit 1
fi

cd "$ROOT"

echo "[dev] Iniciando API en :8000 ..."
"$VENV/bin/uvicorn" src.api.main:app --reload --port 8000 &
API_PID=$!

echo "[dev] Iniciando worker RQ ..."
"$VENV/bin/python" -m src.api.jobs.worker &
WORKER_PID=$!

echo "[dev] Iniciando frontend en :3000 ..."
(cd web && npm run dev) &
WEB_PID=$!

echo "[dev] Stack corriendo. Ctrl+C para detener todo."
trap "kill $API_PID $WORKER_PID $WEB_PID 2>/dev/null; echo '[dev] Detenido.'" EXIT INT TERM
wait

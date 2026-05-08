#!/usr/bin/env bash
# Primera vez: crea el venv e instala todas las dependencias Python y Node.
# Uso: bash scripts/setup.sh
#
# La variable VENV sobreescribe la ruta del venv (default: ~/.venvs/unibabot).
# IMPORTANTE: el venv debe quedar FUERA de iCloud/OneDrive para evitar eviccion
# de archivos por el proveedor de nube.

set -euo pipefail

VENV="${VENV:-$HOME/.venvs/unibabot}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[setup] Creando venv en $VENV ..."
python3 -m venv "$VENV"

echo "[setup] Instalando dependencias Python ..."
"$VENV/bin/pip" install --upgrade pip --quiet
"$VENV/bin/pip" install -r "$ROOT/requirements-api.txt"

echo "[setup] Instalando dependencias Node ..."
(cd "$ROOT/web" && npm install --silent)

echo "[setup] Listo."
echo "  Siguiente paso: bash scripts/dev.sh"
echo "  (Asegurate de que Redis y Ollama esten corriendo antes de arrancar.)"

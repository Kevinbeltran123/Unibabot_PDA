#!/usr/bin/env bash
# render.sh — Convierte todos los .mmd a SVG/PNG usando mmdc (Mermaid CLI)
# y genera el grafico de accuracy con Python.
#
# Requisitos:
#   npm install -g @mermaid-js/mermaid-cli
#   pip install matplotlib   (o activar el venv del proyecto)
#
# Uso:
#   bash diagrams/render.sh
#
# Output: diagrams/rendered/*.svg  y  diagrams/rendered/*.png

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$SCRIPT_DIR/rendered"
mkdir -p "$OUT"

echo "==> Renderizando diagramas Mermaid..."

for MMD in "$SCRIPT_DIR"/*.mmd; do
    NAME="$(basename "$MMD" .mmd)"
    echo "    $NAME"
    mmdc -i "$MMD" -o "$OUT/$NAME.svg" --backgroundColor white --scale 2 --quiet
    mmdc -i "$MMD" -o "$OUT/$NAME.png" --backgroundColor white --scale 3 --quiet
done

echo ""
echo "==> Generando grafico de accuracy (Python)..."

# Intentar con el venv del proyecto, caer en el Python del sistema si no existe
VENV="$HOME/.venvs/unibabot/bin/python"
if [ -f "$VENV" ]; then
    "$VENV" "$SCRIPT_DIR/07_accuracy_journey.py"
else
    python3 "$SCRIPT_DIR/07_accuracy_journey.py"
fi

echo ""
echo "==> Listo. Archivos en: $OUT"
ls -lh "$OUT"

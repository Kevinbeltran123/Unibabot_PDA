"""
Elimina del gold las entradas huerfanas asociadas al PDA
"PDA-Modelos y Simulacion- 2026A.pdf" (archivo ya no existe en disco).

Script de un solo uso; preservado en repo para trazabilidad.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
GOLD_PATH = ROOT / "data" / "gold_labels.json"
PDA_OBSOLETO = "PDA-Modelos y Simulación- 2026A.pdf"


def main():
    with open(GOLD_PATH, encoding="utf-8") as f:
        gold = json.load(f)

    antes = len(gold)
    filtrado = [g for g in gold if g.get("pda_file") != PDA_OBSOLETO]
    eliminadas = antes - len(filtrado)

    with open(GOLD_PATH, "w", encoding="utf-8") as f:
        json.dump(filtrado, f, ensure_ascii=False, indent=2)

    print(f"Gold labels: {antes} -> {len(filtrado)} ({eliminadas} eliminadas)")
    print(f"PDA descartado: {PDA_OBSOLETO}")
    print(f"Archivo: {GOLD_PATH}")


if __name__ == "__main__":
    main()

"""
Fusiona candidatos nuevos con un gold existente.

Reglas de fusion:
- Las entradas existentes se preservan tal cual (son humanas validadas).
- Para cada candidato nuevo, se agrega al gold solo si no existe ya una
  entrada (misma (pda_file, seccion, regla_id)).
- Los campos internos "_regla_descripcion" y "_seccion_pda_meta" se
  descartan antes de escribir el gold final (son solo para el proceso
  de revision, no para evaluate.py).
- El campo "confidence" se descarta igualmente (gold final sin metadata
  de proceso).

Uso:
    python src/tooling/fusionar_gold.py \\
        --candidates data/gold_candidates_train.json \\
        --existing data/gold_labels.json \\
        --output data/gold_labels.json

    # Si no hay gold existente (caso test hold-out):
    python src/tooling/fusionar_gold.py \\
        --candidates data/gold_candidates_test.json \\
        --output data/gold_labels_test.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


CAMPOS_INTERNOS = {"confidence", "_regla_descripcion", "_seccion_pda_meta"}


def limpiar(entrada: dict) -> dict:
    """Elimina campos internos y entradas con estado_esperado=None."""
    return {k: v for k, v in entrada.items() if k not in CAMPOS_INTERNOS}


def clave(e: dict) -> tuple[str, str, str]:
    return (e["pda_file"], e["seccion"], e["regla_id"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--existing", default=None)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--include-review",
        action="store_true",
        help="Incluir entries con confidence=review (estado=null). Default: excluirlas.",
    )
    args = parser.parse_args()

    with open(args.candidates, encoding="utf-8") as f:
        candidatos = json.load(f)

    if args.existing:
        with open(args.existing, encoding="utf-8") as f:
            existentes = json.load(f)
    else:
        existentes = []

    claves_existentes = {clave(e) for e in existentes}

    agregados = 0
    skipped_dup = 0
    skipped_review = 0

    resultado = [limpiar(e) for e in existentes]

    for cand in candidatos:
        if clave(cand) in claves_existentes:
            skipped_dup += 1
            continue
        if cand.get("estado_esperado") is None and not args.include_review:
            skipped_review += 1
            continue
        resultado.append(limpiar(cand))
        agregados += 1

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"Candidatos: {len(candidatos)}")
    print(f"Existentes: {len(existentes)}")
    print(f"Agregados: {agregados}")
    print(f"Skipped (duplicados con existente): {skipped_dup}")
    print(f"Skipped (review sin estado, no --include-review): {skipped_review}")
    print(f"Total final: {len(resultado)}")
    print(f"Archivo: {out}")


if __name__ == "__main__":
    main()

"""
Corrige gold_labels_test.json y gold_labels.json comparando cada entry
NO CUMPLE contra el texto literal del PDA.

Si el codigo canonico de la regla aparece literalmente en el texto del
PDA (via regex), entonces la entry gold esta mal etiquetada (debe ser
CUMPLE). El extractor LLM confirmo esto pero aqui usamos solo regex
directo sobre texto parseado para evitar circularidad.

Para cada correccion: cambia estado_esperado a CUMPLE y anota la razon.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pdf_parser import parsear_pda
from rules.declaracion_checker import extraer_codigo_de_regla

ROOT = Path(__file__).parent.parent.parent
REGLAS_PATH = ROOT / "data" / "lineamientos" / "reglas.json"
PDAS_DIR = ROOT / "PDAs"


def cargar_reglas_dict() -> dict[str, dict]:
    with open(REGLAS_PATH, encoding="utf-8") as f:
        return {r["id"]: r for r in json.load(f)}


def codigo_aparece_en_texto(codigo: str, texto: str) -> bool:
    """Verifica si el codigo aparece literalmente en el texto del PDA.

    Usa word boundaries para evitar falsos positivos (ej. 'C1' no debe
    matchear en 'C15'). Caso especial ABET: acepta '5.1' con context
    ABET o indicador.
    """
    if re.fullmatch(r"\d+\.\d+", codigo):  # ABET
        patron = rf"(ABET|indicador)[^.]*?\b{re.escape(codigo)}\b|\b{re.escape(codigo)}:"
    elif codigo.startswith("C") and codigo[1:].isdigit():
        patron = rf"\b{re.escape(codigo)}\b"
    else:
        patron = rf"\b{re.escape(codigo)}\b"
    return bool(re.search(patron, texto, re.IGNORECASE))


def corregir_gold(gold_path: Path, reglas: dict[str, dict]) -> dict:
    with open(gold_path, encoding="utf-8") as f:
        gold = json.load(f)

    correcciones = []
    pda_cache: dict[str, str] = {}

    for entry in gold:
        if entry.get("estado_esperado") != "NO CUMPLE":
            continue
        regla = reglas.get(entry["regla_id"])
        if not regla:
            continue
        codigo = extraer_codigo_de_regla(regla)
        if not codigo:
            continue

        pda_file = entry["pda_file"]
        if pda_file not in pda_cache:
            pda_path = PDAS_DIR / pda_file
            if not pda_path.exists():
                pda_cache[pda_file] = ""
                continue
            secs = parsear_pda(pda_path)
            pda_cache[pda_file] = "\n".join(secs.values())

        texto = pda_cache[pda_file]
        if codigo_aparece_en_texto(codigo, texto):
            correcciones.append((entry, codigo))
            entry["estado_esperado"] = "CUMPLE"
            entry["nota"] = (
                f"[Auto-corregido m13] El codigo {codigo} aparece literalmente "
                f"en el texto del PDA. Etiquetado original NO CUMPLE era erroneo."
            )

    return {"gold": gold, "correcciones": correcciones, "total_analizadas": len(gold)}


def main():
    reglas = cargar_reglas_dict()

    for gold_name in ["gold_labels.json", "gold_labels_test.json"]:
        gold_path = ROOT / "data" / gold_name
        print(f"\n=== {gold_name} ===")
        result = corregir_gold(gold_path, reglas)
        correcciones = result["correcciones"]
        print(f"Total entries: {result['total_analizadas']}")
        print(f"Correcciones (NO CUMPLE -> CUMPLE): {len(correcciones)}")
        for entry, codigo in correcciones:
            print(f"  {entry['pda_file'][:40]:40s} {entry['regla_id']:10s} (codigo {codigo})")

        if correcciones:
            with open(gold_path, "w", encoding="utf-8") as f:
                json.dump(result["gold"], f, ensure_ascii=False, indent=2)
            print(f"Guardado: {gold_path}")


if __name__ == "__main__":
    main()

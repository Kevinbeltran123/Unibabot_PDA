"""
Genera entradas candidatas para gold_labels.json de forma exhaustiva.

Para cada PDA:
1. EST-001..EST-011 -> confidence=high via estructural_checker (deterministas).
2. COMP aplicables (aplica_a == curso OR "todos", tipo != "estructural") ->
   confidence=medium via analizar_pda() como silver annotator.
3. Si una regla no aparece en el reporte del agente (fuera de top_k),
   queda confidence=review con estado_esperado=null.

Salida: JSON con todas las entradas listas para un segundo annotator
(Claude en session) o etiquetado manual de las entries "review".

Uso:
    python src/tooling/generar_gold_exhaustivo.py \\
        --pdas PDA1.pdf,PDA2.pdf \\
        --cursos 22A14,22A12 \\
        --output data/gold_candidates.json

Convenciones:
- La seccion para EST es siempre "__global__" (reglas globales al PDA).
- Para COMP, se usa el nombre real de la seccion donde fue evaluada por
  el agente (o una derivada de la metadata regla.seccion_pda si no fue
  evaluada en ninguna).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agent import analizar_pda
from pdf_parser import parsear_pda
from rules.estructural_checker import verificar_estructurales

REGLAS_PATH = ROOT / "data" / "lineamientos" / "reglas.json"
PDAS_DIR = ROOT / "PDAs"


def cargar_reglas() -> list[dict]:
    with open(REGLAS_PATH, encoding="utf-8") as f:
        return json.load(f)


def reglas_aplicables_curso(todas: list[dict], codigo_curso: str) -> list[dict]:
    """Reglas no-estructurales que aplican a un curso dado."""
    return [
        r for r in todas
        if r["tipo"] != "estructural"
        and r.get("aplica_a") in (codigo_curso, "todos")
    ]


def entrada_gold(
    pda_file: str,
    codigo_curso: str,
    seccion: str,
    regla_id: str,
    estado_esperado: str | None,
    nota: str,
    confidence: str,
    regla_descripcion: str = "",
    seccion_pda_meta: str = "",
) -> dict:
    return {
        "pda_file": pda_file,
        "codigo_curso": codigo_curso,
        "seccion": seccion,
        "regla_id": regla_id,
        "estado_esperado": estado_esperado,
        "nota": nota,
        "confidence": confidence,
        "_regla_descripcion": regla_descripcion,
        "_seccion_pda_meta": seccion_pda_meta,
    }


def generar_entradas_est(
    pda_file: str,
    codigo_curso: str,
    secciones: dict[str, str],
) -> list[dict]:
    """11 entradas EST via estructural_checker -- alta confianza."""
    hallazgos = verificar_estructurales(secciones)
    entradas = []
    for h in hallazgos:
        entradas.append(entrada_gold(
            pda_file=pda_file,
            codigo_curso=codigo_curso,
            seccion="__global__",
            regla_id=h["regla_id"],
            estado_esperado=h["estado"],
            nota=h["evidencia"][:300],
            confidence="high",
            regla_descripcion=h["regla"],
        ))
    return entradas


def buscar_hallazgo_en_reporte(reporte: dict, regla_id: str) -> tuple[str, dict] | None:
    """Devuelve (seccion, hallazgo) donde la regla fue evaluada, o None."""
    for resultado in reporte.get("resultados", []):
        for h in resultado.get("hallazgos", []):
            if h.get("regla_id") == regla_id:
                return resultado.get("seccion", ""), h
    return None


def generar_entradas_comp(
    pda_file: str,
    codigo_curso: str,
    reglas_comp: list[dict],
    reporte_agente: dict,
) -> list[dict]:
    """COMP entries usando analizar_pda como silver annotator."""
    entradas = []
    for regla in reglas_comp:
        rid = regla["id"]
        encontrado = buscar_hallazgo_en_reporte(reporte_agente, rid)
        if encontrado is None:
            entradas.append(entrada_gold(
                pda_file=pda_file,
                codigo_curso=codigo_curso,
                seccion=regla.get("seccion_pda", ""),
                regla_id=rid,
                estado_esperado=None,
                nota="Regla no evaluada por el agente (fuera del top_k del retrieval). Requiere etiquetado manual.",
                confidence="review",
                regla_descripcion=regla["descripcion"],
                seccion_pda_meta=regla.get("seccion_pda", ""),
            ))
            continue
        seccion_eval, hallazgo = encontrado
        entradas.append(entrada_gold(
            pda_file=pda_file,
            codigo_curso=codigo_curso,
            seccion=seccion_eval,
            regla_id=rid,
            estado_esperado=hallazgo.get("estado"),
            nota=(hallazgo.get("evidencia") or "")[:300],
            confidence="medium",
            regla_descripcion=regla["descripcion"],
            seccion_pda_meta=regla.get("seccion_pda", ""),
        ))
    return entradas


def generar_para_pda(
    pda_file: str,
    codigo_curso: str,
    todas_reglas: list[dict],
    modelo: str,
) -> list[dict]:
    pdf_path = PDAS_DIR / pda_file
    if not pdf_path.exists():
        print(f"  ! PDA no encontrado: {pdf_path}", file=sys.stderr)
        return []

    print(f"\n=== Procesando: {pda_file} ({codigo_curso}) ===")

    secciones = parsear_pda(pdf_path)
    print(f"  Secciones parseadas: {len(secciones)}")

    entradas_est = generar_entradas_est(pda_file, codigo_curso, secciones)
    print(f"  EST: {len(entradas_est)} entradas (estructural_checker)")

    reglas_comp = reglas_aplicables_curso(todas_reglas, codigo_curso)
    print(f"  COMP aplicables: {len(reglas_comp)} reglas")

    print(f"  Corriendo analizar_pda con {modelo}...")
    reporte = analizar_pda(str(pdf_path), codigo_curso, modelo=modelo)

    entradas_comp = generar_entradas_comp(pda_file, codigo_curso, reglas_comp, reporte)
    medium = sum(1 for e in entradas_comp if e["confidence"] == "medium")
    review = sum(1 for e in entradas_comp if e["confidence"] == "review")
    print(f"  COMP generadas: {len(entradas_comp)} (medium={medium}, review={review})")

    return entradas_est + entradas_comp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdas", required=True, help="Lista de PDAs separados por '|' (usar '|' por nombres con comas)")
    parser.add_argument("--cursos", required=True, help="Codigos de curso separados por comas, mismo orden que --pdas")
    parser.add_argument("--output", required=True, help="Ruta del archivo JSON de salida")
    parser.add_argument("--modelo", default="llama3.1:8b", help="Modelo ollama (default: llama3.1:8b)")
    args = parser.parse_args()

    pdas = [s.strip() for s in args.pdas.split("|")]
    cursos = [s.strip() for s in args.cursos.split(",")]
    if len(pdas) != len(cursos):
        parser.error(f"Mismatched pdas ({len(pdas)}) vs cursos ({len(cursos)})")

    todas = cargar_reglas()
    print(f"Reglas cargadas: {len(todas)}")

    todas_entradas = []
    for pda, curso in zip(pdas, cursos):
        todas_entradas.extend(generar_para_pda(pda, curso, todas, args.modelo))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(todas_entradas, f, ensure_ascii=False, indent=2)

    total = len(todas_entradas)
    high = sum(1 for e in todas_entradas if e["confidence"] == "high")
    medium = sum(1 for e in todas_entradas if e["confidence"] == "medium")
    review = sum(1 for e in todas_entradas if e["confidence"] == "review")
    print(f"\n=== RESUMEN ===")
    print(f"Total entradas: {total}")
    print(f"  high   : {high} (EST deterministas)")
    print(f"  medium : {medium} (COMP silver -- candidatos a 2do annotator)")
    print(f"  review : {review} (COMP no evaluadas -- requieren etiquetado manual)")
    print(f"Salida: {out_path}")


if __name__ == "__main__":
    main()

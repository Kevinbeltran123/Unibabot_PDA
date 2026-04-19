"""
Script de evaluacion del pipeline UnibaBot PDA.

Compara la salida del agente contra un dataset gold etiquetado a mano,
y produce metricas: accuracy, precision/recall de NO CUMPLE, json_valid_rate,
latencia, tasa de hallazgos huerfanos.

Uso:
    python src/evaluate.py --tag baseline
    python src/evaluate.py --tag m2_retrieval_filter --modelo llama3.2
    python src/evaluate.py --compare baseline m2_retrieval_filter
"""

import json
import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent import analizar_pda

ROOT = Path(__file__).parent.parent
PDAS_DIR = ROOT / "PDAs"
GOLD_PATH = ROOT / "data" / "gold_labels.json"
RESULTS_DIR = ROOT / "results"

# Mapeo de PDAs a codigos de curso (igual que en prepare_dataset.py)
PDAS_CURSOS = {
    # Train set (3 PDAs originales con gold_labels.json)
    "PDA - Intelligent Agents 2026A-01.docx.pdf": "22A14",
    "PDA - Sistemas de Control Automatico 2026A GR01.pdf": "22A12",
    "PDA - Desarrollo aplicaciones UIUX - 2026A 02.pdf": "22A31",
    # Test set held-out (3 PDAs nuevos agregados 2026-04-18)
    "PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf": "22A35",
    "PDA - Gestión TI 2026A.pdf": "22A32",
    "PDA - Pensamiento computacional 2026A - Firmas.pdf": "22A52",
}


def cargar_gold(path: Path | None = None) -> list[dict]:
    """Carga los gold labels. Cada entrada tiene:
    pda_file, codigo_curso, seccion, regla_id, estado_esperado.
    """
    gold_path = Path(path) if path else GOLD_PATH
    if not gold_path.exists():
        print(f"Gold labels no encontrado en {gold_path}")
        print("Crea el archivo con al menos 30 entradas etiquetadas a mano.")
        sys.exit(1)
    with open(gold_path, encoding="utf-8") as f:
        return json.load(f)


def _secciones_mapean_al_mismo_canonico(a: str, b: str) -> bool:
    """True si ambos nombres de seccion mapean a alguna seccion_pda comun.

    Usa seccion_mapping.py para traducir los nombres reales a categorias
    canonicas. Permite hacer match cuando el gold usa el nombre canonico
    (ej. 'Competencias / Resultados de Aprendizaje') y el agente emite
    bajo el nombre parseado real (ej. 'Plan de estudios de la').
    """
    sys.path.insert(0, str(ROOT / "src"))
    from rag.seccion_mapping import secciones_pda_validas
    mapa_a = set(secciones_pda_validas(a) or [])
    mapa_b = set(secciones_pda_validas(b) or [])
    # El nombre canonico puede ser el literal tambien (ej. "Competencias")
    if a in mapa_b or b in mapa_a:
        return True
    return bool(mapa_a & mapa_b)


def buscar_hallazgo(reporte: dict, seccion: str, regla_id: str) -> dict | None:
    """Encuentra el hallazgo para una regla_id en el reporte del agente.

    Desde m11 (rule-driven) cada regla es evaluada exactamente una vez por
    reporte (grouping determinista por seccion destino). Por lo tanto el
    matching puede basarse exclusivamente en regla_id, ignorando la seccion
    del gold -- la unicidad esta garantizada por construccion.

    El parametro `seccion` se conserva por compatibilidad pero no se usa
    para matching, solo para debugging.
    """
    for resultado in reporte.get("resultados", []):
        for h in resultado.get("hallazgos", []):
            if h.get("regla_id") == regla_id:
                return h
    return None


def calcular_accuracy(reportes: dict[str, dict], gold: list[dict]) -> dict:
    """Calcula metricas comparando reportes del agente contra gold labels.

    Usa "NO CUMPLE" como clase positiva (lo que importa detectar en auditoria).
    """
    tp = fp = tn = fn = 0
    not_found = 0

    for entry in gold:
        reporte = reportes.get(entry["pda_file"])
        if not reporte:
            not_found += 1
            continue

        hallazgo = buscar_hallazgo(reporte, entry["seccion"], entry["regla_id"])
        if hallazgo is None:
            not_found += 1
            continue

        predicho = hallazgo.get("estado")
        esperado = entry["estado_esperado"]

        if predicho == "NO CUMPLE" and esperado == "NO CUMPLE":
            tp += 1
        elif predicho == "NO CUMPLE" and esperado == "CUMPLE":
            fp += 1
        elif predicho == "CUMPLE" and esperado == "CUMPLE":
            tn += 1
        elif predicho == "CUMPLE" and esperado == "NO CUMPLE":
            fn += 1

    matched = tp + fp + tn + fn
    accuracy = (tp + tn) / matched if matched > 0 else 0.0
    precision_nocumple = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall_nocumple = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    return {
        "accuracy": accuracy,
        "precision_nocumple": precision_nocumple,
        "recall_nocumple": recall_nocumple,
        "matched": matched,
        "not_found": not_found,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def calcular_json_valid_rate(reportes: dict[str, dict]) -> float:
    """Fraccion de hallazgos que tienen los campos requeridos (no son errores de parseo)."""
    total = 0
    validos = 0
    for reporte in reportes.values():
        for resultado in reporte.get("resultados", []):
            if resultado.get("error"):
                total += 1
                continue
            for h in resultado.get("hallazgos", []):
                total += 1
                if all(k in h for k in ("regla_id", "estado", "evidencia")):
                    validos += 1
    return validos / total if total > 0 else 0.0


def ejecutar_pipeline(
    modelo: str,
    tag: str,
    pdas_incluidos: set[str] | None = None,
) -> tuple[dict[str, dict], float]:
    """Corre analizar_pda sobre los PDAs especificados.

    Args:
        modelo: modelo ollama a usar.
        tag: etiqueta para persistir reports_<tag>.json.
        pdas_incluidos: si se provee, solo procesa PDAs cuyo nombre esta
            en este conjunto. Permite correr evals sobre subsets definidos
            por el gold activo (train vs test).

    Persiste los reportes en results/reports_<tag>.json.
    """
    reportes = {}
    start = time.time()

    for pdf_name, codigo_curso in PDAS_CURSOS.items():
        if pdas_incluidos is not None and pdf_name not in pdas_incluidos:
            continue

        pdf_path = PDAS_DIR / pdf_name
        if not pdf_path.exists():
            print(f"  Saltando {pdf_name} (no encontrado)")
            continue

        print(f"Procesando: {pdf_name}...")
        try:
            reporte = analizar_pda(str(pdf_path), codigo_curso, modelo=modelo)
            reportes[pdf_name] = reporte
        except Exception as e:
            print(f"  ERROR: {e}")
            reportes[pdf_name] = {"resultados": [], "error": str(e)}

    elapsed = time.time() - start

    # Persistir reportes crudos
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    reportes_path = RESULTS_DIR / f"reports_{tag}.json"
    with open(reportes_path, "w", encoding="utf-8") as f:
        json.dump(reportes, f, ensure_ascii=False, indent=2)
    print(f"\nReportes raw guardados en: {reportes_path}")

    return reportes, elapsed


def cargar_reportes(tag: str) -> dict[str, dict] | None:
    """Carga reportes previamente guardados para un tag dado."""
    reportes_path = RESULTS_DIR / f"reports_{tag}.json"
    if not reportes_path.exists():
        return None
    with open(reportes_path, encoding="utf-8") as f:
        return json.load(f)


def guardar_metricas(metricas: dict, tag: str):
    """Escribe results/metrics_<tag>.json."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"metrics_{tag}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)
    print(f"\nMetricas guardadas en: {out_path}")


def imprimir_metricas(metricas: dict):
    """Imprime tabla de metricas en formato legible."""
    print("\n=== METRICAS ===")
    print(f"Tag:                   {metricas.get('tag', '?')}")
    print(f"Modelo:                {metricas.get('modelo', '?')}")
    print(f"Accuracy:              {metricas.get('accuracy', 0):.3f}")
    print(f"Precision NO CUMPLE:   {metricas.get('precision_nocumple', 0):.3f}")
    print(f"Recall NO CUMPLE:      {metricas.get('recall_nocumple', 0):.3f}")
    print(f"JSON valid rate:       {metricas.get('json_valid_rate', 0):.3f}")
    print(f"Latencia total:        {metricas.get('latencia_total_seg', 0):.1f}s")
    print(f"Gold entries matched:  {metricas.get('matched', 0)} / {metricas.get('total_gold', 0)}")
    print(f"TP/FP/TN/FN:           {metricas.get('tp', 0)}/{metricas.get('fp', 0)}/{metricas.get('tn', 0)}/{metricas.get('fn', 0)}")


def comparar_runs(tag_a: str, tag_b: str):
    """Imprime diff entre dos runs guardados."""
    path_a = RESULTS_DIR / f"metrics_{tag_a}.json"
    path_b = RESULTS_DIR / f"metrics_{tag_b}.json"

    if not path_a.exists() or not path_b.exists():
        print(f"ERROR: Alguna metrica no existe ({path_a} o {path_b})")
        sys.exit(1)

    with open(path_a) as f:
        a = json.load(f)
    with open(path_b) as f:
        b = json.load(f)

    print(f"\n=== COMPARACION: {tag_a} vs {tag_b} ===")
    metricas_claves = [
        ("accuracy", "Accuracy"),
        ("precision_nocumple", "Precision NO CUMPLE"),
        ("recall_nocumple", "Recall NO CUMPLE"),
        ("json_valid_rate", "JSON valid rate"),
        ("latencia_total_seg", "Latencia total (s)"),
    ]
    print(f"{'Metrica':<25} {'A':>10} {'B':>10} {'Delta':>12}")
    print("-" * 60)
    for key, label in metricas_claves:
        va = a.get(key, 0)
        vb = b.get(key, 0)
        delta = vb - va
        signo = "+" if delta >= 0 else ""
        print(f"{label:<25} {va:>10.3f} {vb:>10.3f} {signo}{delta:>11.3f}")


def main():
    parser = argparse.ArgumentParser(description="Evaluar pipeline UnibaBot PDA")
    parser.add_argument("--tag", type=str, help="Tag para guardar esta corrida (ej: baseline, m2_filter)")
    parser.add_argument("--modelo", type=str, default="llama3.2", help="Modelo a usar (default: llama3.2)")
    parser.add_argument("--compare", nargs=2, metavar=("TAG_A", "TAG_B"), help="Comparar dos runs guardados")
    parser.add_argument("--reuse", action="store_true", help="Reutilizar reportes guardados del tag (no re-correr el pipeline)")
    parser.add_argument(
        "--gold-path",
        type=str,
        default=None,
        help="Ruta al archivo de gold labels (default: data/gold_labels.json). "
        "Usar data/gold_labels_test.json para eval hold-out.",
    )
    args = parser.parse_args()

    if args.compare:
        comparar_runs(args.compare[0], args.compare[1])
        return

    if not args.tag:
        parser.error("Se requiere --tag o --compare")

    gold_path = Path(args.gold_path) if args.gold_path else GOLD_PATH
    gold = cargar_gold(gold_path)
    print(f"Gold labels cargados desde {gold_path.name}: {len(gold)} entradas")

    pdas_en_gold = {g["pda_file"] for g in gold}

    if args.reuse:
        reportes = cargar_reportes(args.tag)
        if reportes is None:
            print(f"ERROR: no se encontraron reportes guardados para tag '{args.tag}'")
            sys.exit(1)
        print(f"Reusando reportes guardados para tag '{args.tag}'")
        latencia = 0.0
    else:
        print(f"\nCorriendo pipeline con modelo '{args.modelo}'...")
        reportes, latencia = ejecutar_pipeline(args.modelo, args.tag, pdas_incluidos=pdas_en_gold)

    print("\nCalculando metricas...")
    metricas_acc = calcular_accuracy(reportes, gold)
    json_valid = calcular_json_valid_rate(reportes)

    if metricas_acc is None:
        print("ERROR: calcular_accuracy() no esta implementada aun.")
        sys.exit(1)

    metricas = {
        "tag": args.tag,
        "modelo": args.modelo,
        "total_gold": len(gold),
        "latencia_total_seg": latencia,
        "json_valid_rate": json_valid,
        **metricas_acc,
    }

    imprimir_metricas(metricas)
    guardar_metricas(metricas, args.tag)


if __name__ == "__main__":
    main()

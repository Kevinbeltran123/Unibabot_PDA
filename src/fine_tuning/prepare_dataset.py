"""
Genera el dataset de fine-tuning en formato Alpaca (instruction, input, output).

Fuentes de ejemplos:
1. Secciones reales de PDAs + lineamientos del RAG -> pares para revisar manualmente
2. Ejemplos generados sinteticamente (self-instruct) a partir de los manuales

Formato de salida: JSONL (un JSON por linea)
"""

import json
import sys
from pathlib import Path

# Agregar src/ al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pdf_parser import parsear_pda
from rag.retriever import recuperar_lineamientos

ROOT = Path(__file__).parent.parent.parent
PDAS_DIR = ROOT / "PDAs"
OUTPUT_DIR = ROOT / "data"

INSTRUCCION_BASE = (
    "Evalua si la siguiente seccion del PDA cumple con los lineamientos "
    "institucionales proporcionados. Para cada lineamiento, indica si cumple "
    "o no cumple, con evidencia y correccion requerida si aplica. "
    "Responde en formato JSON."
)

# Mapeo de PDAs a codigos de curso conocidos
PDAS_CURSOS = {
    "PDA - Intelligent Agents 2026A-01.docx.pdf": "22A14",
    "PDA - Sistemas de Control Automatico 2026A GR01.pdf": "22A12",
    "PDA - Desarrollo aplicaciones UIUX - 2026A 02.pdf": "22A31",
    "PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf": "22A35",
    "PDA - Gestión TI 2026A.pdf": "22A32",
    "PDA - Pensamiento computacional 2026A - Firmas.pdf": "22A52",
}


def formatear_lineamientos(lineamientos: list[dict]) -> str:
    lineas = []
    for i, lin in enumerate(lineamientos, 1):
        lineas.append(f"{i}. [{lin['tipo']}] {lin['descripcion']}")
    return "\n".join(lineas)


def generar_pares_crudos(top_k: int = 5) -> list[dict]:
    """Genera pares instruccion-input a partir de los PDAs reales.

    Los pares se generan SIN output -- el output debe ser escrito
    manualmente o generado con un LLM grande y revisado.
    """
    pares = []

    for pdf_name, codigo_curso in PDAS_CURSOS.items():
        pdf_path = PDAS_DIR / pdf_name
        if not pdf_path.exists():
            print(f"  Saltando {pdf_name} (no encontrado)")
            continue

        print(f"Procesando: {pdf_name} (curso: {codigo_curso})")
        secciones = parsear_pda(str(pdf_path))

        for nombre_seccion, contenido in secciones.items():
            if nombre_seccion == "PREAMBULO":
                continue
            if len(contenido) < 20:
                continue

            lineamientos = recuperar_lineamientos(
                contenido, top_k=top_k, codigo_curso=codigo_curso
            )

            input_text = (
                f"SECCION: {nombre_seccion}\n"
                f"CONTENIDO:\n{contenido[:1500]}\n\n"
                f"LINEAMIENTOS:\n{formatear_lineamientos(lineamientos)}"
            )

            pares.append({
                "instruction": INSTRUCCION_BASE,
                "input": input_text,
                "output": "",  # POR LLENAR manualmente o con LLM grande
            })

    return pares


def guardar_jsonl(datos: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for item in datos:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def main():
    print("=== Generando pares crudos desde PDAs reales ===\n")
    pares = generar_pares_crudos()

    # Guardar pares sin output (para revision manual)
    output_path = OUTPUT_DIR / "pares_crudos.jsonl"
    guardar_jsonl(pares, output_path)

    print(f"\nPares generados: {len(pares)}")
    print(f"Guardado en: {output_path}")
    print()
    print("Siguiente paso:")
    print("  1. Revisar pares_crudos.jsonl")
    print("  2. Llenar el campo 'output' con la evaluacion correcta")
    print("  3. Mover los ejemplos completos a training_dataset.jsonl")


if __name__ == "__main__":
    main()

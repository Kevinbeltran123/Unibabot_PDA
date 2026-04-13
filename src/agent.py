"""
Agente de verificacion de cumplimiento de PDAs.

Pipeline: PDF -> secciones -> RAG -> LLM -> reporte
"""

import json
import sys
import ollama
from pathlib import Path

# Asegurar que src/ este en el path para imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_parser import parsear_pda
from rag.retriever import recuperar_lineamientos
from rules.estructural_checker import verificar_estructurales

ROOT = Path(__file__).parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "compliance_prompt.txt"

# Modelos disponibles (registrados en ollama)
MODELO_BASELINE = "llama3.2"
MODELO_FINETUNED = "unibabot-pda"
MODELO_DEFAULT = MODELO_BASELINE


def cargar_prompt_template() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def formatear_lineamientos(lineamientos: list[dict]) -> str:
    """Convierte la lista de lineamientos recuperados en texto para el prompt.

    Incluye el id de cada regla para que el LLM pueda referenciarlo en su respuesta
    y facilitar el matching exacto en el script de evaluacion.
    """
    lineas = []
    for lin in lineamientos:
        lineas.append(f"[{lin['id']}] ({lin['tipo']}) {lin['descripcion']}")
    return "\n".join(lineas)


def evaluar_seccion(
    nombre_seccion: str,
    contenido: str,
    lineamientos: list[dict],
    template: str,
    modelo: str = MODELO_DEFAULT,
) -> dict | None:
    """Envia una seccion + lineamientos al LLM y parsea la respuesta JSON."""
    prompt = template.format(
        nombre_seccion=nombre_seccion,
        contenido_seccion=contenido[:2000],  # limitar contexto para modelo 3B
        lineamientos=formatear_lineamientos(lineamientos),
    )

    response = ollama.chat(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": 0.1,
            "num_predict": 800,  # max tokens de salida (evita loops infinitos)
            "stop": ["<|eot_id|>", "<|end_of_text|>"],  # tokens de fin para modelos fine-tuneados
        },
    )

    texto_respuesta = response["message"]["content"]

    # Intentar parsear JSON de la respuesta
    try:
        # Buscar el JSON en la respuesta (a veces el LLM agrega texto extra)
        inicio = texto_respuesta.find("{")
        fin = texto_respuesta.rfind("}") + 1
        if inicio >= 0 and fin > inicio:
            return json.loads(texto_respuesta[inicio:fin])
    except json.JSONDecodeError:
        pass

    # Si no se pudo parsear, devolver respuesta cruda
    return {
        "seccion": nombre_seccion,
        "hallazgos": [],
        "error": "No se pudo parsear la respuesta del LLM",
        "respuesta_cruda": texto_respuesta[:500],
    }


def preparar_evaluacion(
    secciones: dict[str, str],
    codigo_curso: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Decide que secciones evaluar y recupera lineamientos para cada una.

    Las reglas estructurales (tipo='estructural') se filtran del retrieval
    porque se verifican via rule-based deterministico en analizar_pda().
    El LLM solo recibe reglas de competencias y similares.
    """
    evaluaciones = []
    for nombre, contenido in secciones.items():
        #Saltar secciones irrelevantes (ejemplo: preambulo, bibliografia, etc)
        if nombre == "PREAMBULO":
            continue
        if len(contenido) < 20:
            continue

        # Recuperar mas lineamientos (top_k*2) porque vamos a filtrar estructurales
        lineamientos = recuperar_lineamientos(
            contenido,
            top_k=top_k * 2,
            codigo_curso=codigo_curso,
            nombre_seccion=nombre,
        )
        # Filtrar reglas estructurales (se manejan con rule-based)
        lineamientos = [l for l in lineamientos if l["tipo"] != "estructural"][:top_k]

        if not lineamientos:
            continue

        evaluaciones.append({
            "nombre_seccion": nombre,
            "contenido": contenido,
            "lineamientos": lineamientos,
        })

    return evaluaciones


def analizar_pda(
    pdf_path: str,
    codigo_curso: str | None = None,
    modelo: str = MODELO_DEFAULT,
) -> dict:
    """Pipeline completo: PDF -> reporte de cumplimiento.

    Usa rule-based determinista para las 11 reglas estructurales y LLM
    para las demas reglas (competencias, ABET, dimensiones, etc).
    """
    print(f"Parseando PDF: {pdf_path}")
    print(f"Modelo: {modelo}")
    secciones = parsear_pda(pdf_path)
    print(f"Secciones encontradas: {len(secciones)}")

    # Verificacion rule-based de reglas estructurales (determinista, rapido)
    print("Verificando reglas estructurales (rule-based)...")
    hallazgos_estructurales = verificar_estructurales(secciones)

    print("Preparando evaluacion LLM (solo competencias)...")
    evaluaciones = preparar_evaluacion(secciones, codigo_curso)

    template = cargar_prompt_template()
    reporte = {
        "archivo": pdf_path,
        "modelo": modelo,
        "codigo_curso": codigo_curso,
        "total_secciones": len(evaluaciones),
        "resultados": [
            {
                "seccion": "__estructural_global__",
                "hallazgos": hallazgos_estructurales,
            }
        ],
    }

    for eval_info in evaluaciones:
        nombre = eval_info["nombre_seccion"]
        print(f"  Evaluando: {nombre}...")

        resultado = evaluar_seccion(
            nombre,
            eval_info["contenido"],
            eval_info["lineamientos"],
            template,
            modelo=modelo,
        )
        reporte["resultados"].append(resultado)

    return reporte


# --- CLI ---
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python agent.py <ruta_al_pdf> [codigo_curso] [modelo]")
        print("  modelo: 'baseline' (llama3.2) o 'finetuned' (unibabot-pda). Default: baseline")
        print("Ejemplo: python agent.py 'PDAs/tu_pda.pdf' 22A14 finetuned")
        sys.exit(1)

    pdf_path = sys.argv[1]
    codigo = sys.argv[2] if len(sys.argv) > 2 else None

    # Aliases + fallback a nombre crudo (permite probar modelos ad-hoc)
    aliases = {"baseline": MODELO_BASELINE, "finetuned": MODELO_FINETUNED}
    if len(sys.argv) > 3:
        modelo = aliases.get(sys.argv[3], sys.argv[3])
    else:
        modelo = MODELO_DEFAULT

    reporte = analizar_pda(pdf_path, codigo, modelo=modelo)

    # Guardar reporte con sufijo del modelo para no pisar el del otro
    sufijo = "finetuned" if modelo == MODELO_FINETUNED else "baseline"
    output_path = ROOT / "results" / f"reporte_{sufijo}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"\nReporte guardado en: {output_path}")

    # Resumen
    for resultado in reporte.get("resultados", []):
        seccion = resultado.get("seccion", "?")
        hallazgos = resultado.get("hallazgos", [])
        cumple = sum(1 for h in hallazgos if h.get("estado") == "CUMPLE")
        no_cumple = sum(1 for h in hallazgos if h.get("estado") == "NO CUMPLE")
        print(f"  {seccion}: {cumple} cumple, {no_cumple} no cumple")

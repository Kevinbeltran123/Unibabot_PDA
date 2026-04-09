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

ROOT = Path(__file__).parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "compliance_prompt.txt"
MODELO = "llama3.2"


def cargar_prompt_template() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def formatear_lineamientos(lineamientos: list[dict]) -> str:
    """Convierte la lista de lineamientos recuperados en texto para el prompt."""
    lineas = []
    for i, lin in enumerate(lineamientos, 1):
        lineas.append(f"{i}. [{lin['tipo']}] {lin['descripcion']}")
    return "\n".join(lineas)


def evaluar_seccion(
    nombre_seccion: str,
    contenido: str,
    lineamientos: list[dict],
    template: str,
) -> dict | None:
    """Envia una seccion + lineamientos al LLM y parsea la respuesta JSON."""
    prompt = template.format(
        nombre_seccion=nombre_seccion,
        contenido_seccion=contenido[:2000],  # limitar contexto para modelo 3B
        lineamientos=formatear_lineamientos(lineamientos),
    )

    response = ollama.chat(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1},  # baja temperatura para respuestas consistentes
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
    Returns:
        Lista de dicts con: nombre_seccion, contenido, lineamientos
    """
    evaluaciones = []
    for nombre, contenido in secciones.items():
        #Saltar secciones irrelevantes (ejemplo: preambulo, bibliografia, etc)
        if nombre == "PREAMBULO":
            continue
        if len(contenido) < 20:
            continue
        
        #Recuperar lineamientos relevantes para esta seccion
        lineamientos = recuperar_lineamientos(contenido, top_k=top_k, codigo_curso=codigo_curso)
        evaluaciones.append({
            "nombre_seccion":nombre,
            "contenido": contenido,
            "lineamientos": lineamientos,
        })

    return evaluaciones


def analizar_pda(pdf_path: str, codigo_curso: str | None = None) -> dict:
    """Pipeline completo: PDF -> reporte de cumplimiento."""
    print(f"Parseando PDF: {pdf_path}")
    secciones = parsear_pda(pdf_path)
    print(f"Secciones encontradas: {len(secciones)}")

    print("Preparando evaluacion...")
    evaluaciones = preparar_evaluacion(secciones, codigo_curso)

    template = cargar_prompt_template()
    reporte = {
        "archivo": pdf_path,
        "codigo_curso": codigo_curso,
        "total_secciones": len(evaluaciones),
        "resultados": [],
    }

    for eval_info in evaluaciones:
        nombre = eval_info["nombre_seccion"]
        print(f"  Evaluando: {nombre}...")

        resultado = evaluar_seccion(
            nombre,
            eval_info["contenido"],
            eval_info["lineamientos"],
            template,
        )
        reporte["resultados"].append(resultado)

    return reporte


# --- CLI ---
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python agent.py <ruta_al_pdf> [codigo_curso]")
        print("Ejemplo: python agent.py 'PDAs/PDA - Intelligent Agents 2026A-01.docx.pdf' 22A14")
        sys.exit(1)

    pdf_path = sys.argv[1]
    codigo = sys.argv[2] if len(sys.argv) > 2 else None

    reporte = analizar_pda(pdf_path, codigo)

    # Guardar reporte
    output_path = ROOT / "results" / "reporte_cumplimiento.json"
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

"""
Agente de verificacion de cumplimiento de PDAs.

Pipeline: PDF -> secciones -> RAG -> LLM -> reporte
"""

import json
import sys
import ollama
from pathlib import Path
from pydantic import ValidationError

# Asegurar que src/ este en el path para imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_parser import parsear_pda
from rag.retriever import recuperar_lineamientos
from rules.estructural_checker import verificar_estructurales
from schemas import ReporteSeccion

ROOT = Path(__file__).parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "compliance_prompt.txt"
RETRY_PROMPT_PATH = ROOT / "src" / "prompts" / "retry_prompt.txt"

# Modelos disponibles (registrados en ollama)
MODELO_BASELINE = "llama3.2"
MODELO_FINETUNED = "unibabot-pda"
MODELO_8B = "llama3.1:8b"
# Default es ahora el 8B porque alcanza accuracy 1.000 en el gold dataset
MODELO_DEFAULT = MODELO_8B


def cargar_prompt_template() -> str:
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def cargar_retry_template() -> str:
    with open(RETRY_PROMPT_PATH, encoding="utf-8") as f:
        return f.read()


def _extraer_json(texto: str) -> dict | None:
    """Extrae el primer bloque JSON de un texto, tolerante a texto extra alrededor."""
    inicio = texto.find("{")
    fin = texto.rfind("}") + 1
    if inicio < 0 or fin <= inicio:
        return None
    try:
        return json.loads(texto[inicio:fin])
    except json.JSONDecodeError:
        return None


def parsear_y_validar(texto: str) -> ReporteSeccion | None:
    """Extrae JSON, intenta parsear con Pydantic. Devuelve ReporteSeccion o None."""
    data = _extraer_json(texto)
    if data is None:
        return None
    try:
        return ReporteSeccion(**data)
    except ValidationError:
        return None


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
    retry_template: str | None = None,
) -> dict:
    """Envia una seccion + lineamientos al LLM, valida con Pydantic y reintenta si falla.

    Flujo:
        1. Primera llamada al LLM con el prompt principal.
        2. Extraer JSON + validar con schemas.ReporteSeccion.
        3. Si falla: reintentar una vez con el retry_prompt (que incluye la
           respuesta previa y pide correccion).
        4. Si falla de nuevo: devolver reporte con error estructurado.
    """
    prompt = template.format(
        nombre_seccion=nombre_seccion,
        contenido_seccion=contenido[:1500],  # reducido por few-shot examples en el prompt
        lineamientos=formatear_lineamientos(lineamientos),
    )

    # Intento 1
    response = ollama.chat(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": 0.1,
            "num_predict": 800,
            "stop": ["<|eot_id|>", "<|end_of_text|>"],
        },
    )
    texto_respuesta = response["message"]["content"]

    reporte = parsear_y_validar(texto_respuesta)
    if reporte is not None:
        return reporte.model_dump()

    # Intento 2: retry con el prompt de correccion
    if retry_template is not None:
        retry_prompt = retry_template.format(
            respuesta_previa=texto_respuesta[:800],
            error="JSON invalido o estructura incorrecta",
            nombre_seccion=nombre_seccion,
        )
        response = ollama.chat(
            model=modelo,
            messages=[{"role": "user", "content": retry_prompt}],
            options={
                "temperature": 0.1,
                "num_predict": 400,
                "stop": ["<|eot_id|>", "<|end_of_text|>"],
            },
        )
        texto_respuesta = response["message"]["content"]
        reporte = parsear_y_validar(texto_respuesta)
        if reporte is not None:
            return reporte.model_dump()

    # Fallback: reporte con error estructurado
    return {
        "seccion": nombre_seccion,
        "hallazgos": [],
        "error": "No se pudo parsear la respuesta del LLM tras retry",
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
    retry_template = cargar_retry_template()
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
            retry_template=retry_template,
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
    aliases = {
        "baseline": MODELO_BASELINE,
        "finetuned": MODELO_FINETUNED,
        "8b": MODELO_8B,
        "large": MODELO_8B,
    }
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

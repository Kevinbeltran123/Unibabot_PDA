"""
Agente de verificacion de cumplimiento de PDAs.

Pipeline: PDF -> secciones -> RAG -> LLM -> reporte
"""

import json
import sys
from typing import Callable
import ollama
from pathlib import Path
from pydantic import ValidationError

# Asegurar que src/ este en el path para imports
sys.path.insert(0, str(Path(__file__).parent))

from pdf_parser import parsear_pda
from rag.retriever import recuperar_lineamientos, recuperar_dimension_rules
from rag.seccion_mapping import secciones_pda_validas
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

# Contrato del callback de progreso: (evento, datos) -> None
# Eventos emitidos por analizar_pda:
#   parsing_start       {pdf_path, modelo}
#   parsing_done        {num_secciones}
#   structural_start    {}
#   structural_done     {hallazgos}
#   llm_prep_start      {}
#   llm_prep_done       {num_evaluaciones}
#   section_eval_start  {index, total, name}
#   section_eval_done   {index, total, name, cumple, no_cumple}
#   done                {total_secciones}
ProgressCallback = Callable[[str, dict], None]


def _default_progress(event: str, data: dict) -> None:
    """Callback por defecto: replica exactamente el stdout previo al refactor.

    Solo los eventos que la CLI imprimia antes producen output. El resto
    (structural_done, llm_prep_done, section_eval_done, done) permanecen
    silenciosos para que `python src/agent.py ...` siga teniendo el mismo
    stdout byte-a-byte, y scripts como evaluate.py no noten el cambio.
    """
    if event == "parsing_start":
        print(f"Parseando PDF: {data['pdf_path']}")
        print(f"Modelo: {data['modelo']}")
    elif event == "parsing_done":
        print(f"Secciones encontradas: {data['num_secciones']}")
    elif event == "structural_start":
        print("Verificando reglas estructurales (rule-based)...")
    elif event == "llm_prep_start":
        print("Preparando evaluacion LLM (solo competencias)...")
    elif event == "section_eval_start":
        print(f"  Evaluando: {data['name']}...")


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


def preparar_evaluaciones_dimension(
    secciones: dict[str, str],
    codigo_curso: str,
) -> list[dict]:
    """Genera evaluaciones separadas para reglas de dimension del curso.

    Las reglas de dimension no compiten con reglas de competencias en el ranking
    semantico (tienen terminologia diferente), por lo que se evaluan en llamadas
    LLM separadas — una por cada seccion de Competencias detectada. Esto garantiza
    que buscar_hallazgo() las encuentre sin importar en que seccion el gold las espera.

    Devuelve una lista de evaluaciones (una entrada por seccion de Competencias).
    """
    dim_rules = recuperar_dimension_rules(codigo_curso)
    if not dim_rules:
        return []

    evaluaciones = []
    for nombre, contenido in secciones.items():
        if len(contenido) < 20:
            continue
        secciones_mapeadas = secciones_pda_validas(nombre)
        if secciones_mapeadas and "Competencias" in secciones_mapeadas:
            evaluaciones.append({
                "nombre_seccion": nombre,
                "contenido": contenido,
                "lineamientos": dim_rules,
            })

    return evaluaciones


def analizar_pda(
    pdf_path: str,
    codigo_curso: str | None = None,
    modelo: str = MODELO_DEFAULT,
    top_k: int = 5,
    on_progress: ProgressCallback | None = None,
) -> dict:
    """Pipeline completo: PDF -> reporte de cumplimiento.

    Usa rule-based determinista para las 11 reglas estructurales y LLM
    para las demas reglas (competencias, ABET, dimensiones, etc).

    Si `on_progress` es None, se usa `_default_progress` que replica el
    stdout previo al refactor. La UI de Streamlit pasa un callback custom
    que traduce los eventos a updates visuales (st.status, progress bar).
    """
    emit = on_progress or _default_progress

    emit("parsing_start", {"pdf_path": pdf_path, "modelo": modelo})
    secciones = parsear_pda(pdf_path)
    emit("parsing_done", {"num_secciones": len(secciones)})

    # Verificacion rule-based de reglas estructurales (determinista, rapido)
    emit("structural_start", {})
    hallazgos_estructurales = verificar_estructurales(secciones)
    emit("structural_done", {"hallazgos": len(hallazgos_estructurales)})

    emit("llm_prep_start", {})
    evaluaciones = preparar_evaluacion(secciones, codigo_curso, top_k=top_k)

    # Evaluacion separada para reglas de dimension (no ranquean bien semanticamente)
    if codigo_curso:
        evaluaciones += preparar_evaluaciones_dimension(secciones, codigo_curso)
    emit("llm_prep_done", {"num_evaluaciones": len(evaluaciones)})

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

    total = len(evaluaciones)
    for idx, eval_info in enumerate(evaluaciones, start=1):
        nombre = eval_info["nombre_seccion"]
        emit("section_eval_start", {"index": idx, "total": total, "name": nombre})

        resultado = evaluar_seccion(
            nombre,
            eval_info["contenido"],
            eval_info["lineamientos"],
            template,
            modelo=modelo,
            retry_template=retry_template,
        )
        reporte["resultados"].append(resultado)

        hallazgos = resultado.get("hallazgos", [])
        cumple = sum(1 for h in hallazgos if h.get("estado") == "CUMPLE")
        no_cumple = sum(1 for h in hallazgos if h.get("estado") == "NO CUMPLE")
        emit("section_eval_done", {
            "index": idx,
            "total": total,
            "name": nombre,
            "cumple": cumple,
            "no_cumple": no_cumple,
        })

    emit("done", {"total_secciones": total})
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

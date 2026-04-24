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

from common.logging_config import get_logger, setup_logging
from common.ollama_client import chat as llm_chat
from pdf_parser import parsear_pda
from rag.rule_dispatcher import (
    SECCION_AUSENTE,
    agrupar_reglas_por_seccion,
    formatear_regla_como_lineamiento,
    reglas_aplicables,
)
from rules.declaracion_checker import tiene_codigo_canonico, verificar_declaraciones
from rules.declaracion_extractor import extraer_declaraciones
from rules.estructural_checker import hallazgo, verificar_estructurales
from schemas import ReporteSeccion

logger = get_logger(__name__)

ROOT = Path(__file__).parent.parent
PROMPT_PATH = ROOT / "src" / "prompts" / "compliance_prompt.txt"
RETRY_PROMPT_PATH = ROOT / "src" / "prompts" / "retry_prompt.txt"

# Modelos disponibles (registrados en ollama)
MODELO_QWEN = "qwen2.5:14b"
# Default es Qwen 2.5 14B desde m12 (eval confirmo accuracy +1.8pp test,
# precision NC perfecta 1.000 en train, recall NC +4.8pp en test vs
# Llama 3.1 8B). Llama eliminado del sistema.
MODELO_DEFAULT = MODELO_QWEN

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
    """Callback por defecto: replica exactamente el stdout previo al refactor
    Y emite el evento al logger estructurado (stderr).

    Solo los eventos que la CLI imprimia antes producen stdout. El resto
    (structural_done, llm_prep_done, section_eval_done, done) permanecen
    silenciosos por CLI pero TODOS se emiten como `logger.info(event, **data)`
    para que produccion pueda capturar el flujo completo por JSON logs.
    """
    # logger estructurado: siempre emite, para cualquier evento
    logger.info(event, **data)

    # stdout: solo los eventos que la CLI emitia pre-refactor, byte-a-byte
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

    # num_predict escala con numero de lineamientos: ~180 tokens por hallazgo
    # (JSON estructurado) + 200 tokens base. Minimo 800, maximo 4000.
    num_predict = min(4000, max(800, 200 + 180 * len(lineamientos)))

    # Intento 1
    texto_respuesta = llm_chat(
        model=modelo,
        messages=[{"role": "user", "content": prompt}],
        options={
            "temperature": 0.1,
            "num_predict": num_predict,
            "stop": ["<|eot_id|>", "<|end_of_text|>"],
        },
    )

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
        texto_respuesta = llm_chat(
            model=modelo,
            messages=[{"role": "user", "content": retry_prompt}],
            options={
                "temperature": 0.1,
                "num_predict": 400,
                "stop": ["<|eot_id|>", "<|end_of_text|>"],
            },
        )
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
    reglas_filtro: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Prepara evaluaciones para el LLM usando iteracion sobre reglas (m11/m13).

    Flujo rule-driven (no retrieval):
    1. Iterar sobre reglas aplicables al curso (o las provistas via reglas_filtro).
    2. Agrupar por la seccion destino (via metadata seccion_pda).
    3. Producir una evaluacion por (seccion, reglas).

    Desde m13: el caller suele pasar reglas_filtro con solo las reglas SIN
    codigo canonico (las canonicas se manejan con extractor+matcher
    deterministico). En la practica este pipeline LLM-compliance suele
    quedar vacio porque 168/168 reglas no-EST tienen codigo canonico.

    Returns:
        (evaluaciones_llm, hallazgos_deterministicos_ausentes).
    """
    if not codigo_curso:
        return [], []

    reglas = reglas_filtro if reglas_filtro is not None else reglas_aplicables(codigo_curso)
    if not reglas:
        return [], []
    grupos = agrupar_reglas_por_seccion(reglas, secciones)

    evaluaciones = []
    hallazgos_ausentes = []

    for nombre, reglas_grupo in grupos.items():
        if nombre == SECCION_AUSENTE:
            for r in reglas_grupo:
                hallazgos_ausentes.append(hallazgo(
                    regla_id=r["id"],
                    regla=r["descripcion"],
                    cumple=False,
                    evidencia=f"Seccion esperada '{r.get('seccion_pda', '?')}' no encontrada en el PDA",
                    correccion=f"Agregar la seccion correspondiente y declarar: {r['descripcion'][:120]}",
                ))
            continue

        contenido = secciones.get(nombre, "")
        if len(contenido) < 20:
            for r in reglas_grupo:
                hallazgos_ausentes.append(hallazgo(
                    regla_id=r["id"],
                    regla=r["descripcion"],
                    cumple=False,
                    evidencia=f"Seccion '{nombre}' vacia o insuficiente para evaluar",
                    correccion=f"Completar la seccion con: {r['descripcion'][:120]}",
                ))
            continue

        evaluaciones.append({
            "nombre_seccion": nombre,
            "contenido": contenido,
            "lineamientos": [formatear_regla_como_lineamiento(r) for r in reglas_grupo],
        })

    return evaluaciones, hallazgos_ausentes


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

    # m13: extractor LLM de declaraciones (1 call) + matcher deterministico
    hallazgos_declaraciones: list[dict] = []
    reglas_sin_codigo: list[dict] = []
    if codigo_curso:
        emit("extract_start", {})
        declaraciones = extraer_declaraciones(secciones, modelo=modelo)
        reglas_app = reglas_aplicables(codigo_curso)
        reglas_canonicas = [r for r in reglas_app if tiene_codigo_canonico(r)]
        reglas_sin_codigo = [r for r in reglas_app if not tiene_codigo_canonico(r)]
        hallazgos_declaraciones = verificar_declaraciones(reglas_canonicas, declaraciones)
        emit("extract_done", {
            "declaraciones": declaraciones,
            "canonicas": len(reglas_canonicas),
            "sin_codigo": len(reglas_sin_codigo),
            "hallazgos": len(hallazgos_declaraciones),
        })

    emit("llm_prep_start", {})
    # Si codigo_curso esta definido, el extractor ya proceso las canonicas.
    # Pasar reglas_filtro=[] (lista vacia explicita) para desactivar LLM compliance.
    # Sin codigo_curso, comportamiento legacy: evaluar todo via LLM.
    reglas_filtro = reglas_sin_codigo if codigo_curso else None
    evaluaciones, hallazgos_ausentes = preparar_evaluacion(
        secciones, codigo_curso, reglas_filtro=reglas_filtro,
    )
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

    # m13: hallazgos deterministicos producidos por extractor+matcher.
    # Cubren las 168 reglas no-EST con codigo canonico (C1, 1b, SP5, D4, ABET X.Y).
    if hallazgos_declaraciones:
        reporte["resultados"].append({
            "seccion": "__declaraciones_global__",
            "hallazgos": hallazgos_declaraciones,
        })

    # Hallazgos deterministicos para reglas cuya seccion destino no existe
    # en el PDA (o esta vacia): el sistema los emite sin consultar al LLM.
    if hallazgos_ausentes:
        reporte["resultados"].append({
            "seccion": "__seccion_ausente_global__",
            "hallazgos": hallazgos_ausentes,
        })

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

    setup_logging()

    if len(sys.argv) < 2:
        print("Uso: python agent.py <ruta_al_pdf> [codigo_curso] [modelo]")
        print("  modelo: alias 'qwen' (default qwen2.5:14b) o nombre crudo de otro modelo ollama")
        print("Ejemplo: python agent.py 'PDAs/tu_pda.pdf' 22A14 qwen")
        sys.exit(1)

    pdf_path = sys.argv[1]
    codigo = sys.argv[2] if len(sys.argv) > 2 else None

    # Aliases + fallback a nombre crudo (permite probar modelos ad-hoc)
    aliases = {
        "qwen": MODELO_QWEN,
        "14b": MODELO_QWEN,
        "default": MODELO_QWEN,
    }
    if len(sys.argv) > 3:
        modelo = aliases.get(sys.argv[3], sys.argv[3])
    else:
        modelo = MODELO_DEFAULT

    reporte = analizar_pda(pdf_path, codigo, modelo=modelo)

    # Guardar reporte con sufijo del modelo
    sufijo = modelo.replace(":", "-").replace("/", "_")
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

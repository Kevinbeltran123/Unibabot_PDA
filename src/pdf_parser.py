"""
Extraccion y segmentacion de PDAs en formato PDF.

Pipeline: PDF -> texto por pagina -> bloques con metadata -> secciones segmentadas
"""

import re
import fitz  # PyMuPDF
from pathlib import Path


# Secciones conocidas de un PDA (bilingue).
# Se matchean con "contiene" para tolerar variaciones como
# "1. Informacion general" vs "Informacion General del Curso".
SECCIONES_CONOCIDAS = [
    # Estructura principal (numeradas)
    "informacion general", "general information",
    "contexto de la asignatura", "context of the subject",
    "descripcion y proposito", "description and purpose",
    "resultados de aprendizaje", "learning outcomes",
    "resultados de aprendizaje esperados",
    # Sub-secciones pedagogicas
    "estrategia", "pedagogical strategy",
    "metodologia", "methodology",
    "como aprenderan", "how will my students learn",
    "que caracteriza", "what characterizes",
    "tipologia del salon", "classroom typology",
    # Evaluacion
    "criterios para la valoracion", "assessment criteria",
    "retroalimentacion", "feedback",
    "valoracion y la retroalimentacion",
    # Contenido academico
    "cronograma", "schedule", "calendar",
    "bibliografia", "bibliography", "references",
    "competencias", "competences",
    # Administrativo
    "politicas y acuerdos", "policies and agreements",
    "encuadre pedagogico", "pedagogical agreement",
    "revisado y aprobado", "reviewed and approved",
    "informacion del docente", "professor's information",
    "plan de estudios", "syllabus",
    "acciones de mejora", "improvement actions",
]


def extraer_bloques(pdf_path: str) -> list[dict]:
    """Extrae todos los bloques de texto del PDF con su metadata.

    Cada bloque contiene:
        - text: el contenido del bloque
        - page: numero de pagina (0-indexed)
        - font_size: tamano de fuente predominante del bloque
        - is_bold: si la fuente predominante es bold
    """
    doc = fitz.open(pdf_path)
    bloques = []

    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] != 0:  # solo bloques de texto, no imagenes
                continue

            textos = []
            font_sizes = []
            bold_counts = 0
            total_spans = 0

            for line in block["lines"]:
                for span in line["spans"]:
                    texto = span["text"].strip()
                    if texto:
                        textos.append(texto)
                        font_sizes.append(span["size"])
                        total_spans += 1
                        if "bold" in span["font"].lower():
                            bold_counts += 1

            texto_completo = " ".join(textos)
            if not texto_completo.strip():
                continue

            bloques.append({
                "text": texto_completo,
                "page": page_num,
                "font_size": max(font_sizes) if font_sizes else 0,
                "is_bold": (bold_counts / total_spans) > 0.5 if total_spans > 0 else False,
            })

    doc.close()
    return bloques


def normalizar(texto: str) -> str:
    """Quita acentos, numeros de seccion y caracteres especiales para comparacion."""
    texto = texto.lower().strip()
    texto = re.sub(r"^\d+[\.\)]\s*", "", texto)  # quitar "1. ", "2) "
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for original, reemplazo in reemplazos.items():
        texto = texto.replace(original, reemplazo)
    return texto


def es_encabezado(bloque: dict, font_size_promedio: float) -> bool:
    """Determina si un bloque de texto es un encabezado de seccion del PDA.

    Usa doble filtro:
    1. Debe parecer un encabezado visualmente (bold o fuente grande)
    2. Debe matchear alguna seccion conocida del formato PDA
    """
    texto = bloque["text"]

    if len(texto) < 4:
        return False
    if len(texto) > 80:
        return False

    parece_encabezado = bloque["font_size"] > font_size_promedio * 1.2 or bloque["is_bold"]
    if not parece_encabezado:
        return False

    texto_norm = normalizar(texto)
    return any(seccion in texto_norm for seccion in SECCIONES_CONOCIDAS)

    


def segmentar_por_secciones(bloques: list[dict]) -> dict[str, str]:
    """Agrupa los bloques en secciones usando los encabezados detectados.

    Returns:
        Diccionario {nombre_seccion: contenido_texto}
    """
    if not bloques:
        return {}

    # Calcular font_size promedio del documento
    sizes = [b["font_size"] for b in bloques if b["font_size"] > 0]
    font_size_promedio = sum(sizes) / len(sizes) if sizes else 12.0

    secciones = {}
    seccion_actual = "PREAMBULO"
    contenido_actual = []

    for bloque in bloques:
        if es_encabezado(bloque, font_size_promedio):
            # Guardar seccion anterior
            if contenido_actual:
                secciones[seccion_actual] = "\n".join(contenido_actual).strip()
            seccion_actual = bloque["text"]
            contenido_actual = []
        else:
            contenido_actual.append(bloque["text"])

    # Guardar ultima seccion
    if contenido_actual:
        secciones[seccion_actual] = "\n".join(contenido_actual).strip()

    return secciones


def parsear_pda(pdf_path: str) -> dict[str, str]:
    """Pipeline completo: PDF -> secciones segmentadas."""
    bloques = extraer_bloques(pdf_path)
    return segmentar_por_secciones(bloques)


# --- Para explorar los PDAs ---
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Uso: python pdf_parser.py <ruta_al_pdf>")
        print("  Opciones:")
        print("    --bloques    Muestra los bloques crudos con metadata")
        print("    --secciones  Muestra las secciones segmentadas (default)")
        sys.exit(1)

    pdf_path = sys.argv[1]
    modo = sys.argv[2] if len(sys.argv) > 2 else "--secciones"

    if modo == "--bloques":
        bloques = extraer_bloques(pdf_path)
        for i, b in enumerate(bloques):
            print(f"[{i:03d}] page={b['page']} size={b['font_size']:.1f} "
                  f"bold={b['is_bold']} | {b['text'][:100]}")
    else:
        secciones = parsear_pda(pdf_path)
        for nombre, contenido in secciones.items():
            print(f"\n{'='*60}")
            print(f"SECCION: {nombre}")
            print(f"{'='*60}")
            print(contenido[:300] + ("..." if len(contenido) > 300 else ""))

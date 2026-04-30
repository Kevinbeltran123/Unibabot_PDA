"""
Extraccion y segmentacion de PDAs usando Docling (IBM).

Reemplazo del parser basado en PyMuPDF. Ventajas:
- Detecta secciones por layout visual (modelo de deep learning, no keywords).
- Extrae tablas estructuradas via TableFormer (no fragmentos sueltos).
- Nativo en espanol; multilingue por diseno.

Contrato publico identico al parser anterior:
    parsear_pda(pdf_path) -> dict[str, str]
    normalizar(texto) -> str
"""

import re

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import (
    DoclingDocument,
    SectionHeaderItem,
    TableItem,
    TextItem,
    TitleItem,
)

from common.exceptions import PDFParseError
from common.text import normalizar as _normalizar_common


_CONVERTER: DocumentConverter | None = None


def _get_converter() -> DocumentConverter:
    """Cachea el converter para no reinicializar modelos entre llamadas."""
    global _CONVERTER
    if _CONVERTER is None:
        opts = PdfPipelineOptions(do_ocr=False, do_table_structure=True)
        _CONVERTER = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )
    return _CONVERTER


def normalizar(texto: str) -> str:
    """Quita acentos, numeros de seccion y caracteres especiales para comparacion.

    Wrapper de `common.text.normalizar(..., strip_numbering=True)`. Preservado
    como funcion modulo-local porque `src/rules/estructural_checker.py` la
    importa desde pdf_parser.
    """
    return _normalizar_common(texto, strip_numbering=True)


def _tabla_a_texto(table_item: TableItem, doc: DoclingDocument) -> str:
    """Tabla Docling -> markdown una-linea-por-fila.

    Filas/columnas vacias eliminadas (artefactos de fusion de celdas) y
    newlines internos en celdas reemplazados por ' / ' para preservar
    porcentajes y fechas en una sola linea recuperable por la regex de
    EST-007.
    """
    df = table_item.export_to_dataframe(doc=doc)
    df = df.dropna(how="all").dropna(how="all", axis=1)
    df = df.map(lambda v: " / ".join(str(v).split("\n")) if isinstance(v, str) else v)
    return df.to_markdown(index=False)


def _desambiguar_nombre(nombre: str, ya_vistos: set[str]) -> str:
    """Sufija con ' (2)', ' (3)'... si el nombre ya fue usado, para no
    colapsar contenido de dos secciones con el mismo encabezado."""
    if nombre not in ya_vistos:
        return nombre
    i = 2
    while f"{nombre} ({i})" in ya_vistos:
        i += 1
    return f"{nombre} ({i})"


def _limpiar_encabezado(texto: str) -> str:
    """Strip y colapso de whitespace interno en encabezados."""
    return " ".join(texto.split()).strip()


def parsear_pda(pdf_path: str) -> dict[str, str]:
    """Pipeline: PDF -> {nombre_seccion: contenido_texto} en orden de aparicion.

    Reglas:
    - Primera key "PREAMBULO" si hay contenido antes del primer heading (se
      omite si no hay preambulo).
    - SectionHeaderItem y TitleItem abren nueva seccion.
    - TableItem se convierte a texto y se anexa a la seccion actual.
    - TextItem (y subclases como ListItem) se anexan como contenido.
    - Colision de nombres de seccion: sufija con ' (2)', ' (3)', ...
    - Secciones vacias o con contenido trivial (<10 chars) se omiten.
    """
    converter = _get_converter()
    try:
        result = converter.convert(str(pdf_path))
    except Exception as e:
        # Docling puede fallar por PDF corrupto, demasiado grande (OOM),
        # formato no soportado. Envolvemos en PDFParseError para que el
        # caller (evaluate.py / streamlit) pueda manejar el fallo con
        # contexto sin depender del tipo interno de Docling.
        raise PDFParseError(
            f"Docling no pudo parsear '{pdf_path}': {e}"
        ) from e
    doc = result.document

    secciones: dict[str, list[str]] = {"PREAMBULO": []}
    nombres_vistos: set[str] = set()
    seccion_actual = "PREAMBULO"
    # Docling clasifica todos los encabezados al mismo nivel (no distingue
    # h1/h2). En los PDAs de la Universidad de Ibague las secciones de primer
    # nivel estan siempre numeradas ("1. Informacion general", "4. Resultados
    # de Aprendizaje", "8. Bibliografia"); las sub-secciones NO ("Competencias
    # especificas:", "Saber Pro:", "ABET:", "Como bibliografia se utilizara:").
    # Para preservar el agrupamiento que esperan las reglas downstream
    # (declaracion_extractor filtra por nombre de seccion padre), los headings
    # sin numeracion se anexan como texto del padre sin abrir nueva seccion.

    def es_top_level(heading: str) -> bool:
        return bool(re.match(r"^\d+[.)]\s+", heading))

    for item, _level in doc.iterate_items():
        # Orden importa: SectionHeader y Title heredan de TextItem.
        if isinstance(item, (SectionHeaderItem, TitleItem)):
            texto = _limpiar_encabezado(item.text)
            # Mismo filtro que el parser viejo: headings muy cortos suelen ser
            # running headers/footers del PDF mal clasificados por el layout
            # model (ej. "PDA" en cada pagina). Muy largos suelen ser parrafos.
            # Degradamos a texto en vez de descartar para no perder contenido.
            if not texto or len(texto) < 4 or len(texto) > 80:
                if texto:
                    secciones.setdefault(seccion_actual, []).append(texto)
                continue
            if not es_top_level(texto) and seccion_actual != "PREAMBULO":
                # Heading sin numeracion: sub-heading, se anexa al padre.
                secciones.setdefault(seccion_actual, []).append(texto)
                continue
            nombre = _desambiguar_nombre(texto, nombres_vistos)
            nombres_vistos.add(nombre)
            seccion_actual = nombre
            secciones.setdefault(seccion_actual, [])
        elif isinstance(item, TableItem):
            tabla = _tabla_a_texto(item, doc)
            if tabla:
                secciones.setdefault(seccion_actual, []).append(tabla)
        elif isinstance(item, TextItem):
            texto = item.text.strip()
            if texto:
                secciones.setdefault(seccion_actual, []).append(texto)

    # Omite secciones con contenido trivial (<10 chars o solo puntuacion).
    # Motivo: Docling a veces fragmenta una seccion en heading + sub-heading
    # inmediato (ej. "8. Bibliografia" seguido de "Como bibliografia se
    # utilizara:" con el contenido real). Dejar la seccion vacia hace que
    # find_seccion() la devuelva primero con contenido inutil.
    resultado: dict[str, str] = {}
    for nombre, fragmentos in secciones.items():
        contenido = "\n".join(fragmentos).strip()
        if len(contenido) >= 10 and re.search(r"\w", contenido):
            resultado[nombre] = contenido
    return resultado


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python pdf_parser.py <ruta_al_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    secciones = parsear_pda(pdf_path)
    for nombre, contenido in secciones.items():
        print(f"\n{'=' * 60}")
        print(f"SECCION: {nombre}")
        print(f"{'=' * 60}")
        print(contenido[:400] + ("..." if len(contenido) > 400 else ""))

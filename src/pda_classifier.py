"""
Clasificador rule-based: distingue PDAs de la Universidad de Ibague de
cualquier otro PDF que el usuario pueda subir por error (papers, syllabi
de otras instituciones, escaneados sin OCR, manuales, facturas, tesis).

Disenado para correr SINCRONO en el endpoint de upload (antes de encolar
el trabajo costoso). Reutiliza la verificacion estructural ya existente
en `src.rules.estructural_checker.verificar_estructurales` como senal
fuerte: si <=2 de las 11 reglas estructurales cumplen, el documento no
tiene la estructura canonica de un PDA institucional.

No usa LLM. No depende de la red. Latencia esperada <1s sobre el dict
de secciones ya parseado.
"""

from __future__ import annotations

from rules.estructural_checker import verificar_estructurales


# Umbrales (ajustables si la cobertura de PDAs nuevos cambia).
MIN_CHARS_TOTAL = 500          # debajo: PDF vacio / escaneado / muy corto
MIN_SECCIONES = 2              # debajo: documento sin estructura
EST_MIN_PARA_PDA = 6           # >= 6/11 EST CUMPLE => es PDA valido (umbral pasa)
EST_MIN_TEMPLATE_VIEJO = 4     # 4-5/11: posible PDA con template viejo (requiere EST-001)
# 1-3/11: documento academico que NO es PDA (papers, syllabi, manuales).
# Es facil que un doc academico cualquiera matchee 2-3 EST por casualidad
# (p.ej. menciones de "bibliografia", "introduccion", "metodologia"); un PDA
# real practicamente siempre tiene la seccion de "Informacion general"
# institucional. Por eso EST-001 es requisito duro para OLD_TEMPLATE.


def clasificar_documento(secciones: dict[str, str]) -> tuple[bool, str | None, str]:
    """Determina si `secciones` parseadas corresponden a un PDA valido.

    Args:
        secciones: dict {nombre_seccion: contenido} producido por parsear_pda().

    Returns:
        Tupla `(es_pda, code, mensaje)`:
            - es_pda: True si el documento puede procesarse como PDA.
            - code: identificador del caso de rechazo (None si es_pda=True).
              Valores: NOT_A_PDA, EMPTY_OR_SCANNED, INSUFFICIENT_STRUCTURE,
              OLD_TEMPLATE.
            - mensaje: texto en espanol estilo chat para mostrar al usuario.
              Cuando es_pda=True, mensaje contiene un breve acuse del numero
              de secciones canonicas detectadas.
    """
    total_chars = sum(len(c) for c in secciones.values())

    if total_chars < MIN_CHARS_TOTAL:
        return (
            False,
            "EMPTY_OR_SCANNED",
            "No pude extraer texto del documento. ¿Es un PDF escaneado sin OCR? "
            "Necesito un PDA con texto seleccionable para analizarlo.",
        )

    if len(secciones) < MIN_SECCIONES:
        return (
            False,
            "INSUFFICIENT_STRUCTURE",
            "El documento no parece tener la estructura de un PDA. "
            "Asegúrate de adjuntar un Plan de Desarrollo Académico de la "
            "Universidad de Ibagué.",
        )

    hallazgos_est = verificar_estructurales(secciones)
    n_cumple = sum(1 for h in hallazgos_est if h["estado"] == "CUMPLE")
    total = len(hallazgos_est)

    if n_cumple == 0:
        return (
            False,
            "NOT_A_PDA",
            "Este documento no parece ser un PDA. No reconocí ninguna de las "
            "secciones canónicas (información general, estrategia pedagógica, "
            "RAE, evaluación, cronograma, bibliografía). Verifica que el archivo "
            "sea un Plan de Desarrollo Académico de la Universidad de Ibagué.",
        )

    # EST-001 (Informacion general institucional) es requisito duro para
    # categorizar como OLD_TEMPLATE. Sin ella el documento es casi
    # seguramente un paper o syllabus que coincidio en algunos EST por
    # casualidad (terminologia academica generica).
    est_001_cumple = next(
        (h["estado"] == "CUMPLE" for h in hallazgos_est if h["regla_id"] == "EST-001"),
        False,
    )

    if n_cumple < EST_MIN_TEMPLATE_VIEJO or not est_001_cumple:
        return (
            False,
            "INSUFFICIENT_STRUCTURE",
            f"Este documento parece académico pero no es un PDA. Solo reconocí "
            f"{n_cumple}/{total} secciones canónicas y le falta la sección "
            "institucional de información general. ¿Quizás subiste un "
            "syllabus, un plan de curso de otra institución, o un paper?",
        )

    if n_cumple < EST_MIN_PARA_PDA:
        faltantes = [
            h["regla_id"] for h in hallazgos_est if h["estado"] == "NO CUMPLE"
        ]
        return (
            False,
            "OLD_TEMPLATE",
            f"El documento parece ser un PDA pero le faltan {total - n_cumple} "
            f"secciones canónicas ({', '.join(faltantes[:5])}"
            f"{'...' if len(faltantes) > 5 else ''}). "
            "¿Es una versión vieja del template institucional? Verifica que estés "
            "usando la versión actual del PDA antes de subirlo.",
        )

    return (
        True,
        None,
        f"Documento aceptado: reconocí {n_cumple}/{total} secciones canónicas.",
    )

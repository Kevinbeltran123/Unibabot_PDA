"""
Aplica labels de Claude como segundo annotator sobre data/gold_candidates_test.json.

Fundamento: Claude leyo las secciones de los 3 PDAs test y produjo
predicciones independientes de CUMPLE / NO CUMPLE para las entradas
review (sin label del LLM) y medium (con label del LLM).

Reglas de consolidacion:
- Si ambos annotators (LLM local + Claude) coinciden -> confidence=high
- Si difieren -> confidence=review con ambas predicciones en notas
- Si solo Claude tiene prediccion (entrada era review) -> confidence=medium
  (se necesita segunda validacion por humano)

Script de un solo uso. Preserva el JSON intermedio para trazabilidad.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CANDIDATES_PATH = ROOT / "data" / "gold_candidates_test.json"

# Labels de Claude con evidencia concreta extraida del PDA
# Formato: (pda_file, regla_id) -> (estado, justificacion_claude)
CLAUDE_LABELS: dict[tuple[str, str], tuple[str, str]] = {
    # Arquitectura de Software (22A35)
    ("PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf", "COMP-124"):
        ("CUMPLE", "RAE declara explicitamente 'C2. Disena sistemas, componentes o procesos, para satisfacer requerimientos, restricciones, especificaciones tecnicas relacionadas con los sistemas de informacion y el desarrollo de software'."),
    ("PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf", "COMP-125"):
        ("NO CUMPLE", "La seccion RAE no declara la competencia especifica C3 (Formula y evalua proyectos)."),
    ("PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf", "COMP-126"):
        ("NO CUMPLE", "No se menciona 1a: Comunicacion en lengua materna."),
    ("PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf", "COMP-127"):
        ("NO CUMPLE", "No se menciona 1h: Pensamiento critico."),
    ("PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf", "COMP-128"):
        ("NO CUMPLE", "RAE menciona 'vision sistemica' pero no declara competencia 1l (Pensamiento sistemico) explicitamente."),
    ("PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf", "COMP-129"):
        ("NO CUMPLE", "No hay mencion de SABER PRO SP2 Lectura critica."),

    # Gestion TI (22A32)
    ("PDA - Gestión TI 2026A.pdf", "COMP-106"):
        ("NO CUMPLE", "La seccion Estrategia pedagogica no declara la competencia especifica C2 (Disena sistemas)."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-107"):
        ("NO CUMPLE", "No se menciona 1e Cultura cientifica y tecnologica."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-108"):
        ("CUMPLE", "Estrategia pedagogica declara 'Trabajo colaborativo, promoviendo el desarrollo de competencias en liderazgo, planificacion y toma de decisiones' -- equivalente a 1i Trabajo en equipo."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-109"):
        ("NO CUMPLE", "No se menciona 1j Espiritu emprendedor."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-110"):
        ("NO CUMPLE", "No hay mencion de SABER PRO SP4 Competencias ciudadanas."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-111"):
        ("NO CUMPLE", "Cronograma menciona Proyecto Final con equipos pero no declara indicador ABET 5.1 explicitamente."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-112"):
        ("NO CUMPLE", "No declara indicador ABET 5.2 explicitamente."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-113"):
        ("NO CUMPLE", "No declara indicador ABET 6.3 explicitamente."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-114"):
        ("CUMPLE", "Estrategia pedagogica declara 'Dimension D1 Transdisciplinar D6 Regional' explicitamente."),
    ("PDA - Gestión TI 2026A.pdf", "COMP-115"):
        ("CUMPLE", "Estrategia pedagogica declara 'D6 Regional' explicitamente."),

    # Pensamiento Computacional (22A52)
    ("PDA - Pensamiento computacional 2026A - Firmas.pdf", "COMP-001"):
        ("NO CUMPLE", "No declara competencia especifica C1 (Analiza) explicitamente."),
    ("PDA - Pensamiento computacional 2026A - Firmas.pdf", "COMP-002"):
        ("NO CUMPLE", "No se menciona 1b Comprension lectora / comprension."),
    ("PDA - Pensamiento computacional 2026A - Firmas.pdf", "COMP-003"):
        ("NO CUMPLE", "No se menciona 1g Aprender a aprender."),
    ("PDA - Pensamiento computacional 2026A - Firmas.pdf", "COMP-004"):
        ("NO CUMPLE", "No declara competencia 1l Pensamiento sistemico explicitamente."),
    ("PDA - Pensamiento computacional 2026A - Firmas.pdf", "COMP-005"):
        ("NO CUMPLE", "No hay mencion de SABER PRO SP5 Ingles."),
    ("PDA - Pensamiento computacional 2026A - Firmas.pdf", "COMP-006"):
        ("CUMPLE", "Estrategia pedagogica declara 'Dimension Internacional' explicitamente (=D4)."),
}


def main():
    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        candidatos = json.load(f)

    agreed = 0
    disagreed = 0
    only_claude = 0
    unchanged = 0

    for c in candidatos:
        k = (c["pda_file"], c["regla_id"])
        if k not in CLAUDE_LABELS:
            unchanged += 1
            continue

        claude_estado, claude_nota = CLAUDE_LABELS[k]
        llm_estado = c.get("estado_esperado")

        if c["confidence"] == "review":
            # Solo Claude tiene prediccion; pasa a medium para validacion humana final
            c["estado_esperado"] = claude_estado
            c["nota"] = f"[Claude annotator] {claude_nota}"
            c["confidence"] = "medium"
            only_claude += 1
        elif c["confidence"] == "medium":
            if llm_estado == claude_estado:
                # Ambos coinciden -> high confidence
                c["nota"] = f"[LLM+Claude agree] {claude_nota}"
                c["confidence"] = "high"
                agreed += 1
            else:
                # Disagreement -> review
                c["nota"] = f"[DISAGREE] LLM={llm_estado} Claude={claude_estado}. Claude: {claude_nota}. LLM_nota: {c['nota'][:150]}"
                c["estado_esperado"] = None
                c["confidence"] = "review"
                disagreed += 1

    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(candidatos, f, ensure_ascii=False, indent=2)

    print(f"Claude annotator aplicado a {CANDIDATES_PATH.name}:")
    print(f"  LLM+Claude coinciden (->high): {agreed}")
    print(f"  Disagreement (->review): {disagreed}")
    print(f"  Solo Claude (review->medium): {only_claude}")
    print(f"  Sin cambios (EST high): {unchanged}")

    from collections import Counter
    conf = Counter(c["confidence"] for c in candidatos)
    print(f"\nNueva distribucion: {dict(conf)}")


if __name__ == "__main__":
    main()

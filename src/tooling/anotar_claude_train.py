"""
Claude como segundo annotator sobre data/gold_candidates_train.json.

Tras filtrar candidates que ya estan en gold_labels.json (duplicados),
quedan 7 medium + 1 review (COMP-119 UI/UX) que requieren juicio.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
CANDIDATES_PATH = ROOT / "data" / "gold_candidates_train.json"

# Labels de Claude basados en lectura del PDA
CLAUDE_LABELS: dict[tuple[str, str, str], tuple[str, str]] = {
    # Intelligent Agents (PDA en ingles; LLM predice razonablemente bien sobre secciones de estrategia)
    ("PDA - Intelligent Agents 2026A-01.docx.pdf", "Pedagogical Strategy(ies)", "COMP-100"):
        ("NO CUMPLE", "La seccion Pedagogical Strategy no declara la competencia especifica C1 (Analiza y modela fenomenos); describe metodologia ABP."),
    ("PDA - Intelligent Agents 2026A-01.docx.pdf", "Pedagogical Strategy(ies)", "COMP-101"):
        ("NO CUMPLE", "La seccion Pedagogical Strategy no declara la competencia especifica C2 (Disena sistemas)."),
    ("PDA - Intelligent Agents 2026A-01.docx.pdf", "What methodology guides the activities?", "COMP-102"):
        ("NO CUMPLE", "La seccion 'What methodology guides the activities?' no declara 1c (Comunicacion en segunda lengua); se enfoca en como se ensena."),
    ("PDA - Intelligent Agents 2026A-01.docx.pdf", "Pedagogical Strategy(ies)", "COMP-103"):
        ("CUMPLE", "La seccion menciona 'practical application of techniques used by intelligent agents in real-world cases and challenges', lo que implica pensamiento critico (1h)."),
    ("PDA - Intelligent Agents 2026A-01.docx.pdf", "Pedagogical Strategy(ies)", "COMP-105"):
        ("CUMPLE", "La seccion declara 'the international dimension is integrated through the delivery of materials and presentation of results in English' -- D4 Internacional."),

    # UI/UX
    ("PDA - Desarrollo aplicaciones UIUX - 2026A 02.pdf", "Competencias específicas:", "COMP-122"):
        ("NO CUMPLE", "La seccion Competencias especificas no declara la dimension D1 Transdisciplinar (las dimensiones van en otra seccion)."),
    ("PDA - Desarrollo aplicaciones UIUX - 2026A 02.pdf", "Competencias específicas:", "COMP-123"):
        ("NO CUMPLE", "La seccion Competencias especificas no declara la dimension D5 Espiritu emprendedor."),

    # Review entry: COMP-119 (conocido del m8b)
    ("PDA - Desarrollo aplicaciones UIUX - 2026A 02.pdf", "Competencias / Resultados de Aprendizaje", "COMP-119"):
        ("NO CUMPLE", "El PDA de UI/UX declara 1e (Cultura cientifica) donde la regla exige 1g (Aprender a aprender). Caso conocido documentado en m8b."),
}


def main():
    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        candidatos = json.load(f)

    agreed = 0
    disagreed = 0
    only_claude = 0
    unchanged = 0

    for c in candidatos:
        k = (c["pda_file"], c["seccion"], c["regla_id"])
        if k not in CLAUDE_LABELS:
            unchanged += 1
            continue

        claude_estado, claude_nota = CLAUDE_LABELS[k]
        llm_estado = c.get("estado_esperado")

        if c["confidence"] == "review":
            c["estado_esperado"] = claude_estado
            c["nota"] = f"[Claude annotator] {claude_nota}"
            c["confidence"] = "medium"
            only_claude += 1
        elif c["confidence"] == "medium":
            if llm_estado == claude_estado:
                c["nota"] = f"[LLM+Claude agree] {claude_nota}"
                c["confidence"] = "high"
                agreed += 1
            else:
                c["nota"] = f"[DISAGREE] LLM={llm_estado} Claude={claude_estado}. Claude: {claude_nota}"
                c["estado_esperado"] = None
                c["confidence"] = "review"
                disagreed += 1

    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(candidatos, f, ensure_ascii=False, indent=2)

    print(f"Claude annotator aplicado a {CANDIDATES_PATH.name}:")
    print(f"  LLM+Claude coinciden (->high): {agreed}")
    print(f"  Disagreement (->review): {disagreed}")
    print(f"  Solo Claude (review->medium): {only_claude}")
    print(f"  Sin cambios: {unchanged}")

    from collections import Counter
    conf = Counter(c["confidence"] for c in candidatos)
    print(f"\nNueva distribucion: {dict(conf)}")


if __name__ == "__main__":
    main()

# Reporte de generacion del gold expandido (m10)

## Resumen

Expansion del gold desde 40 entradas (3 PDAs originales, post-limpieza de Modelos y Simulacion) a **112 entradas totales** con distincion explicita train/test hold-out:

| Split | Archivo | PDAs | Entradas | CUMPLE | NO CUMPLE | Balance NC |
|-------|---------|------|----------|--------|-----------|------------|
| **train/dev** | `data/gold_labels.json` | 3 originales | 57 | 49 | 8 | 14% |
| **test hold-out** | `data/gold_labels_test.json` | 3 nuevos | 55 | 34 | 21 | 38% |
| **TOTAL** | -- | 6 | **112** | 83 | 29 | 26% |

Escalado 2.8x respecto al baseline labelable (40). Clase NO CUMPLE sube de 2/48 (4%) a 29/112 (26%), **13x mas senial** para medir precision/recall de deteccion de incumplimiento.

## Distribucion por PDA

### Train (3 PDAs originales)

| PDA | Codigo | EST | COMP | Total |
|-----|--------|-----|------|-------|
| Intelligent Agents | 22A14 | 11 | 9 | 20 |
| Sistemas Control Automatico | 22A12 | 11 | 4 | 15 |
| Desarrollo UI/UX | 22A31 | 11 | 11 | 22 |

Note: Intelligent Agents y UI/UX superan los COMP planeados porque la misma regla COMP puede aparecer en multiples secciones del PDA (e.g. "Pedagogical Strategy" y "What methodology guides the activities?"). Son entradas legitimas: cada par (seccion, regla) es evaluable independientemente.

### Test hold-out (3 PDAs nuevos)

| PDA | Codigo | EST | COMP | Total |
|-----|--------|-----|------|-------|
| Arquitectura de Software | 22A35 | 11 | 6 | 17 |
| Gestion TI | 22A32 | 11 | 10 | 21 |
| Pensamiento Computacional | 22A52 | 11 | 6 | 17 |

## Metodologia de etiquetado (dual annotator)

Cada entrada pasa por dos annotators independientes:

### Annotator 1: agente local (LLM silver)
Para EST-001..EST-011: `src/rules/estructural_checker.py` (reglas deterministas). Accuracy ~100% sobre estas 11 reglas cuando el PDA esta bien parseado.

Para COMP (competencias): `src/agent.py analizar_pda()` con Llama 3.1 8B via ollama. Produce hallazgos tipo `{estado, evidencia, correccion}`.

### Annotator 2: Claude (juicio directo)
Claude lee las secciones relevantes del PDA (via `parsear_pda`) y produce predicciones independientes. Ver `src/tooling/anotar_claude_train.py` y `anotar_claude_test.py` para las labels exactas con justificacion textual.

### Consolidacion

- Ambos coinciden -> `confidence=high` (gold listo para uso).
- Uno no predice (LLM fuera de top_k) -> `confidence=medium` (Claude prediction valida; requiere sanity check humano antes de prod).
- Discrepancia -> `confidence=review` con ambas predicciones; usuario resuelve (1 caso: COMP-124, resuelto CUMPLE con evidencia textual directa).

## Conteos por confidence (antes de fusion)

### Train candidates (gold_candidates_train.json)
- high: 40 (33 EST + 7 COMP LLM+Claude agree)
- medium: 11 (Claude-only labels)
- review: 0 (tras anotacion de Claude)

### Test candidates (gold_candidates_test.json)
- high: 37 (33 EST + 4 COMP LLM+Claude agree)
- medium: 17 (Claude-only labels)
- review: 1 -> **resuelto COMP-124 = CUMPLE** (texto PDA declara C2 explicitamente)

## Casos notables

### Disagreements LLM vs Claude (tras anotar)

**1 solo caso:** COMP-124 (Arquitectura de Software, C2 "Disena sistemas").

- LLM: NO CUMPLE ("la seccion no declara explicitamente C2").
- Claude: CUMPLE (texto exacto "C2. Disena sistemas, componentes o procesos..." presente en RAE).
- **Resolucion:** CUMPLE. El LLM ignoro la declaracion explicita en el texto, aparentemente por confusion entre "declarar" y "desarrollar".

### Nuevos NO CUMPLE descubiertos

Del etiquetado exhaustivo salieron **27 nuevos NO CUMPLE** (6 train + 21 test) que el sistema no detectaba antes por falta de gold. Estos corresponden a competencias que aplican al curso pero el PDA no las declara:

**Train (6 NO CUMPLE nuevos):**
- UI/UX no declara dimensions D1 (Transdisciplinar) ni D5 (Espiritu emprendedor) en seccion Competencias especificas.
- Intelligent Agents no declara C1 ni C2 en seccion Pedagogical Strategy.
- Intelligent Agents no declara 1c (Comunicacion en segunda lengua) en seccion "What methodology guides activities".

**Test (21 NO CUMPLE):**
- Arquitectura: no declara C3, 1a, 1h, 1l, SP2.
- Gestion TI: no declara C2, 1e, 1j, SP4, ABET 5.1/5.2/6.3.
- Pensamiento Computacional: no declara C1, 1b, 1g, 1l, SP5.

**CUMPLE descubiertos:**
- Gestion TI declara D1 Transdisciplinar, D6 Regional, 1i Trabajo en equipo.
- Pensamiento Computacional declara D4 Internacional.

### Cobertura de retrieval (LLM agent)

De 22 COMP aplicables en test, el agente evaluo solo 5 en sus reportes (otros 17 quedaron fuera del top_k). Este ratio bajo (23%) confirma que el retrieval actual no recupera todas las reglas aplicables, especialmente ABET y competencias genericas globales. Punto de mejora futuro: ajustar top_k o incluir dimension/SABER PRO rules via metadata como se hizo con dimension rules (via `recuperar_dimension_rules`).

## Aportes de los 3 PDAs nuevos

1. **Mas clases positivas NO CUMPLE** (21 vs 2 en train original). Esto permite:
   - Precision/recall de NO CUMPLE con resolucion estadistica (antes 1 TP flipaba la metrica entera).
   - Validar que el agente detecta incumplimientos estructuralmente, no por memorizacion.

2. **Nuevos tipos de regla evaluados:**
   - ABET 5.1, 5.2, 6.3 (Gestion TI) -- tipo `abet` nunca antes en gold.
   - Dimensiones D1, D4, D6 (distintas de las del train que tenia D1 y D5).

3. **Diversidad semestral:**
   - 22A52 (Pensamiento Computacional) es del nucleo basico disciplinar, no Ingenieria de Sistemas. Valida que el pipeline generaliza a otros programas academicos.

4. **Diversidad de formato:**
   - Arquitectura de Software: incluye datos de contacto docente extensos.
   - Gestion TI: ~6K caracteres en "Plan de estudios".
   - Pensamiento Computacional: estructura "Contenido tematico resumido" no comun.

## Como reproducir

```bash
# 1. Generar candidatos (requiere ollama corriendo)
python src/tooling/generar_gold_exhaustivo.py \
    --pdas "PDA - Intelligent Agents 2026A-01.docx.pdf|PDA - Sistemas de Control Automatico 2026A GR01.pdf|PDA - Desarrollo aplicaciones UIUX - 2026A 02.pdf" \
    --cursos "22A14,22A12,22A31" \
    --output data/gold_candidates_train.json

python src/tooling/generar_gold_exhaustivo.py \
    --pdas "PDA - Arquitectura de Software - 2026A - Gr03 LM.pdf|PDA - Gestión TI 2026A.pdf|PDA - Pensamiento computacional 2026A - Firmas.pdf" \
    --cursos "22A35,22A32,22A52" \
    --output data/gold_candidates_test.json

# 2. Aplicar Claude como segundo annotator
python src/tooling/anotar_claude_train.py
python src/tooling/anotar_claude_test.py

# 3. Fusionar con gold existente
python src/tooling/fusionar_gold.py \
    --candidates data/gold_candidates_train.json \
    --existing data/gold_labels.json \
    --output data/gold_labels.json \
    --include-review

python src/tooling/fusionar_gold.py \
    --candidates data/gold_candidates_test.json \
    --output data/gold_labels_test.json \
    --include-review

# 4. Evaluar
python src/evaluate.py --tag m10_train --modelo llama3.1:8b
python src/evaluate.py --gold-path data/gold_labels_test.json --tag m10_test --modelo llama3.1:8b
```

## Proximo paso

Ejecutar `evaluate.py` con los dos gold paths y registrar metricas m10 en `results/evaluation_report.md`. Criterios de exito:

- **Train:** accuracy >= 0.90, matched >= 54/57. Las 8 NO CUMPLE deberian detectarse (recall NC >= 0.75).
- **Test hold-out:** accuracy >= 0.85, matched >= 47/55. Prueba si el sistema generaliza sin haber visto esos gold labels.
- **Latencia total:** <= 600s para 6 PDAs (baseline m8b era 236s para 4).

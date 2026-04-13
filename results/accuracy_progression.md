# Progresion de accuracy del pipeline UnibaBot PDA

Dataset de evaluacion: 48 entradas gold etiquetadas manualmente sobre 4 PDAs reales.

| Snapshot | Mejora | Accuracy | Prec NC | Recall NC | JSON valid | Latencia | FP | TN | Matched |
|----------|--------|----------|---------|-----------|------------|----------|----|----|---------|
| `baseline` | Llama 3.2 3B sin mejoras | 0.351 | 0.000 | 0.000 | 0.986 | 565s | 23 | 13 | 37/48 |
| `m8_rule_based` | + rule-based hybrid | **0.927** | 0.000 | 0.000 | 0.978 | 444s | 2 | 38 | 41/48 |

## Analisis por mejora

### Mejora 8 (rule-based hybrid)

**Cambio principal:** Las 11 reglas estructurales (EST-001 a EST-011) se verifican deterministicamente con funciones Python en vez de pasar por el LLM. Ademas, estas reglas se filtran del retrieval de ChromaDB antes de enviar al LLM.

**Impacto medido:**
- Accuracy: +57.6 puntos porcentuales (0.351 → 0.927)
- Falsos positivos: 23 → 2 (reduccion del 91%)
- Verdaderos negativos: 13 → 38 (+192%)
- Latencia: -21% (el LLM recibe ~30% menos tokens al no tener reglas estructurales en el prompt)
- JSON valid: leve caida de 0.986 a 0.978 (dentro del margen de varianza)

**Por que funciono:** El baseline tenia un problema conceptual grave. Evaluaba cada seccion del PDA contra las top-5 reglas del retrieval, lo cual generaba casos absurdos como "la seccion de Estrategia Pedagogica no contiene bibliografia → NO CUMPLE". Pero bibliografia es una regla **global** al PDA, no de una seccion individual. El rule-based razona sobre el PDA completo y elimina estos artefactos.

**Lo que no se arreglo:** Precision/Recall de NO CUMPLE siguen en 0.000. Los 2 NO CUMPLE reales del gold son de reglas de competencias (COMP-119 y COMP-074), no estructurales. El LLM sigue prediciendo CUMPLE para esos casos. Este problema debe atacarse en las siguientes mejoras.

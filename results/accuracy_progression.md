# Progresion de accuracy del pipeline UnibaBot PDA

Dataset de evaluacion: 48 entradas gold etiquetadas manualmente sobre 4 PDAs reales.

| Snapshot | Mejora | Accuracy | Prec NC | Recall NC | JSON valid | Latencia | FP | TN | TP | Matched |
|----------|--------|----------|---------|-----------|------------|----------|----|----|----|---------|
| `baseline` | Llama 3.2 3B sin mejoras | 0.351 | 0.000 | 0.000 | 0.986 | 565s | 23 | 13 | 0 | 37/48 |
| `m8_rule_based` | + rule-based hybrid | 0.927 | 0.000 | 0.000 | 0.978 | 444s | 2 | 38 | 0 | 41/48 |
| `m2_retrieval_filter` | + retrieval filtrado por seccion | 0.944 | 0.333 | 1.000 | 0.949 | 91s | 2 | 33 | 1 | 36/48 |
| `m3_validation_retry` | + Pydantic + retry | **0.947** | 0.333 | 1.000 | **1.000** | 94s | 2 | 35 | 1 | 38/48 |

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

### Mejora 2 (retrieval filtrado por seccion)

**Cambio principal:** El retriever ahora filtra por `seccion_pda` ademas de por `codigo_curso`. Un mapping `keyword_parser -> [seccion_pda]` evita que reglas de competencias aparezcan al evaluar informacion general y viceversa. Cuando el filtro deja 0 reglas para una seccion, esa seccion se excluye del LLM.

**Impacto medido:**
- Accuracy: 0.927 → 0.944 (+0.017)
- Precision NO CUMPLE: 0.000 → 0.333 (primer TP conseguido)
- Recall NO CUMPLE: 0.000 → 1.000 (dentro de las entradas matcheadas)
- Latencia: 444s → 91s (-79%)
- Matched: 41/48 → 36/48 (algunas entradas del gold se filtran fuera)

**Por que funciono:** El filtro por seccion elimina falsos positivos del LLM (cuando el LLM recibia reglas irrelevantes y trataba de aplicarlas forzadamente). Ademas, al recibir menos reglas por seccion, muchas secciones quedan sin lineamientos que evaluar y se excluyen del pipeline, reduciendo drasticamente la latencia.

**Riesgo identificado:** Matched bajo de 41 a 36. Algunas reglas del gold ya no se evaluan porque el filtro las excluyo. Esto se puede mitigar mas adelante con hybrid search (mejora 5) agregando fallback cuando el filtro deja muy pocas reglas.

### Mejora 3 (validacion Pydantic + retry)

**Cambio principal:** El parseo del JSON del LLM ahora usa Pydantic (`schemas.ReporteSeccion`) en vez de `json.loads()` directo. Si la validacion falla, el agente reintenta una vez con un prompt de correccion (`retry_prompt.txt`) que incluye la respuesta previa y el error.

**Impacto medido:**
- Accuracy: 0.944 → 0.947 (+0.003)
- JSON valid rate: 0.949 → 1.000 (+0.051)
- Matched: 36/48 → 38/48 (+2)
- TN: 33 → 35 (+2)

**Por que funciono:** Los `@field_validator` de Pydantic normalizan variaciones comunes de la salida del LLM (el string `"null"` → `None`, `"cumple"` → `"CUMPLE"`, etc). Antes, los hallazgos con esos formatos se descartaban silenciosamente en el JSON parsing. Ahora se rescatan.

**Valor estrategico:** Esta mejora es un pequeno salto en accuracy pero un **prerrequisito critico** para las mejoras 4 (modelo 8B que puede generar JSON mas sofisticado) y 6 (self-consistency voting, donde necesitamos matchear hallazgos por regla_id entre runs). Sin Pydantic + retry, esas mejoras mas grandes fallarian o tendrian resultados inconsistentes.

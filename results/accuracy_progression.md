# Progresion de accuracy del pipeline UnibaBot PDA

Dataset de evaluacion: 48 entradas gold etiquetadas manualmente sobre 4 PDAs reales.

| Snapshot | Mejora | Accuracy | Prec NC | Recall NC | JSON valid | Latencia | FP | TN | TP | Matched |
|----------|--------|----------|---------|-----------|------------|----------|----|----|----|---------|
| `baseline` | Llama 3.2 3B sin mejoras | 0.351 | 0.000 | 0.000 | 0.986 | 565s | 23 | 13 | 0 | 37/48 |
| `m8_rule_based` | + rule-based hybrid | 0.927 | 0.000 | 0.000 | 0.978 | 444s | 2 | 38 | 0 | 41/48 |
| `m2_retrieval_filter` | + retrieval filtrado por seccion | 0.944 | 0.333 | 1.000 | 0.949 | 91s | 2 | 33 | 1 | 36/48 |
| `m3_validation_retry` | + Pydantic + retry | 0.947 | 0.333 | 1.000 | 1.000 | 94s | 2 | 35 | 1 | 38/48 |
| `m1_few_shot` | + few-shot (2 CUMPLE + 1 NO CUMPLE) | 0.951 | 0.333 | 1.000 | 1.000 | 91s | 2 | 38 | 1 | 41/48 |
| `m4_llama31_8b` | + Llama 3.1 8B como modelo LLM | **1.000** | **1.000** | **1.000** | 1.000 | 189s | **0** | **40** | 1 | 41/48 |

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

### Mejora 1 (few-shot prompts)

**Cambio principal:** El prompt incluye 3 ejemplos completos (seccion + contenido + lineamientos + respuesta JSON correcta) antes de la instruccion. Los ejemplos cubren dos casos CUMPLE (con cita textual y con declaracion explicita) y uno NO CUMPLE (por competencia ausente).

**Impacto medido (m1 vs m3):**
- Accuracy: 0.947 → 0.951 (+0.004)
- Matched: 38/48 → 41/48 (+3)
- TN: 35 → 38 (+3)
- Latencia: 94s → 91s (leve reduccion)
- Precision/Recall NO CUMPLE: mantiene 0.333 / 1.000

**Iteraciones del experimento:**
1. **v1 (1 CUMPLE + 2 NO CUMPLE):** accuracy cayo a 0.902 porque el modelo se sesgo a predecir mas NO CUMPLE. Los falsos positivos subieron de 2 a 4.
2. **v2 (2 CUMPLE + 1 NO CUMPLE + regla agresiva "si menciona el concepto es CUMPLE"):** accuracy subio a 0.976 pero recall NO CUMPLE cayo a 0 -- modelo demasiado permisivo. Descartada para auditoria (falsos negativos son inaceptables).
3. **v3 (2 CUMPLE + 1 NO CUMPLE, sin regla agresiva):** balance optimo. Accuracy 0.951 y mantiene deteccion de NO CUMPLE.

**Aprendizaje clave:** Los ejemplos few-shot introducen un prior estadistico implicito. La proporcion CUMPLE:NO CUMPLE del few-shot debe matchear la distribucion real del dataset (~78% CUMPLE en los PDAs reales). Instrucciones categoricas como "si menciona X es CUMPLE" sesgan demasiado al modelo.

### Mejora 4 (Llama 3.1 8B) -- CHECKPOINT CRITICO

**Cambio principal:** El modelo LLM cambia de `llama3.2` (3B parametros) a `llama3.1:8b` (8B parametros). El resto del pipeline (rule-based, retrieval filtrado, Pydantic, few-shot) se mantiene igual.

**Impacto medido (m4 vs m1):**
- Accuracy: 0.951 → **1.000** (+0.049)
- Precision NO CUMPLE: 0.333 → **1.000** (+0.667)
- Recall NO CUMPLE: mantiene 1.000
- FP: 2 → 0 (perfecto)
- TN: 38 → 40
- Latencia: 91s → 189s (~2x, esperado por modelo mas grande)

**Resultado:** El pipeline alcanza **accuracy perfecta 1.000** sobre 41 entradas matcheadas del gold (41 de 48, los 7 restantes son casos donde el filtro de retrieval excluye la regla antes de llegar al LLM).

**Por que funciono:** Los 2 FP que tenia m1 eran casos en que el 3B confundia similitud semantica con cumplimiento estricto. El 8B razona mejor sobre contexto, distingue "el PDA habla de pensamiento critico" vs "el PDA declara la competencia 1h: Pensamiento critico" como lineamiento formal.

**Cambio de default:** `MODELO_DEFAULT` en `src/agent.py` se actualiza de `MODELO_BASELINE` (llama3.2 3B) a `MODELO_8B` (llama3.1:8b). El 3B sigue disponible como `baseline` por CLI.

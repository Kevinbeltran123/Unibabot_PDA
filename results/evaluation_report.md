# Reporte de evaluacion -- UnibaBot PDA

## Resumen ejecutivo

Se desarrollo un agente para verificacion de cumplimiento de Planes de Desarrollo Academico (PDA) de la Universidad de Ibague. El sistema combina extraccion de PDF, busqueda semantica (RAG) sobre 179 lineamientos institucionales, y un modelo de lenguaje Llama 3.2 3B via ollama.

Se implementaron dos variantes del modelo: un **baseline** (Llama 3.2 3B sin fine-tuning) y un **fine-tuneado** con QLoRA sobre 42 ejemplos generados a partir de los 4 PDAs reales disponibles. Durante la evaluacion comparativa se identifico un hallazgo importante que se documenta a continuacion.

## Metodologia

### Pipeline de evaluacion

Para cada PDA se ejecuto el mismo pipeline:

```
PDF -> pdf_parser.py -> secciones -> rag/retriever.py -> lineamientos -> LLM -> reporte JSON
```

### PDAs de prueba

| PDA | Curso | Codigo |
|-----|-------|--------|
| PDA - Intelligent Agents 2026A-01 | Agentes Inteligentes | 22A14 |
| PDA - Sistemas de Control Automatico | Sistemas de Control Automatico | 22A12 |
| PDA - Desarrollo aplicaciones UIUX | Desarrollo de Aplicaciones UI/UX | 22A31 |
| PDA - Modelos y Simulacion | Modelos y Simulacion | (no mapeado) |

## Resultados -- Modelo baseline (Llama 3.2 3B)

El modelo baseline genero reportes con la estructura esperada. Ejemplo de hallazgo:

```json
{
  "seccion": "3. Description and purpose of the course",
  "hallazgos": [
    {
      "regla": "El PDA debe declarar la competencia C2",
      "estado": "CUMPLE",
      "evidencia": "La seccion menciona que los estudiantes acquire the ability to design, describe, and develop the different learning methods",
      "correccion": null
    }
  ]
}
```

### Fortalezas del baseline

- Genera JSON valido consistentemente
- Cita fragmentos textuales del PDA como evidencia cuando identifica cumplimiento
- Responde en espanol aunque el PDA este en ingles (flexibilidad bilingue)
- Tiempo por seccion: ~15-20 segundos en MacBook Pro M3 18GB

### Debilidades del baseline

- Algunas evidencias son vagas ("La seccion no menciona explicitamente...")
- Correcciones genericas ("Revisar y agregar la competencia...")
- Falsos positivos al evaluar competencias contra secciones donde no aplican (evalua "informacion general" contra reglas de competencias)

## Resultados -- Modelo fine-tuneado (QLoRA)

### Configuracion del entrenamiento

| Parametro | Valor |
|-----------|-------|
| Modelo base | unsloth/Llama-3.2-3B-Instruct |
| Tecnica | QLoRA (4-bit NF4 + LoRA) |
| LoRA rank (r) | 16 |
| LoRA alpha | 16 |
| Target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj |
| Dataset train | 42 ejemplos |
| Dataset validation | 5 ejemplos |
| Epochs | 3 |
| Learning rate | 2e-4 |
| Batch size efectivo | 8 (2 * 4 gradient accumulation) |
| Hardware | Google Colab GPU T4 |

### Metricas de entrenamiento

| Epoch | Train loss | Validation loss |
|-------|-----------|-----------------|
| Inicio | 1.6365 | -- |
| 1 | -- | 1.5223 |
| 2 | -- | 1.2483 |
| 3 (final) | 1.2552 | 1.1456 |

Las curvas de loss muestran una tendencia de descenso estable sin overfitting aparente (validation loss sigue bajando en epoch 3).

## Hallazgo critico -- Degradacion del modelo fine-tuneado

### Sintoma observado

Al intentar evaluar un PDA completo con el modelo fine-tuneado, el pipeline que en baseline tarda ~5 minutos se extendio a mas de 30 minutos sin completar. Una prueba aislada revelo que el modelo entra en **loops de generacion** repetitivos:

```
{"estado": "NO CUMPLE", "mensaje": "[EXCEPCION]"}
{"estado": "CUMPLE", "mensaje": ""} JSON
{"estado": "NO CUMPLE", "mensaje": "[EXCEPCION]"}
{"estado": "CUMPLE", "mensaje": ""} JSON
... (repetido hasta agotar max_tokens)
```

El modelo genera patrones repetitivos de JSON mal formado en lugar de responder con un hallazgo estructurado.

### Diagnostico y causas probables

El comportamiento observado es consistente con una **degradacion de capacidad de razonamiento** producto de fine-tuning con condiciones sub-optimas. Las causas probables, en orden de impacto estimado:

1. **Dataset de entrenamiento demasiado pequeno.** 42 ejemplos de train son insuficientes para un modelo de 3 mil millones de parametros. Con 3 epochs, el modelo vio cada ejemplo 3 veces pero nunca lo suficiente para generalizar patrones robustos. La literatura sugiere minimo 200-500 ejemplos para fine-tuning de tareas estructuradas.

2. **Circularidad en la generacion de outputs.** Los outputs del dataset de entrenamiento fueron generados por el mismo Llama 3.2 3B baseline. Esto crea un **feedback loop degradante**: el fine-tuneado aprende a imitar (y amplificar) las limitaciones del baseline, especialmente sus fallas de formato JSON.

3. **Overfitting sobre patrones superficiales.** Con tan pocos datos, el modelo probablemente memorizo fragmentos de texto especificos en vez de la estructura logica de la evaluacion. Al encontrar entradas nuevas, recurre a patrones memorizados sin sentido semantico.

4. **Temperature 0.1 en inferencia.** A baja temperatura, los modelos degradados tienden a caer en loops con mayor probabilidad porque siempre eligen el token mas probable, que en este caso lleva a bucles.

### Validacion del diagnostico

La prueba aislada con una seccion simple confirma el problema:

- Entrada: "Este curso desarrolla pensamiento critico y trabajo en equipo."
- Regla: "El curso debe declarar competencia 1h: Pensamiento critico"
- Respuesta esperada: `{"estado": "CUMPLE", "evidencia": "menciona pensamiento critico"}`
- Respuesta real: patron repetitivo `{"estado": "X", "mensaje": "..."}` x N

El baseline con el mismo prompt responde correctamente en 2.4 segundos.

## Decision tecnica

Dado el hallazgo, se decide usar el **modelo baseline** (Llama 3.2 3B sin fine-tuning) como modelo de produccion del agente. El modelo fine-tuneado se conserva en `models/unibabot-pda.gguf` como artefacto del experimento pero no se utiliza en el pipeline.

Esta decision:

- Preserva la calidad de los reportes (baseline produce JSON valido consistentemente)
- Mantiene tiempos razonables de evaluacion (~5 min por PDA)
- No sacrifica la componente RAG, que sigue aportando los lineamientos relevantes

## Limitaciones identificadas

1. **Tamano del corpus de PDAs.** Solo se pudo trabajar con 4 PDAs reales. Un corpus mas grande permitiria dataset de entrenamiento mas robusto y evaluacion mas estadisticamente significativa.

2. **Fine-tuning requiere outputs de alta calidad.** Para un fine-tuning efectivo se necesitarian outputs generados por un modelo mas capaz (GPT-4, Claude) o escritos manualmente por evaluadores expertos.

3. **Segmentacion de PDF dependiente del formato.** El parser detecta encabezados via heuristicas visuales (fuente, bold) y una lista de secciones conocidas. PDAs con formato atipico podrian no segmentarse correctamente.

4. **Modelo pequeno (3B parametros).** Para tareas con multiples reglas y contexto largo, modelos mas grandes (7B, 13B) probablemente darian mejores resultados, pero requeririan mas recursos computacionales.

## Trabajo futuro

- **Ampliar dataset de entrenamiento** a 200-500 ejemplos con outputs escritos manualmente o generados por Claude/GPT-4
- **Experimentar con menos epochs** (1-2) y learning rate mas bajo (1e-4) para evitar degradacion
- **Evaluar modelos base alternativos:** Mistral 7B, Gemma 2B, modelos especificos para espanol
- **Agregar validacion cruzada entre secciones:** verificar coherencia entre "competencias declaradas" y "resultados de aprendizaje"
- **Interfaz web** para que las oficinas academicas suban PDAs y visualicen reportes
- **Integracion con el sistema institucional** para automatizar la recoleccion de PDAs por semestre

## Conclusiones

El proyecto demuestra que es viable construir un agente inteligente para verificacion de cumplimiento de PDAs combinando RAG con un modelo de lenguaje pequeno corriendo localmente. El pipeline completo funciona end-to-end y genera reportes estructurados en formato JSON que las oficinas academicas pueden consumir.

El experimento de fine-tuning con QLoRA no alcanzo los resultados esperados debido al tamano limitado del dataset y la calidad de los outputs sinteticos. Este hallazgo constituye una leccion importante sobre las precondiciones necesarias para que el fine-tuning mejore (en lugar de degradar) un modelo base. El sistema final opera con el modelo baseline, que produce resultados consistentes y utilizables.

La contribucion principal del proyecto no esta solo en el pipeline funcional, sino en la documentacion del proceso completo: desde la codificacion de 179 reglas institucionales en una base vectorial, hasta la identificacion de las condiciones bajo las cuales el fine-tuning falla. Ambos aspectos son valiosos para futuros trabajos en automatizacion de procesos academicos con NLP.

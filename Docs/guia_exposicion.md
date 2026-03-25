# Guia de Exposicion - UnibaBot PDA

Este documento explica que decir en cada diapositiva y que significa cada parte del informe IEEE. Leelo completo antes de la exposicion para que ambos dominen el contenido.

---

## Conceptos clave que hay que entender antes de todo

Antes de entrar en las diapositivas, hay varios conceptos que se repiten en todo el proyecto. Si los entienden bien, el resto fluye solo.

### LLM (Large Language Model)
Un modelo de lenguaje grande. Es un programa de inteligencia artificial entrenado con cantidades enormes de texto (libros, articulos, paginas web) para que "entienda" y genere texto. Ejemplos: ChatGPT, Claude, LLaMA. La idea es que aprendio patrones del lenguaje y puede responder preguntas, clasificar texto, extraer informacion, etc.

### Transformer
Es la arquitectura (la estructura interna) que usan todos los LLMs modernos. Fue inventada en 2017 por Google. Su innovacion clave es el "mecanismo de atencion": en vez de leer el texto palabra por palabra de izquierda a derecha (como hacian los modelos anteriores), el Transformer mira TODAS las palabras al mismo tiempo y decide cuales son importantes para entender cada una. Esto lo hace mucho mas rapido y preciso para capturar relaciones entre palabras que estan lejos en el texto.

### RAG (Retrieval-Augmented Generation)
"Generacion aumentada por recuperacion". Es una tecnica que combina dos cosas:
1. Un buscador que busca informacion relevante en una base de datos
2. Un LLM que usa esa informacion para generar una respuesta

Analogia: imaginen que les piden evaluar un PDA. Ustedes NO se saben de memoria todas las reglas. Entonces primero BUSCAN las reglas relevantes (eso es el "retrieval"), luego las LEEN junto con el PDA y dan su evaluacion (eso es la "generation"). RAG hace exactamente eso pero automatizado.

### Fine-tuning
Es el proceso de tomar un LLM que ya fue entrenado de forma general y entrenarlo un poco mas con datos especificos de tu dominio para que sea mejor en una tarea particular. Analogia: un medico general (modelo pre-entrenado) que hace una especializacion en cardiologia (fine-tuning) para ser mejor en diagnosticos del corazon.

### LoRA (Low-Rank Adaptation)
Es una tecnica para hacer fine-tuning de manera eficiente. En vez de modificar TODOS los parametros del modelo (que son miles de millones y requiere hardware caro), LoRA solo agrega unas matrices pequenas adicionales que se entrenan. El resultado es casi igual de bueno pero usando mucho menos memoria y poder de computo.

### QLoRA
Es LoRA + compresion del modelo. Comprime el modelo original a 4 bits (normalmente usa 16 o 32 bits), lo que reduce la memoria necesaria dramaticamente. Permite hacer fine-tuning de modelos grandes en GPUs gratuitas como las de Google Colab.

### Vector Database (Base de datos vectorial)
Es una base de datos que almacena texto convertido en vectores (listas de numeros). Cada texto se convierte en un vector que representa su "significado". Cuando buscas algo, se compara el significado de tu consulta con los significados almacenados y se devuelven los mas similares. Es la base del componente de "retrieval" en RAG.

### ABET
Es una organizacion internacional que acredita programas de ingenieria. Define 7 "student outcomes" (O1-O7) que son las habilidades que todo egresado de ingenieria debe tener. La universidad los usa como parte de su marco de evaluacion.

### PDA (Plan de Desarrollo Academico)
Es el documento que cada profesor llena cada semestre para cada curso. Incluye los resultados de aprendizaje, metodos de evaluacion, cronograma, y acciones de mejora. Debe cumplir con las competencias asignadas a ese curso segun el mapeo institucional.

---

## Diapositiva 1: Titulo (30 segundos)

**Que decir:**

> "Buenos dias/tardes. Somos Kevin Beltran y Jeryleefth Lasso, estudiantes de Ingenieria de Sistemas. Hoy vamos a presentar UnibaBot PDA, un agente inteligente que automatiza la verificacion de cumplimiento de los Planes de Desarrollo Academico en la universidad."

No se extiendan aqui. Es solo la presentacion. Pasen rapido a la siguiente.

---

## Diapositiva 2: El Problema (1-2 minutos)

**Que decir:**

> "Cada semestre, las oficinas de los programas academicos deben revisar manualmente mas de 20 PDAs para verificar que cumplan con los lineamientos institucionales. Esto incluye verificar que cada PDA cubra las competencias ABET, las competencias especificas del programa, las genericas, los componentes de Saber Pro y las dimensiones institucionales que le corresponden a ese curso."
>
> "Este proceso tiene tres problemas principales:"
>
> "Primero, es LENTO. La revision manual de todos los PDAs toma varios dias cada semestre."
>
> "Segundo, es INCONSISTENTE. Diferentes revisores pueden aplicar los criterios de forma distinta. Un revisor puede marcar algo como no cumplido que otro revisor si aceptaria."
>
> "Tercero, es PROPENSO A ERRORES. Con tantos documentos y tantas reglas que cruzar, es facil que se pasen por alto violaciones."

**Dato extra por si preguntan:** Los PDAs son documentos en PDF con secciones estandarizadas. Las reglas estan codificadas en archivos JSON con mapeos por curso (por ejemplo, el curso 22A14 "Agentes Inteligentes" debe cubrir competencias C1 y C2, ABET nada en particular, genericas 1c y 1h, Saber Pro SP5, y dimension D4).

---

## Diapositiva 3: Estado del Arte - LLMs (1-2 minutos)

**Que decir:**

> "Para entender nuestra solucion, primero revisemos las tecnologias en las que se basa. Todo empieza con el Transformer, una arquitectura de inteligencia artificial propuesta por Vaswani y colaboradores en 2017. La innovacion clave del Transformer es el mecanismo de atencion: permite que el modelo analice todas las palabras de un texto simultaneamente en vez de una por una, lo que lo hace mucho mas eficiente y preciso."
>
> "A partir del Transformer surgieron dos familias de modelos. La generativa, con GPT-1 y GPT-2 de OpenAI, que mostro que un modelo pre-entrenado con mucho texto puede realizar tareas sin entrenamiento adicional, lo que se conoce como zero-shot learning. Y la de comprension, con BERT de Google, que lee el texto en ambas direcciones y es especialmente bueno para tareas de clasificacion y extraccion de informacion, que es lo que nosotros necesitamos."
>
> "Lo que hizo esto accesible para proyectos academicos como el nuestro fue la aparicion de modelos open-source. LLaMA de Meta y Mistral son modelos que se pueden usar gratuitamente y correr en GPUs de Google Colab, que es el hardware que tenemos disponible."

**Por si preguntan sobre zero-shot:** Significa que el modelo puede hacer una tarea que nunca vio durante su entrenamiento. Por ejemplo, si le pides que clasifique un texto como positivo o negativo sin haberle mostrado ejemplos de eso, y lo hace bien, eso es zero-shot.

**Por si preguntan sobre la diferencia GPT vs BERT:** GPT genera texto (escribe), BERT entiende texto (clasifica, extrae). Para nuestro proyecto necesitamos ambas cosas: entender el PDA Y generar el reporte de cumplimiento.

---

## Diapositiva 4: Estado del Arte - RAG (1-2 minutos)

**Que decir:**

> "La segunda tecnologia clave es RAG, o Generacion Aumentada por Recuperacion, propuesta por Lewis y colaboradores en 2020. La idea es simple pero poderosa: en vez de que el modelo dependa solo de lo que memorizo durante su entrenamiento, le damos acceso a una base de conocimiento externa. Cuando recibe una consulta, primero busca la informacion relevante en esa base y luego genera su respuesta usando tanto la consulta como la informacion recuperada."
>
> "De la literatura identificamos tres hallazgos importantes para nuestro proyecto:"
>
> "Primero, Fan y colaboradores demostraron que la calidad de la recuperacion es el factor mas critico. Si el sistema no encuentra el documento correcto, la respuesta sera incorrecta sin importar que tan bueno sea el modelo."
>
> "Segundo, Jimeno Yepes y colaboradores mostraron que la forma en que se fragmentan los documentos para almacenarlos importa mucho. Respetar la estructura del documento mejora la precision entre 15 y 20 por ciento."
>
> "Tercero, Sun y colaboradores construyeron un sistema de verificacion de cumplimiento normativo basado en RAG y demostraron que supera a los modelos que trabajan solo con su conocimiento interno. Esto valida directamente nuestro enfoque."

**Por si preguntan como funciona la busqueda:** Cada texto se convierte en un vector (una lista de numeros que representa su significado). Cuando buscamos, convertimos la consulta en vector y buscamos los vectores mas "cercanos" en la base de datos. Cercania = similitud de significado.

---

## Diapositiva 5: Estado del Arte - Fine-Tuning (1-2 minutos)

**Que decir:**

> "La tercera pieza es el fine-tuning, que es tomar un modelo ya entrenado y especializarlo en nuestra tarea. El problema es que hacer fine-tuning completo de un modelo de 7 mil millones de parametros requiere mas de 80 gigas de memoria de GPU, algo que no tenemos."
>
> "LoRA, propuesto por Hu y colaboradores en 2022, resuelve esto. En vez de modificar todos los parametros, agrega unas matrices pequenas adicionales y solo entrena esas. El resultado es que entrenas menos del 1% de los parametros con resultados casi identicos al fine-tuning completo."
>
> "QLoRA va un paso mas alla: comprime el modelo a 4 bits antes de aplicar LoRA, reduciendo la memoria a solo 6 gigas. Esto es importante porque significa que podemos hacer fine-tuning en Google Colab gratis, que tiene GPUs T4 con 16 gigas."
>
> "Para crear los datos de entrenamiento, la literatura muestra que se puede usar la tecnica de Self-Instruct: usar un modelo mas capaz para generar ejemplos sinteticos de entrenamiento. Alpaca de Stanford demostro que esto funciona bien con un costo menor a 600 dolares."

**Por si preguntan que son los parametros:** Son los "pesos" internos del modelo, los numeros que determinan como procesa la informacion. Un modelo de 7B tiene 7 mil millones de estos numeros. Cambiarlos todos requiere mucha memoria; LoRA solo cambia unos pocos miles de forma inteligente.

---

## Diapositiva 6: Estado del Arte - Compliance Checking (1 minuto)

**Que decir:**

> "Finalmente, revisamos trabajos existentes en verificacion automatica de cumplimiento. Encontramos sistemas para GDPR, contratos de construccion, y textos legales. Todos confirman que combinar conocimiento estructurado con LLMs produce mejores resultados que usar cualquiera de los dos por separado."
>
> "Sin embargo, identificamos un vacio importante en la literatura: NO existen sistemas disenados para verificacion de cumplimiento academico, y menos aun en el contexto de programas acreditados por ABET con documentos en espanol. Nuestro proyecto aborda directamente ese vacio."

Este slide es corto. El punto principal es el GAP, eso es lo que justifica que el proyecto vale la pena.

---

## Diapositiva 7: Objetivo General (1 minuto)

**Que decir:**

> "Nuestro objetivo general es disenar e implementar un agente inteligente que verifique automaticamente el cumplimiento de los PDAs contra el marco completo de competencias de la universidad."
>
> "Este marco tiene cinco componentes que el agente debe verificar para cada curso:"
>
> "Los 7 student outcomes de ABET, como la capacidad de resolver problemas complejos o comunicarse efectivamente. Las 3 competencias especificas del programa de Sistemas. Las 12 competencias genericas institucionales. Los 5 componentes de Saber Pro. Y las 6 dimensiones institucionales."
>
> "Cada curso tiene un mapeo especifico que dice cuales de estos elementos debe cubrir. El agente genera un reporte indicando que se cumple, que no, y que correcciones se necesitan."

**Por si preguntan un ejemplo concreto:** "El curso Agentes Inteligentes, codigo 22A14, debe cubrir competencias especificas C1 y C2, genericas 1c y 1h, Saber Pro SP5, y dimension D4. Si el PDA de ese curso no menciona nada sobre comunicacion en segunda lengua (que es la competencia 1c), el agente lo detectaria y generaria un comentario indicando que falta."

---

## Diapositiva 8: Preguntas de Investigacion (1 minuto)

**Que decir:**

> "Planteamos tres preguntas de investigacion que guian el desarrollo:"
>
> "RQ1: Que tan preciso es nuestro sistema comparado con un revisor humano experto? Esto lo mediremos comparando las evaluaciones del agente contra evaluaciones hechas por personas."
>
> "RQ2: Que tanto aporta cada componente? Compararemos el sistema completo contra versiones simplificadas: solo lookup estructurado, lookup mas RAG sin fine-tuning, y el sistema completo. Asi podemos ver si el fine-tuning realmente agrega valor o si RAG solo es suficiente."
>
> "RQ3: Como afecta el fine-tuning la capacidad del modelo de entender contenido academico en espanol? Los modelos base fueron entrenados principalmente en ingles, entonces queremos ver si el fine-tuning mejora su desempeno con nuestros documentos."

---

## Diapositiva 9: Arquitectura del Sistema (2 minutos)

**Que decir:**

> "Esta es la arquitectura de nuestro sistema, dividida en 4 etapas."
>
> "Etapa 1, Ingesta del Documento: El sistema recibe un PDA en PDF, extrae el texto, y lo segmenta en secciones. Cada PDA tiene secciones identificables: resultados de aprendizaje, metodos de evaluacion, cronograma, y acciones de mejora."
>
> "Etapa 2, Busqueda de Requisitos: Aqui el sistema identifica el codigo del curso, por ejemplo 22A14 para Agentes Inteligentes, y hace un lookup directo en nuestros archivos JSON para obtener exactamente que competencias, indicadores ABET, y demas elementos debe cubrir ese curso. Esta etapa es determinista, no usa IA, es una consulta directa a los datos estructurados."
>
> "Etapa 3, Analisis con RAG y LLM: Esta es la etapa inteligente. Para cada requisito encontrado en la etapa anterior, el sistema busca en la base de datos vectorial la descripcion completa de esa competencia o indicador ABET. Por ejemplo, para el indicador ABET 1.1, recupera 'Identificar los problemas y las teorias aplicables'. Luego le pasa al LLM tanto la seccion del PDA como la descripcion del requisito, y el modelo evalua si la seccion realmente cubre lo que pide el requisito."
>
> "Etapa 4, Generacion del Reporte: Agrega todas las evaluaciones individuales en un reporte final que lista las secciones que cumplen, las que no cumplen con el comentario especifico de que falta, y cualquier contenido que no corresponda al formato esperado."

**Por si preguntan por que separar etapa 2 y 3:** La etapa 2 es un lookup exacto -- sabemos con certeza que competencias necesita cada curso porque estan en un JSON. La etapa 3 es semantica -- necesitamos entender si el TEXTO LIBRE del PDA realmente cubre esas competencias. Son dos problemas distintos: uno de datos estructurados, otro de comprension de lenguaje natural.

**Por si preguntan por que no usar solo el LLM sin RAG:** Porque el LLM no "conoce" las definiciones especificas de las competencias de la Universidad de Ibague. Si le preguntas sin darle contexto, inventaria o daria respuestas genericas. RAG le da el contexto correcto para evaluar.

---

## Diapositiva 10: Cierre (30 segundos)

**Que decir:**

> "En resumen, UnibaBot PDA busca transformar un proceso manual que toma dias en un flujo automatizado que toma minutos, usando RAG para acceder dinamicamente a los lineamientos institucionales y un LLM fine-tuneado para evaluar el cumplimiento. Con esto no solo se gana velocidad sino tambien consistencia, algo que la revision humana no puede garantizar."
>
> "Gracias. Estamos abiertos a preguntas."

---

## Preguntas frecuentes que podrian hacerles

### "Por que no usar solo ChatGPT/Claude directamente?"
Porque esos modelos no conocen las reglas especificas de la universidad. No saben que el curso 22A14 debe cubrir C1, C2, 1c, 1h, SP5 y D4. RAG le da ese conocimiento al modelo en tiempo real. Ademas, depender de una API externa tiene costos y problemas de privacidad con datos institucionales.

### "Por que RAG y no simplemente meter todas las reglas en el prompt?"
Porque hay un limite de contexto en los modelos. Si intentamos meter todas las competencias, todos los indicadores ABET, todos los mapeos de todos los cursos en un solo prompt, podriamos exceder el limite o diluir la atencion del modelo. RAG recupera SOLO lo relevante para el curso que se esta evaluando.

### "Que pasa si las reglas cambian el proximo semestre?"
Esa es precisamente una ventaja de RAG. Como las reglas estan en archivos JSON y en la base vectorial, solo hay que actualizar esos archivos. No hay que re-entrenar el modelo completo.

### "Que tan preciso esperan que sea?"
Eso es lo que mediremos con la RQ1. La meta es que sea al menos comparable a un revisor humano, pero con la ventaja de ser 100% consistente (siempre aplica los mismos criterios).

### "Que modelo base van a usar?"
Planeamos usar Llama 3.2 3B como primera opcion porque corre en Google Colab T4 gratis. Si los resultados no son suficientes, podriamos probar con Mistral 7B usando QLoRA.

### "Como van a conseguir datos de entrenamiento para el fine-tuning?"
Usando la tecnica de Self-Instruct: tomamos secciones reales de PDAs, las combinamos con los requisitos del JSON, y usamos un modelo mas capaz (como GPT-4o-mini) para generar pares de instruccion-respuesta que sirvan como datos de entrenamiento. Es la misma tecnica que uso Stanford con Alpaca.

### "Que framework o librerias van a usar?"
Para RAG: LangChain o LlamaIndex con una base vectorial como ChromaDB o FAISS. Para fine-tuning: Hugging Face Transformers + PEFT + TRL con Unsloth para optimizar velocidad en Colab. Para extraccion de PDF: PyMuPDF o pdfplumber.

---

## Explicacion del informe IEEE seccion por seccion

### Abstract (Resumen)
Es el resumen de todo el articulo en un parrafo. Presenta el problema (revision manual de PDAs), la solucion (RAG + fine-tuning), y el alcance del articulo (estado del arte + objetivos + preguntas de investigacion). Cualquier persona deberia poder leer solo el abstract y entender de que trata el proyecto.

### Section I - Introduction
Expande el problema con mas detalle. Explica que son los PDAs, que contienen, contra que se evaluan (el marco de competencias ABET + institucionales), y por que la revision manual es problematica. Luego presenta la solucion propuesta y anticipa la estructura del resto del articulo.

Lo mas importante de esta seccion es que establece que el marco normativo no es un solo documento de texto libre, sino un conjunto de datos estructurados (mapeos curso-competencia) combinado con descripciones textuales (que significa cada competencia). Esto justifica la arquitectura hibrida lookup + RAG.

### Section II - State of the Art
Es la revision de la literatura existente, dividida en cuatro subsecciones:

**II-A: Large Language Models** -- Explica la evolucion desde el Transformer hasta los modelos open-source actuales. El punto clave es que ya existen modelos capaces y accesibles (LLaMA, Mistral) que podemos usar con recursos limitados.

**II-B: RAG** -- Explica que es RAG, por que es necesario (el modelo no conoce nuestras reglas), y que aprendimos de la literatura: que la calidad de la busqueda es critica, que como fragmentamos los documentos importa, y que RAG ya se probo exitosamente para tareas de cumplimiento normativo.

**II-C: Fine-Tuning** -- Explica LoRA y QLoRA (como hacer fine-tuning barato), instruction tuning (como formatear los datos de entrenamiento), y Self-Instruct (como generar datos sinteticos). Todo esto es el camino para especializar el modelo en nuestra tarea con los recursos que tenemos.

**II-D: Compliance Checking** -- Muestra que la verificacion automatizada ya se ha hecho en otros dominios (GDPR, construccion, legal) pero NO en el ambito academico ni en espanol. Este es el "gap" que justifica nuestro proyecto.

### Section III - Research Goals and Questions
Define que queremos lograr (objetivo general + especificos) y que preguntas queremos responder (RQ1-RQ3). Los objetivos especificos son los pasos concretos: construir el RAG, construir el dataset y hacer fine-tuning, integrar todo, y evaluar.

### Section IV - Proposed System Architecture
Describe el pipeline de 4 etapas que explique en la diapositiva 9. Lo clave aqui es la separacion entre lookup estructurado (etapa 2, determinista) y analisis semantico (etapa 3, con IA). No todo el problema requiere IA; la parte de "que competencias necesita este curso" es una consulta directa a un JSON.

### Section V - Evaluation Methodology
Explica como vamos a medir si el sistema funciona. Tres dimensiones: correctness (precision vs revisores humanos), granularity (calidad de los comentarios generados), y consistency (que siempre de la misma respuesta para el mismo PDA). Tambien describe un estudio de ablacion: comparar el sistema completo contra versiones parciales para aislar la contribucion de cada componente.

### Section VI - Conclusion
Cierra resumiendo la propuesta y lo que se establecio en el articulo. Resalta el gap en la literatura y como nuestro trabajo lo aborda.

---


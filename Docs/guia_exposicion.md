# Guia de Exposicion - UnibaBot PDA

Este documento tiene todo lo que necesitan para la exposicion. Cada diapositiva tiene tres bloques:
1. **En ingles**: lo que deben decir tal cual (pueden parafrasear, pero la idea es esa)
2. **Traduccion**: para que entiendan exactamente que estan diciendo
3. **Explicacion y preguntas**: contexto adicional y respuestas a posibles preguntas de la profesora

Lealo completo antes de la exposicion. Ambos deben dominar todo el contenido aunque solo expongan su parte.

---

## Division de la exposicion

### Persona 1 (~4-5 min): Datos estructurados + State of Art (LLMs y RAG)
- Diapositiva 1: Titulo
- Diapositiva 2: Estructura de datos (JSON)
- Diapositiva 3: State of Art - LLMs
- Diapositiva 4: State of Art - RAG

### Persona 2 (~4-5 min): Fine-tuning + Arquitectura + Preguntas
- Diapositiva 5: State of Art - Fine-tuning
- Diapositiva 6: State of Art - Compliance Checking
- Diapositiva 7: Objetivo General
- Diapositiva 8: Preguntas de Investigacion
- Diapositiva 9: Arquitectura del Sistema
- Diapositiva 10: Cierre

**Transicion de Persona 1 a Persona 2:**
> "So that covers the knowledge base and the two main technologies we build on. Now [nombre] will explain how we adapt the model to our task and the system architecture we propose."

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

## PERSONA 1

---

## Diapositiva 1: Titulo (30 segundos)

### En ingles:

> "Good morning/afternoon. We are Kevin Beltran and Jeryleefth Lasso, Systems Engineering students at the University of Ibague. Today we are going to present UnibaBot PDA, an intelligent agent that automates the compliance verification of Academic Development Plans."

### Traduccion:

> "Buenos dias/tardes. Somos Kevin Beltran y Jeryleefth Lasso, estudiantes de Ingenieria de Sistemas de la Universidad de Ibague. Hoy vamos a presentar UnibaBot PDA, un agente inteligente que automatiza la verificacion de cumplimiento de los Planes de Desarrollo Academico."

### Explicacion:

No se extiendan aqui. Es solo la presentacion. Pasen rapido a la siguiente diapositiva.

---

## Diapositiva 2: Estructura de Datos - JSON (2 minutos)

### En ingles:

> "The first step in our project was to encode the entire institutional regulatory framework into structured JSON files. We have five files that form our knowledge base."
>
> "First, `cursos.json`: it contains all the courses in the program with their code and semester. For example, 22A14 is Intelligent Agents, semester 8."
>
> "Second, `competenciascursos.json`: this is the key file. For each course code, it maps exactly what that course must cover across five categories: specific competencies like C1 and C2, generic competencies like 1b and 1h, ABET performance indicators like 1.1 and 6.3, Saber Pro components like SP5, and institutional dimensions like D4. For example, the course 22A05 must cover C1 and C2, generic competencies 1b and 1e, Saber Pro SP5, and ABET indicators 1.1, 1.3, 6.1, and 6.3."
>
> "Third, `competencias.json`: it contains the textual definitions of each competency. For example, C1 means 'Analyzes and models phenomena to solve information management problems', generic 1h is 'Critical thinking', SP5 is 'English proficiency', and so on."
>
> "Fourth and fifth, `abet.json` and `abet_es.json`: the seven ABET student outcomes with their performance indicators, in both English and Spanish. For example, Outcome 1 is 'Identify, formulate, and solve complex engineering problems', and its indicator 1.1 is 'Analyze a problem by identifying the context, variables, and applicable principles'."
>
> "This structure is what the agent queries deterministically: given a course code, it knows exactly which requirements to look for. What it cannot do with these files alone is evaluate whether the free text of a PDA actually covers those competencies. That is where the techniques we will discuss next come in."

### Traduccion:

> "El primer paso de nuestro proyecto fue codificar todo el marco normativo institucional en archivos JSON estructurados. Tenemos cinco archivos que forman nuestra base de conocimiento."
>
> "Primero, `cursos.json`: contiene todos los cursos del programa con su codigo y semestre. Por ejemplo, 22A14 es Agentes Inteligentes, semestre 8."
>
> "Segundo, `competenciascursos.json`: este es el archivo clave. Para cada codigo de curso, mapea exactamente que debe cubrir en cinco categorias: competencias especificas como C1 y C2, genericas como 1b y 1h, indicadores ABET como 1.1 y 6.3, componentes de Saber Pro como SP5, y dimensiones institucionales como D4. Por ejemplo, el curso 22A05 debe cubrir C1 y C2, genericas 1b y 1e, Saber Pro SP5, e indicadores ABET 1.1, 1.3, 6.1 y 6.3."
>
> "Tercero, `competencias.json`: contiene las definiciones textuales de cada competencia. Por ejemplo, C1 significa 'Analiza y modela fenomenos para resolver problemas de gestion de informacion', la generica 1h es 'Pensamiento critico', SP5 es 'Ingles', etc."
>
> "Cuarto y quinto, `abet.json` y `abet_es.json`: los siete student outcomes de ABET con sus indicadores de desempeno, en ingles y espanol. Por ejemplo, el Outcome 1 es 'Identificar, formular y resolver problemas complejos de ingenieria', y su indicador 1.1 es 'Analiza un problema identificando contexto, variables y principios aplicables'."
>
> "Esta estructura es lo que el agente consulta de forma determinista: dado un codigo de curso, sabe exactamente que requisitos buscar. Lo que NO puede hacer solo con estos archivos es evaluar si el texto libre del PDA realmente cubre esas competencias. Para eso estan las tecnicas que vamos a ver ahora."

### Explicacion:

Lo importante de esta diapositiva es que el publico entienda que el marco normativo NO es un solo documento de texto, sino un conjunto de datos relacionados entre si. Hay un mapeo por curso que dice "este curso debe cubrir estas competencias", y luego hay definiciones de que significa cada competencia. Son dos tipos de datos distintos: uno estructurado (el mapeo) y otro textual (las descripciones). Esa separacion es la que justifica despues tener dos etapas diferentes en la arquitectura.

**Posibles preguntas:**

**"Who created those JSON files? Where does the data come from?"**
> "We manually encoded the data from the official institutional documents. The competency mappings come from the program's curriculum matrix, and the ABET indicators come from the official ABET documentation. We structured them in JSON because it makes them machine-readable and easy to update when the curriculum changes."

Traduccion: "Nosotros codificamos manualmente los datos a partir de los documentos oficiales institucionales. Los mapeos de competencias vienen de la matriz curricular del programa, y los indicadores ABET vienen de la documentacion oficial de ABET. Los estructuramos en JSON porque eso los hace legibles por maquina y faciles de actualizar cuando el curriculo cambie."

**"Why JSON and not a database or a spreadsheet?"**
> "JSON is lightweight, human-readable, and does not require a database server. Since the dataset is relatively small -- around 20 courses with their mappings -- JSON is the simplest solution that works. If the project scales to cover multiple programs, migrating to a database would be straightforward because the structure is already well-defined."

Traduccion: "JSON es liviano, legible por humanos y no requiere un servidor de base de datos. Como el dataset es relativamente pequeno -- unos 20 cursos con sus mapeos -- JSON es la solucion mas simple que funciona. Si el proyecto escala para cubrir multiples programas, migrar a una base de datos seria sencillo porque la estructura ya esta bien definida."

**"Why do you have ABET in both English and Spanish?"**
> "The official ABET definitions are in English, but the PDAs are written in Spanish. We need both versions: the English one as the authoritative reference, and the Spanish one so the system can compare it semantically against the Spanish text in the PDAs."

Traduccion: "Las definiciones oficiales de ABET son en ingles, pero los PDAs estan escritos en espanol. Necesitamos ambas versiones: la inglesa como referencia oficial, y la espanola para que el sistema pueda compararla semanticamente contra el texto en espanol de los PDAs."

---

## Diapositiva 3: Estado del Arte - LLMs (1.5 minutos)

### En ingles:

> "To understand our solution, let us first review the technologies it is built on. Everything starts with the Transformer, an architecture proposed by Vaswani and colleagues in 2017. Its key innovation is the attention mechanism: instead of reading text word by word from left to right, the Transformer looks at all words at the same time and decides which ones are important for understanding each one. This makes it much faster and more accurate."
>
> "From the Transformer, two families of models emerged. The generative family, with GPT-1 and GPT-2 from OpenAI, showed that a model pre-trained on a large amount of text can perform tasks without additional training -- what is known as zero-shot learning. The understanding family, with BERT from Google, reads text in both directions and is especially good at classification and information extraction tasks, which is what we need."
>
> "What made this accessible for academic projects like ours was the release of open-source models. LLaMA from Meta and Mistral are models that can be used for free and run on Google Colab GPUs, which is the hardware we have available."

### Traduccion:

> "Para entender nuestra solucion, primero revisemos las tecnologias en las que se basa. Todo empieza con el Transformer, una arquitectura propuesta por Vaswani y colaboradores en 2017. Su innovacion clave es el mecanismo de atencion: en vez de leer el texto palabra por palabra de izquierda a derecha, el Transformer mira todas las palabras al mismo tiempo y decide cuales son importantes para entender cada una. Esto lo hace mucho mas rapido y preciso."
>
> "A partir del Transformer surgieron dos familias de modelos. La generativa, con GPT-1 y GPT-2 de OpenAI, mostro que un modelo pre-entrenado con mucho texto puede realizar tareas sin entrenamiento adicional, lo que se conoce como zero-shot learning. La de comprension, con BERT de Google, lee el texto en ambas direcciones y es especialmente bueno para clasificacion y extraccion de informacion, que es lo que necesitamos."
>
> "Lo que hizo esto accesible para proyectos academicos como el nuestro fue la aparicion de modelos open-source. LLaMA de Meta y Mistral son modelos que se pueden usar gratuitamente y correr en GPUs de Google Colab, que es el hardware que tenemos disponible."

### Explicacion:

El Transformer es la base de todo. Antes de el, los modelos leian el texto en secuencia (palabra por palabra), lo cual era lento y perdia relaciones entre palabras lejanas. El Transformer resolvio eso mirando todo el texto a la vez con su mecanismo de atencion.

GPT y BERT son dos "hijos" del Transformer. GPT genera texto (escribe), BERT entiende texto (clasifica, extrae). Para nuestro proyecto necesitamos ambas cosas: entender el PDA Y generar el reporte.

Los modelos open-source (LLaMA, Mistral) son la razon por la que este proyecto es viable. Sin ellos, tendriamos que pagar por APIs o tener hardware muy caro.

**Posibles preguntas:**

**"What is zero-shot learning?"**
> "It means the model can perform a task it was never explicitly trained on. For example, if you ask it to classify a text as positive or negative without ever showing it examples of that task, and it does it correctly, that is zero-shot. The model generalizes from its pre-training."

Traduccion: "Significa que el modelo puede hacer una tarea para la que nunca fue entrenado explicitamente. Por ejemplo, si le pides que clasifique un texto como positivo o negativo sin haberle mostrado ejemplos de esa tarea, y lo hace bien, eso es zero-shot. El modelo generaliza a partir de su pre-entrenamiento."

**"What is the difference between GPT and BERT?"**
> "GPT is generative -- it produces text. It reads from left to right and predicts what comes next. BERT is bidirectional -- it reads in both directions to understand meaning. GPT is better at writing, BERT is better at understanding. Modern models like LLaMA combine both capabilities."

Traduccion: "GPT es generativo -- produce texto. Lee de izquierda a derecha y predice lo que viene despues. BERT es bidireccional -- lee en ambas direcciones para entender significado. GPT es mejor escribiendo, BERT es mejor entendiendo. Los modelos modernos como LLaMA combinan ambas capacidades."

**"Why not just use ChatGPT directly?"**
> "Two reasons. First, ChatGPT does not know the specific rules of our university -- it does not know that course 22A14 must cover competencies C1, C2, 1c, 1h, SP5, and D4. Second, sending institutional documents to an external API raises privacy concerns and has ongoing costs. With a local model, we control the data."

Traduccion: "Dos razones. Primero, ChatGPT no conoce las reglas especificas de nuestra universidad -- no sabe que el curso 22A14 debe cubrir C1, C2, 1c, 1h, SP5 y D4. Segundo, enviar documentos institucionales a una API externa tiene problemas de privacidad y costos recurrentes. Con un modelo local, controlamos los datos."

---

## Diapositiva 4: Estado del Arte - RAG (1.5 minutos)

### En ingles:

> "The second key technology is RAG, or Retrieval-Augmented Generation, proposed by Lewis and colleagues in 2020. The idea is straightforward: instead of having the model rely only on what it memorized during training, we give it access to an external knowledge base. When it receives a query, it first retrieves the relevant information from that base and then generates its answer using both the query and the retrieved context."
>
> "From the literature, we identified three important findings for our project."
>
> "First, Fan and colleagues showed that retrieval quality is the most critical factor. If the system does not find the right document, the answer will be wrong no matter how good the model is."
>
> "Second, Jimeno Yepes and colleagues showed that how documents are split for storage matters a lot. Respecting the document's structure improves accuracy by 15 to 20 percent."
>
> "Third, Sun and colleagues built a regulatory compliance checking system based on RAG and showed that it outperforms models that work only with their internal knowledge. This directly validates our approach."

### Traduccion:

> "La segunda tecnologia clave es RAG, o Generacion Aumentada por Recuperacion, propuesta por Lewis y colaboradores en 2020. La idea es simple: en vez de que el modelo dependa solo de lo que memorizo durante su entrenamiento, le damos acceso a una base de conocimiento externa. Cuando recibe una consulta, primero busca la informacion relevante en esa base y luego genera su respuesta usando tanto la consulta como el contexto recuperado."
>
> "De la literatura identificamos tres hallazgos importantes para nuestro proyecto."
>
> "Primero, Fan y colaboradores mostraron que la calidad de la recuperacion es el factor mas critico. Si el sistema no encuentra el documento correcto, la respuesta sera incorrecta sin importar que tan bueno sea el modelo."
>
> "Segundo, Jimeno Yepes y colaboradores mostraron que la forma en que se fragmentan los documentos para almacenarlos importa mucho. Respetar la estructura del documento mejora la precision entre 15 y 20 por ciento."
>
> "Tercero, Sun y colaboradores construyeron un sistema de verificacion de cumplimiento normativo basado en RAG y mostraron que supera a los modelos que trabajan solo con su conocimiento interno. Esto valida directamente nuestro enfoque."

### Explicacion:

RAG es basicamente un "buscador inteligente" conectado a un LLM. El LLM por si solo no conoce las reglas de nuestra universidad, asi que antes de pedirle que evalue algo, le buscamos las reglas relevantes y se las pasamos junto con la consulta. Es como si antes de un examen te dejaran consultar tus apuntes -- vas a responder mucho mejor que de memoria.

Los tres hallazgos de la literatura nos dicen: (1) el buscador tiene que ser bueno, (2) hay que fragmentar bien los documentos, y (3) este enfoque ya funciono para tareas parecidas a la nuestra.

**Posibles preguntas:**

**"How does the vector search actually work?"**
> "Each text is converted into a vector -- a list of numbers that represents its meaning. We use a sentence-transformer model for this conversion. When we search, we convert the query into a vector too, and then find the vectors that are closest in the vector space. Closeness means similarity in meaning, not in exact words."

Traduccion: "Cada texto se convierte en un vector -- una lista de numeros que representa su significado. Usamos un modelo sentence-transformer para esta conversion. Cuando buscamos, convertimos la consulta en vector tambien, y luego encontramos los vectores mas cercanos en el espacio vectorial. Cercania significa similitud de significado, no de palabras exactas."

**"Why RAG and not just put all the rules in the prompt?"**
> "There is a context window limit in language models. If we tried to include all the competencies, all the ABET indicators, and all the course mappings in a single prompt, we would either exceed the limit or dilute the model's attention. RAG retrieves only what is relevant for the specific course being evaluated."

Traduccion: "Hay un limite de contexto en los modelos de lenguaje. Si intentamos meter todas las competencias, todos los indicadores ABET y todos los mapeos en un solo prompt, excederiamos el limite o diluiriamos la atencion del modelo. RAG recupera solo lo relevante para el curso que se esta evaluando."

**"What happens if the rules change next semester?"**
> "That is one of the main advantages of RAG. Since the rules are stored in JSON files and in the vector database, we just need to update those files. There is no need to retrain the model."

Traduccion: "Esa es una de las ventajas principales de RAG. Como las reglas estan en archivos JSON y en la base vectorial, solo hay que actualizar esos archivos. No hay que re-entrenar el modelo."

**Transicion a Persona 2:**
> "So that covers the knowledge base and the two main technologies we build on. Now [nombre] will explain how we adapt the model to our specific task and the overall system architecture."

---

## PERSONA 2

---

## Diapositiva 5: Estado del Arte - Fine-Tuning (1.5 minutos)

### En ingles:

> "The third key piece is fine-tuning -- taking a model that was already trained on general data and specializing it for our task. The challenge is that full fine-tuning of a model with 7 billion parameters requires more than 80 gigabytes of GPU memory, which we do not have."
>
> "LoRA, proposed by Hu and colleagues in 2022, solves this. Instead of modifying all the parameters, it adds small additional matrices and only trains those. The result is that less than 1 percent of the parameters are trained, with results nearly identical to full fine-tuning."
>
> "QLoRA goes one step further: it compresses the model to 4 bits before applying LoRA, reducing the memory requirement to just 6 gigabytes. This is important because it means we can fine-tune on Google Colab's free T4 GPUs, which have 16 gigabytes of memory."
>
> "For creating training data, the literature shows that the Self-Instruct technique works well: a more capable model generates synthetic training examples. Stanford's Alpaca demonstrated this approach effectively at a cost of less than 600 dollars."

### Traduccion:

> "La tercera pieza clave es el fine-tuning -- tomar un modelo ya entrenado con datos generales y especializarlo para nuestra tarea. El problema es que hacer fine-tuning completo de un modelo de 7 mil millones de parametros requiere mas de 80 gigas de memoria GPU, algo que no tenemos."
>
> "LoRA, propuesto por Hu y colaboradores en 2022, resuelve esto. En vez de modificar todos los parametros, agrega matrices pequenas adicionales y solo entrena esas. El resultado es que se entrena menos del 1% de los parametros con resultados casi identicos al fine-tuning completo."
>
> "QLoRA va un paso mas alla: comprime el modelo a 4 bits antes de aplicar LoRA, reduciendo la memoria necesaria a solo 6 gigas. Esto es importante porque significa que podemos hacer fine-tuning en Google Colab gratis, que tiene GPUs T4 con 16 gigas de memoria."
>
> "Para crear datos de entrenamiento, la literatura muestra que la tecnica Self-Instruct funciona bien: un modelo mas capaz genera ejemplos sinteticos de entrenamiento. Alpaca de Stanford demostro este enfoque con un costo menor a 600 dolares."

### Explicacion:

Fine-tuning es como una especializacion medica. El modelo base ya "sabe" lenguaje general, pero no sabe evaluar PDAs. Lo entrenamos un poco mas con ejemplos especificos de nuestra tarea para que se vuelva bueno en eso.

El problema es que entrenar modelos grandes requiere mucha memoria. LoRA resuelve esto siendo "inteligente" sobre que partes del modelo modificar: en vez de tocar los 7 mil millones de parametros, agrega unas matrices chiquitas (miles de parametros) que capturan lo nuevo que tiene que aprender. QLoRA ademas comprime el modelo para que use menos memoria.

Self-Instruct es una tecnica para generar datos de entrenamiento. Tomamos secciones reales de PDAs, las combinamos con requisitos del JSON, y usamos un modelo mas capaz para generar el analisis de cumplimiento que luego usamos como ejemplo de entrenamiento.

**Posibles preguntas:**

**"What are parameters?"**
> "Parameters are the internal weights of the model -- the numbers that determine how it processes information. A 7B model has 7 billion of these numbers. Changing all of them requires a lot of memory. LoRA only modifies a few thousand of them in a smart way."

Traduccion: "Los parametros son los pesos internos del modelo -- los numeros que determinan como procesa la informacion. Un modelo de 7B tiene 7 mil millones de estos numeros. Cambiarlos todos requiere mucha memoria. LoRA solo modifica unos pocos miles de forma inteligente."

**"What base model will you use?"**
> "We plan to use Llama 3.2 3B as our first option because it runs on Google Colab's free T4 GPU. If the results are not good enough, we could try Mistral 7B using QLoRA, which would also fit within our memory constraints."

Traduccion: "Planeamos usar Llama 3.2 3B como primera opcion porque corre en la GPU T4 gratuita de Google Colab. Si los resultados no son suficientes, podriamos probar con Mistral 7B usando QLoRA, que tambien cabria dentro de nuestras limitaciones de memoria."

**"How will you get training data for the fine-tuning?"**
> "Using the Self-Instruct technique: we take real PDA sections, combine them with the requirements from the JSON files, and use a more capable model like GPT-4o-mini to generate instruction-response pairs as training data. This is the same approach Stanford used with Alpaca."

Traduccion: "Usando la tecnica Self-Instruct: tomamos secciones reales de PDAs, las combinamos con los requisitos de los archivos JSON, y usamos un modelo mas capaz como GPT-4o-mini para generar pares instruccion-respuesta como datos de entrenamiento. Es el mismo enfoque que uso Stanford con Alpaca."

---

## Diapositiva 6: Estado del Arte - Compliance Checking (1 minuto)

### En ingles:

> "Finally, we reviewed existing work on automated compliance verification. There are systems for GDPR compliance, construction contracts, and legal texts. All of them confirm that combining structured knowledge with LLMs produces better results than using either one alone."
>
> "However, we identified an important gap in the literature: there are no systems designed for academic compliance verification, and even less so in the context of ABET-accredited programs with documents in Spanish. Our project directly addresses that gap."

### Traduccion:

> "Finalmente, revisamos trabajos existentes en verificacion automatica de cumplimiento. Hay sistemas para cumplimiento de GDPR, contratos de construccion y textos legales. Todos confirman que combinar conocimiento estructurado con LLMs produce mejores resultados que usar cualquiera de los dos por separado."
>
> "Sin embargo, identificamos un vacio importante en la literatura: no existen sistemas disenados para verificacion de cumplimiento academico, y menos aun en el contexto de programas acreditados por ABET con documentos en espanol. Nuestro proyecto aborda directamente ese vacio."

### Explicacion:

Esta diapositiva es corta a proposito. El punto principal es el GAP: nadie ha hecho esto para documentos academicos ni en espanol. Eso es lo que justifica que el proyecto vale la pena como investigacion. No es solo "hacer algo con IA" -- es resolver un problema que no tiene solucion existente en la literatura.

**Posibles preguntas:**

**"What are those GDPR and construction systems you mention?"**
> "For GDPR, there are systems that check whether privacy policies comply with the European data protection regulation. For construction, there are tools that verify whether project proposals follow building codes. Both use a combination of structured rules and language models, similar to what we propose."

Traduccion: "Para GDPR, hay sistemas que verifican si las politicas de privacidad cumplen con la regulacion europea de proteccion de datos. Para construccion, hay herramientas que verifican si las propuestas de proyecto cumplen con los codigos de construccion. Ambas usan una combinacion de reglas estructuradas y modelos de lenguaje, similar a lo que proponemos."

**"Are you sure there is nothing similar for academic documents?"**
> "From our literature review, we found no system that specifically addresses academic compliance verification against a structured competency framework like ABET. There are plagiarism checkers and automated grading tools, but those solve different problems. Our task is about verifying that a plan covers specific competencies -- that is a compliance checking task, not a text quality task."

Traduccion: "Segun nuestra revision de literatura, no encontramos ningun sistema que aborde especificamente la verificacion de cumplimiento academico contra un marco de competencias estructurado como ABET. Hay detectores de plagio y herramientas de calificacion automatica, pero esos resuelven problemas diferentes. Nuestra tarea es verificar que un plan cubra competencias especificas -- eso es verificacion de cumplimiento, no evaluacion de calidad de texto."

---

## Diapositiva 7: Objetivo General (30 segundos)

### En ingles:

> "Our general objective is to design and implement an intelligent agent that automatically verifies PDA compliance against the university's complete competency framework."
>
> "This framework has five components the agent must check for each course: the 7 ABET student outcomes, the 3 program-specific competencies, the 12 generic institutional competencies, the 5 Saber Pro components, and the 6 institutional dimensions. Each course has a specific mapping that tells which of these elements it must cover. The agent generates a report indicating what complies, what does not, and what corrections are needed."

### Traduccion:

> "Nuestro objetivo general es disenar e implementar un agente inteligente que verifique automaticamente el cumplimiento de los PDAs contra el marco completo de competencias de la universidad."
>
> "Este marco tiene cinco componentes que el agente debe verificar para cada curso: los 7 student outcomes de ABET, las 3 competencias especificas del programa, las 12 competencias genericas institucionales, los 5 componentes de Saber Pro y las 6 dimensiones institucionales. Cada curso tiene un mapeo especifico que dice cuales de estos elementos debe cubrir. El agente genera un reporte indicando que cumple, que no cumple, y que correcciones se necesitan."

### Explicacion:

Aqui no se extiendan. El objetivo ya fue implicitamente explicado con los JSON y el estado del arte. Solo hay que dejarlo claro en una oracion y pasar a las preguntas de investigacion.

**Posibles preguntas:**

**"Can you give a concrete example?"**
> "Sure. The course Intelligent Agents, code 22A14, must cover specific competencies C1 and C2, generic competencies 1c and 1h, Saber Pro SP5, and dimension D4. If the PDA for that course does not mention anything about communication in a second language, which is generic competency 1c, the agent would flag that as non-compliant and generate a specific comment."

Traduccion: "Claro. El curso Agentes Inteligentes, codigo 22A14, debe cubrir competencias especificas C1 y C2, genericas 1c y 1h, Saber Pro SP5 y dimension D4. Si el PDA de ese curso no menciona nada sobre comunicacion en segunda lengua, que es la competencia generica 1c, el agente lo marcaria como no cumplido y generaria un comentario especifico."

---

## Diapositiva 8: Preguntas de Investigacion (1 minuto)

### En ingles:

> "We formulated two research questions to guide the development."
>
> "RQ1: How accurately can the system identify compliance and non-compliance compared to a human expert reviewer? We will measure this by comparing the agent's evaluations against evaluations made by people."
>
> "RQ2: What is the individual contribution of each system component? We will compare the complete system against simplified versions: only structured lookup, lookup plus RAG without fine-tuning, and the full system. This way we can see whether fine-tuning actually adds value or if RAG alone is enough."

### Traduccion:

> "Formulamos dos preguntas de investigacion para guiar el desarrollo."
>
> "RQ1: Que tan preciso es el sistema para identificar cumplimiento y no-cumplimiento comparado con un revisor humano experto? Esto lo mediremos comparando las evaluaciones del agente contra evaluaciones hechas por personas."
>
> "RQ2: Cual es la contribucion individual de cada componente del sistema? Compararemos el sistema completo contra versiones simplificadas: solo lookup estructurado, lookup mas RAG sin fine-tuning, y el sistema completo. Asi podemos ver si el fine-tuning realmente agrega valor o si RAG solo es suficiente."

### Explicacion:

Las preguntas de investigacion son lo que le da rigor academico al proyecto. No es solo "construir algo", sino hacernos preguntas medibles.

RQ1 es la pregunta mas basica: funciona o no? Lo medimos comparando con humanos.

RQ2 es mas interesante: queremos saber si cada parte del sistema realmente aporta. Si resulta que RAG solo ya es suficiente y el fine-tuning no mejora nada, eso tambien es un resultado valido. A esto se le llama "estudio de ablacion" -- ir quitando piezas para ver cual importa.

**Posibles preguntas:**

**"What metrics will you use for RQ1?"**
> "Precision, recall, and F1 score. Precision measures how many of the issues the system flags are actually real issues. Recall measures how many of the real issues the system actually catches. F1 is the balance between both."

Traduccion: "Precision, recall y F1 score. Precision mide cuantos de los problemas que el sistema marca son problemas reales. Recall mide cuantos de los problemas reales el sistema logra detectar. F1 es el balance entre ambos."

**"What is an ablation study?"**
> "It means removing components one by one to measure their individual impact. We compare: just the JSON lookup alone, then lookup plus RAG, then the full system with fine-tuning. If adding RAG improves results by 20 percent but fine-tuning only adds 2 percent, that tells us where the real value is."

Traduccion: "Significa quitar componentes uno por uno para medir su impacto individual. Comparamos: solo el lookup del JSON, luego lookup mas RAG, luego el sistema completo con fine-tuning. Si agregar RAG mejora los resultados un 20% pero el fine-tuning solo agrega 2%, eso nos dice donde esta el valor real."

---

## Diapositiva 9: Arquitectura del Sistema (1.5 minutos)

### En ingles:

> "This is our system architecture, divided into four stages."
>
> "Stage 1, Document Ingestion: the system receives a PDA as a PDF, extracts the text, and segments it into sections. Each PDA has identifiable sections: learning outcomes, assessment methods, course schedule, and improvement actions."
>
> "Stage 2, Requirement Lookup: the system identifies the course code -- for example 22A14 for Intelligent Agents -- and does a direct lookup in our JSON files to get exactly which competencies, ABET indicators, and other elements that course must cover. This stage is deterministic. It does not use AI. It is a direct query to the structured data."
>
> "Stage 3, Analysis with RAG and LLM: this is the intelligent stage. For each requirement found in Stage 2, the system searches the vector database for the full description of that competency or ABET indicator. For example, for ABET indicator 1.1, it retrieves 'Analyze a problem by identifying the context, variables, and applicable principles'. Then it passes both the PDA section and the requirement description to the LLM, which evaluates whether the section actually covers what the requirement asks."
>
> "Stage 4, Report Generation: it aggregates all the individual evaluations into a final report that lists which sections comply, which do not with specific comments on what is missing, and any content that does not fit the expected format."

### Traduccion:

> "Esta es la arquitectura de nuestro sistema, dividida en cuatro etapas."
>
> "Etapa 1, Ingesta del Documento: el sistema recibe un PDA en PDF, extrae el texto y lo segmenta en secciones. Cada PDA tiene secciones identificables: resultados de aprendizaje, metodos de evaluacion, cronograma y acciones de mejora."
>
> "Etapa 2, Busqueda de Requisitos: el sistema identifica el codigo del curso -- por ejemplo 22A14 para Agentes Inteligentes -- y hace un lookup directo en nuestros archivos JSON para obtener exactamente que competencias, indicadores ABET y demas elementos debe cubrir. Esta etapa es determinista. No usa IA. Es una consulta directa a los datos estructurados."
>
> "Etapa 3, Analisis con RAG y LLM: esta es la etapa inteligente. Para cada requisito encontrado en la Etapa 2, el sistema busca en la base de datos vectorial la descripcion completa de esa competencia o indicador ABET. Por ejemplo, para el indicador ABET 1.1, recupera 'Analiza un problema identificando contexto, variables y principios aplicables'. Luego le pasa al LLM tanto la seccion del PDA como la descripcion del requisito, y el modelo evalua si la seccion realmente cubre lo que pide el requisito."
>
> "Etapa 4, Generacion del Reporte: agrega todas las evaluaciones individuales en un reporte final que lista las secciones que cumplen, las que no cumplen con comentarios especificos de que falta, y cualquier contenido que no corresponda al formato esperado."

### Explicacion:

Esta es la diapositiva mas importante tecnicamente. Lo clave es entender POR QUE hay cuatro etapas separadas:

- La Etapa 1 es procesamiento de texto puro -- extraer y organizar.
- La Etapa 2 es busqueda exacta en datos estructurados. No necesita IA porque sabemos con certeza que competencias necesita cada curso (esta en el JSON). Es como buscar en una tabla de Excel.
- La Etapa 3 es donde entra la IA. Aqui el problema es semantico: necesitamos que un modelo "entienda" si el texto libre del PDA realmente cubre una competencia. No se puede hacer con una busqueda exacta porque el PDA no va a decir textualmente "este curso cubre C1". Va a describir actividades y resultados de aprendizaje que implicitamente cubren esa competencia.
- La Etapa 4 es consolidacion y formato.

**Posibles preguntas:**

**"Why separate Stage 2 and Stage 3?"**
> "They solve fundamentally different problems. Stage 2 answers 'what should this course cover?' -- that is a structured data lookup with a definite answer. Stage 3 answers 'does the PDA text actually address this requirement?' -- that is a natural language understanding problem that needs AI. Mixing them would make the system less reliable because the deterministic part would inherit the uncertainty of the AI part."

Traduccion: "Resuelven problemas fundamentalmente diferentes. La Etapa 2 responde 'que debe cubrir este curso?' -- eso es una consulta a datos estructurados con respuesta definitiva. La Etapa 3 responde 'el texto del PDA realmente aborda este requisito?' -- eso es un problema de comprension de lenguaje natural que necesita IA. Mezclarlos haria el sistema menos confiable porque la parte determinista heredaria la incertidumbre de la parte de IA."

**"Why not use only the LLM without RAG?"**
> "Because the LLM does not know the specific competency definitions of the University of Ibague. If you ask it without context, it would either make things up or give generic answers. RAG provides the exact context needed for each evaluation."

Traduccion: "Porque el LLM no conoce las definiciones especificas de competencias de la Universidad de Ibague. Si le preguntas sin contexto, inventaria o daria respuestas genericas. RAG le da el contexto exacto necesario para cada evaluacion."

**"What frameworks or libraries will you use?"**
> "For RAG: LangChain or LlamaIndex with a vector database like ChromaDB or FAISS. For fine-tuning: Hugging Face Transformers plus PEFT plus TRL, with Unsloth to optimize speed on Colab. For PDF extraction: PyMuPDF or pdfplumber."

Traduccion: "Para RAG: LangChain o LlamaIndex con una base vectorial como ChromaDB o FAISS. Para fine-tuning: Hugging Face Transformers mas PEFT mas TRL, con Unsloth para optimizar velocidad en Colab. Para extraccion de PDF: PyMuPDF o pdfplumber."

---

## Diapositiva 10: Cierre (30 segundos)

### En ingles:

> "In summary, UnibaBot PDA aims to transform a manual process that takes days into an automated pipeline that takes minutes, using structured lookups for deterministic checks and RAG with a fine-tuned LLM for semantic analysis. This brings not only speed but also consistency -- something that manual review cannot guarantee."
>
> "Thank you. We are open to questions."

### Traduccion:

> "En resumen, UnibaBot PDA busca transformar un proceso manual que toma dias en un pipeline automatizado que toma minutos, usando lookups estructurados para verificaciones deterministas y RAG con un LLM fine-tuneado para analisis semantico. Esto trae no solo velocidad sino tambien consistencia -- algo que la revision manual no puede garantizar."
>
> "Gracias. Estamos abiertos a preguntas."

### Explicacion:

Cierren con confianza. El resumen debe tocar los tres puntos clave: (1) el problema es real y toma mucho tiempo, (2) nuestra solucion combina datos estructurados con IA, (3) el resultado es velocidad Y consistencia.

---

## Preguntas adicionales que podrian hacer

### "How is your system different from just giving all PDAs to ChatGPT?"

> "Three key differences. First, our system has the specific rules encoded in structured data -- ChatGPT does not know which competencies each course needs. Second, our system uses RAG to provide precise context for each evaluation instead of relying on the model's general knowledge. Third, with a local fine-tuned model we avoid sending institutional data to external servers and we avoid recurring API costs."

Traduccion: "Tres diferencias clave. Primero, nuestro sistema tiene las reglas especificas codificadas en datos estructurados -- ChatGPT no sabe que competencias necesita cada curso. Segundo, nuestro sistema usa RAG para dar contexto preciso en cada evaluacion en vez de depender del conocimiento general del modelo. Tercero, con un modelo local fine-tuneado evitamos enviar datos institucionales a servidores externos y evitamos costos recurrentes de API."

### "How accurate do you expect the system to be?"

> "That is exactly what RQ1 addresses. Our goal is for it to be at least comparable to a human reviewer, but with the advantage of being 100 percent consistent -- it always applies the same criteria in the same way."

Traduccion: "Eso es exactamente lo que aborda la RQ1. Nuestra meta es que sea al menos comparable a un revisor humano, pero con la ventaja de ser 100% consistente -- siempre aplica los mismos criterios de la misma manera."

### "Can this be extended to other programs?"

> "Yes. The architecture is modular. To add a new program, we would just need to create the JSON mappings for that program's courses and add the relevant competency definitions to the vector database. The model and the pipeline remain the same."

Traduccion: "Si. La arquitectura es modular. Para agregar un nuevo programa, solo necesitariamos crear los mapeos JSON para los cursos de ese programa y agregar las definiciones de competencias relevantes a la base vectorial. El modelo y el pipeline siguen siendo los mismos."

### "What happens if a PDA has sections that should not be there?"

> "Stage 4 of our pipeline handles that. After checking compliance for all required elements, the system also identifies content that does not match any expected section or requirement. It flags those sections in the report as surplus content that may need to be reviewed or removed."

Traduccion: "La Etapa 4 de nuestro pipeline maneja eso. Despues de verificar el cumplimiento de todos los elementos requeridos, el sistema tambien identifica contenido que no corresponde a ninguna seccion o requisito esperado. Marca esas secciones en el reporte como contenido sobrante que podria necesitar ser revisado o eliminado."

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
Define que queremos lograr (objetivo general) y que preguntas queremos responder (RQ1-RQ2). RQ1 mide precision contra humanos, RQ2 mide la contribucion de cada componente via estudio de ablacion.

### Section IV - Proposed System Architecture
Describe el pipeline de 4 etapas. Lo clave es la separacion entre lookup estructurado (etapa 2, determinista) y analisis semantico (etapa 3, con IA). No todo el problema requiere IA; la parte de "que competencias necesita este curso" es una consulta directa a un JSON.

### Section V - Evaluation Methodology
Explica como vamos a medir si el sistema funciona. Tres dimensiones: correctness (precision vs revisores humanos), granularity (calidad de los comentarios generados), y consistency (que siempre de la misma respuesta para el mismo PDA). Tambien describe un estudio de ablacion: comparar el sistema completo contra versiones parciales para aislar la contribucion de cada componente.

### Section VI - Conclusion
Cierra resumiendo la propuesta y lo que se establecio en el articulo. Resalta el gap en la literatura y como nuestro trabajo lo aborda.

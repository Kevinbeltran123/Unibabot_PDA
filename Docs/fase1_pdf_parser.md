# Fase 1: Extraccion y segmentacion de PDFs

## Que vamos a construir

Un modulo `src/pdf_parser.py` que recibe un PDA en PDF y retorna un diccionario con sus secciones:

```python
{
  "1. General Information": "System Engineering\nSpecific professional\n...",
  "2. Context of the subject": "Today, intelligent systems are...",
  "4. Expected Learning Outcomes": "At the end of this course...",
  ...
}
```

Este diccionario es la entrada de todo lo que sigue: el RAG busca lineamientos para cada seccion, y el LLM evalua cada seccion por separado. Si esta fase falla, todo lo que viene despues falla con ella.

---

## Teoria: como funciona un PDF por dentro

Antes de escribir codigo, hay que entender por que extraer texto de un PDF no es tan simple como abrir un `.txt`.

Un PDF **no es un documento de texto**. Internamente es una serie de instrucciones graficas: "dibuja el caracter 'H' en la coordenada (72, 680)", "dibuja el caracter 'e' en (78, 680)", etc. No hay parrafos, no hay secciones, no hay estructura logica. Solo posiciones en una pagina.

Esto tiene tres consecuencias practicas:

**1. El orden no esta garantizado.** El parser extrae los caracteres en el orden en que aparecen en el archivo, que no siempre es el orden de lectura. Los documentos bien generados (como un Word exportado a PDF) suelen estar en orden. Los PDFs escaneados o mal construidos pueden estar completamente mezclados.

**2. Las tablas son un problema.** Una tabla en PDF es una cuadricula de cajas independientes. El parser puede leer fila por fila o columna por columna dependiendo de como fue construida. Para los PDAs, que tienen tablas en la seccion de informacion general, esto puede generar texto raro.

**3. No hay encabezados semanticos.** En HTML existe `<h1>`, `<h2>`. En PDF no. Un encabezado visualmente grande es simplemente texto con una fuente mas grande o en negrita. Para detectar secciones, tenemos que buscar patrones en el contenido del texto (numeros, mayusculas, palabras clave).

### Por que PyMuPDF

Existen varias librerias para extraer texto de PDFs en Python:

| Libreria | Ventaja | Desventaja |
|----------|---------|------------|
| `PyMuPDF` (fitz) | Rapida, precisa, mantiene orden de lectura | Requiere compilacion en algunos sistemas |
| `pdfplumber` | Excelente para tablas, mas control sobre coordenadas | Mas lenta |
| `pypdf` | Simple, pura Python | Menor precision en documentos complejos |
| `pdfminer` | Muy detallada (coordenadas exactas) | API compleja, verbosa |

Para los PDAs usamos `PyMuPDF` porque los documentos son PDFs bien estructurados (generados desde Word), el orden de extraccion es confiable, y la API es limpia.

---

## Setup del entorno

Primero crea la estructura de carpetas del proyecto. Ejecuta esto desde la raiz del repositorio:

```bash
mkdir -p src/rag src/fine_tuning src/prompts
mkdir -p data/pdas data/lineamientos
mkdir -p models notebooks results tests
touch src/__init__.py src/rag/__init__.py src/fine_tuning/__init__.py
touch requirements.txt
```

Mueve el PDA a su carpeta:

```bash
mv "PDA - Intelligent Agents 2026A-01.docx.pdf" data/pdas/
```

Crea un entorno virtual e instala la dependencia de esta fase:

```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
pip install pymupdf
```

Agrega al `requirements.txt`:

```
pymupdf>=1.24.0
```

---

## Implementacion paso a paso

### Paso 1: Extraccion basica por pagina

Crea el archivo `src/pdf_parser.py` y escribe esta primera funcion:

```python
import fitz  # PyMuPDF


def extraer_texto_por_pagina(ruta_pdf: str) -> list[str]:
    """
    Abre un PDF y retorna una lista donde cada elemento
    es el texto completo de una pagina.

    Args:
        ruta_pdf: ruta al archivo PDF

    Returns:
        Lista de strings, uno por pagina
    """
    doc = fitz.open(ruta_pdf)
    paginas = []
    for pagina in doc:
        paginas.append(pagina.get_text())
    doc.close()
    return paginas
```

**Por que retornar una lista por pagina y no todo junto?**

Porque a veces quieres inspeccionar pagina por pagina para entender la estructura antes de procesarla. La funcion siguiente las unira cuando sea necesario. Separar responsabilidades hace el codigo mas facil de depurar.

Prueba que funciona:

```python
# Ejecuta desde la raiz del proyecto con: python -c "..."
from src.pdf_parser import extraer_texto_por_pagina

paginas = extraer_texto_por_pagina("data/pdas/PDA - Intelligent Agents 2026A-01.docx.pdf")

print(f"Total de paginas: {len(paginas)}")
print("--- PAGINA 1 ---")
print(paginas[0])
```

Deberias ver el texto de la primera pagina. Verifica que el orden sea correcto (encabezado -> informacion general -> etc.).

---

### Paso 2: Entender el patron de los encabezados

Antes de escribir la segmentacion, analiza el texto extraido para identificar como se ven los encabezados:

```python
paginas = extraer_texto_por_pagina("data/pdas/PDA - Intelligent Agents 2026A-01.docx.pdf")
texto_completo = "\n".join(paginas)

for i, linea in enumerate(texto_completo.split("\n")):
    linea_limpia = linea.strip()
    if linea_limpia:  # ignorar lineas vacias
        print(f"{i:4d} | {linea_limpia[:80]}")
```

Al revisar la salida, notaras que los encabezados de seccion siguen el patron:

```
1. General Information
2. Context of the subject
3. Description and purpose of the course
4. Expected Learning Outcomes (Resultados de Aprendizaje Esperados - RAE)
5. Methodology and Learning Activities
```

Patron comun: **numero entero + punto + espacio + texto con mayuscula inicial**.

---

### Paso 3: Expresiones regulares para detectar encabezados

Una expresion regular (regex) es un patron que describe la forma de un texto. Python las maneja con el modulo `re`.

Para los encabezados del PDA, el patron es: "linea que empieza con uno o mas digitos, seguidos de un punto y un espacio":

```python
import re

patron = r'^\d+\.\s+'
```

Desglose del patron:
- `^` -- el patron debe estar al inicio de la linea
- `\d+` -- uno o mas digitos (1, 2, 10, 23...)
- `\.` -- un punto literal (el backslash escapa el punto porque en regex `.` significa "cualquier caracter")
- `\s+` -- uno o mas espacios en blanco

Prueba el patron contra las lineas del documento:

```python
for linea in texto_completo.split("\n"):
    linea_limpia = linea.strip()
    if re.match(r'^\d+\.\s+', linea_limpia):
        print(f"ENCABEZADO: '{linea_limpia}'")
```

Revisa la salida: captura exactamente los encabezados de seccion? O captura cosas que no son encabezados (como items de una lista numerada "1. algo")?

Si hay falsos positivos, puedes hacerlo mas estricto exigiendo que el texto despues del numero empiece con mayuscula:

```python
patron_estricto = r'^\d+\.\s+[A-Z]'
```

---

### Paso 4: La funcion de segmentacion

Con el patron identificado, ahora implementas la logica de segmentacion.

El algoritmo es un **recorrido lineal con estado**:
- Mantienes dos variables: la seccion actual y el contenido acumulado
- Cuando encuentras un encabezado, guardas lo acumulado y empiezas una nueva seccion
- Al terminar el loop, guardas la ultima seccion (que nunca tuvo un "siguiente encabezado" que la cerrara)

Agrega esto a `src/pdf_parser.py`:

```python
import re


def segmentar_secciones(paginas: list[str]) -> dict[str, str]:
    """
    Recibe la lista de paginas y retorna un diccionario
    {nombre_seccion: contenido} detectando los encabezados
    numerados del PDA.

    Args:
        paginas: lista de strings con el texto de cada pagina

    Returns:
        Diccionario donde la clave es el nombre de la seccion
        y el valor es su contenido
    """
    texto_completo = "\n".join(paginas)
    lineas = texto_completo.split("\n")

    secciones = {}
    seccion_actual = "encabezado"  # texto antes de la primera seccion
    contenido_actual = []

    for linea in lineas:
        linea_limpia = linea.strip()

        if re.match(r'^\d+\.\s+[A-Z]', linea_limpia):
            # Guardar la seccion anterior antes de empezar la nueva
            if contenido_actual:
                secciones[seccion_actual] = "\n".join(contenido_actual).strip()

            # Iniciar nueva seccion
            seccion_actual = linea_limpia
            contenido_actual = []
        else:
            # Acumular contenido de la seccion actual
            contenido_actual.append(linea)

    # Guardar la ultima seccion (no tiene encabezado siguiente que la cierre)
    if contenido_actual:
        secciones[seccion_actual] = "\n".join(contenido_actual).strip()

    return secciones
```

**Por que `contenido_actual` es una lista y no un string?**

Porque concatenar strings en un loop es ineficiente en Python. Cada `string1 + string2` crea un nuevo objeto en memoria. Acumular en una lista y hacer `"\n".join()` al final es O(n) en vez de O(n²).

---

### Paso 5: Funcion principal que orquesta todo

Agrega una funcion conveniente que recibe la ruta del PDF y retorna las secciones directamente:

```python
def parsear_pda(ruta_pdf: str) -> dict[str, str]:
    """
    Pipeline completo: recibe un PDF de PDA y retorna
    sus secciones como diccionario.

    Args:
        ruta_pdf: ruta al archivo PDF del PDA

    Returns:
        Diccionario {nombre_seccion: contenido}
    """
    paginas = extraer_texto_por_pagina(ruta_pdf)
    secciones = segmentar_secciones(paginas)
    return secciones
```

---

### El archivo completo: `src/pdf_parser.py`

```python
import re
import fitz  # PyMuPDF


def extraer_texto_por_pagina(ruta_pdf: str) -> list[str]:
    """
    Abre un PDF y retorna una lista donde cada elemento
    es el texto completo de una pagina.
    """
    doc = fitz.open(ruta_pdf)
    paginas = []
    for pagina in doc:
        paginas.append(pagina.get_text())
    doc.close()
    return paginas


def segmentar_secciones(paginas: list[str]) -> dict[str, str]:
    """
    Recibe la lista de paginas y retorna un diccionario
    {nombre_seccion: contenido} detectando los encabezados
    numerados del PDA.
    """
    texto_completo = "\n".join(paginas)
    lineas = texto_completo.split("\n")

    secciones = {}
    seccion_actual = "encabezado"
    contenido_actual = []

    for linea in lineas:
        linea_limpia = linea.strip()

        if re.match(r'^\d+\.\s+[A-Z]', linea_limpia):
            if contenido_actual:
                secciones[seccion_actual] = "\n".join(contenido_actual).strip()
            seccion_actual = linea_limpia
            contenido_actual = []
        else:
            contenido_actual.append(linea)

    if contenido_actual:
        secciones[seccion_actual] = "\n".join(contenido_actual).strip()

    return secciones


def parsear_pda(ruta_pdf: str) -> dict[str, str]:
    """
    Pipeline completo: recibe un PDF de PDA y retorna
    sus secciones como diccionario.
    """
    paginas = extraer_texto_por_pagina(ruta_pdf)
    secciones = segmentar_secciones(paginas)
    return secciones
```

---

## Tu turno: lo que debes implementar

La funcion `segmentar_secciones` tiene un problema potencial que no esta resuelto: **el ruido de los encabezados de pagina**.

Mira el PDF del PDA: cada pagina tiene un bloque superior con `PDA`, `Intelligent Agents`, `22A14`, `Engineering Faculty`, `System Engineering Program`. Ese texto se extrae en cada pagina y puede contaminar el contenido de las secciones.

**Tu tarea:** Agrega una funcion `limpiar_ruido(texto: str) -> str` que recibe el contenido de una seccion y elimina las lineas que corresponden al encabezado de pagina. Considera: como identificas esas lineas? Son siempre iguales en todas las paginas? Puedes asumir que el codigo del curso (`22A14`) y la palabra `PDA` son marcadores confiables.

```python
def limpiar_ruido(texto: str) -> str:
    """
    Elimina el texto repetido del encabezado de cada pagina
    del contenido de las secciones.

    TODO: implementar
    """
    pass
```

---

## Validacion: como saber que funciona

Corre este script de prueba y verifica manualmente los resultados:

```python
from src.pdf_parser import parsear_pda

secciones = parsear_pda("data/pdas/PDA - Intelligent Agents 2026A-01.docx.pdf")

print(f"Secciones encontradas: {len(secciones)}")
print()

for nombre, contenido in secciones.items():
    print(f"=== {nombre} ===")
    print(contenido[:200])  # primeros 200 caracteres
    print()
```

**Criterios de exito:**
- Cada seccion del PDA tiene su propia entrada en el diccionario
- El contenido de cada seccion corresponde a lo que se ve en el PDF
- No hay mezcla de contenido entre secciones
- El texto del encabezado de pagina no contamina el contenido (si implementaste `limpiar_ruido`)

---

## Proximos pasos

Una vez que `parsear_pda` retorna secciones limpias y correctas, estamos listos para la Fase 2: construir la base vectorial que permitira buscar lineamientos relevantes para cada una de estas secciones.

El output de esta fase es la entrada del RAG. Cada valor del diccionario se convertira en una consulta: "dado este contenido de la seccion de RAE, dame los lineamientos institucionales mas relevantes".

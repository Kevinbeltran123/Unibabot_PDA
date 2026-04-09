"""
Genera outputs para los pares crudos usando Llama 3.2 via ollama.

Usa un prompt mas detallado que el baseline para producir evaluaciones
de mayor calidad que sirvan como datos de entrenamiento.

Despues de generar, el usuario debe revisar y corregir manualmente.
"""

import json
import sys
import ollama
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
PARES_PATH = ROOT / "data" / "pares_crudos.jsonl"
TRAIN_PATH = ROOT / "data" / "training_dataset.jsonl"
VAL_PATH = ROOT / "data" / "validation_dataset.jsonl"

MODELO = "llama3.2"

PROMPT_GENERACION = """Eres un evaluador academico experto de la Universidad de Ibague. Debes evaluar si una seccion de un PDA (Plan de Desarrollo Academico) cumple con lineamientos institucionales.

REGLAS ESTRICTAS:
- Responde SOLO con JSON valido, sin texto antes ni despues
- Cada lineamiento debe tener una evaluacion
- "evidencia" debe citar texto especifico de la seccion, o explicar por que no se encontro
- "correccion" debe ser una accion concreta y realizable, o null si cumple
- Se riguroso: si la seccion no menciona explicitamente algo, es NO CUMPLE

{input_text}

Responde con este JSON exacto:
{{
  "seccion": "nombre de la seccion",
  "hallazgos": [
    {{
      "regla": "el lineamiento evaluado",
      "estado": "CUMPLE" o "NO CUMPLE",
      "evidencia": "cita textual o explicacion especifica",
      "correccion": "accion concreta requerida, o null si cumple"
    }}
  ]
}}"""


def cargar_pares() -> list[dict]:
    pares = []
    with open(PARES_PATH, encoding="utf-8") as f:
        for line in f:
            pares.append(json.loads(line))
    return pares


def generar_output(par: dict) -> str:
    """Genera el output para un par usando Llama 3.2."""
    prompt = PROMPT_GENERACION.format(input_text=par["input"][:3000])

    response = ollama.chat(
        model=MODELO,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1, "num_ctx": 4096},
    )

    texto = response["message"]["content"]

    # Validar que es JSON parseable
    try:
        inicio = texto.find("{")
        fin = texto.rfind("}") + 1
        if inicio >= 0 and fin > inicio:
            parsed = json.loads(texto[inicio:fin])
            return json.dumps(parsed, ensure_ascii=False)
    except json.JSONDecodeError:
        pass

    # Si fallo el parseo, devolver crudo
    return texto


def main():
    pares = cargar_pares()
    total = len(pares)
    completados = []
    errores = 0

    print(f"Generando outputs para {total} pares...\n")

    for i, par in enumerate(pares):
        seccion = par["input"].split("\n")[0].replace("SECCION: ", "")
        print(f"  [{i+1}/{total}] {seccion[:60]}...", end=" ", flush=True)

        try:
            output = generar_output(par)
            par["output"] = output
            completados.append(par)
            print("OK")
        except Exception as e:
            errores += 1
            print(f"ERROR: {e}")

    # Dividir en train (90%) y validation (10%)
    split_idx = int(len(completados) * 0.9)
    train = completados[:split_idx]
    val = completados[split_idx:]

    # Guardar (sin campo metadata, solo instruction/input/output)
    def guardar(datos, path):
        with open(path, "w", encoding="utf-8") as f:
            for item in datos:
                registro = {
                    "instruction": item["instruction"],
                    "input": item["input"],
                    "output": item["output"],
                }
                f.write(json.dumps(registro, ensure_ascii=False) + "\n")

    guardar(train, TRAIN_PATH)
    guardar(val, VAL_PATH)

    print(f"\nResultados:")
    print(f"  Completados: {len(completados)}/{total}")
    print(f"  Errores: {errores}")
    print(f"  Training: {len(train)} ejemplos -> {TRAIN_PATH}")
    print(f"  Validation: {len(val)} ejemplos -> {VAL_PATH}")


if __name__ == "__main__":
    main()

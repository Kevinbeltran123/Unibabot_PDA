# Primera vez: crea el venv e instala todas las dependencias Python y Node.
# Uso: .\scripts\setup.ps1
#
# La variable de entorno VENV sobreescribe la ruta del venv.
# Default: $env:USERPROFILE\.venvs\unibabot
# IMPORTANTE: el venv debe quedar FUERA de OneDrive para evitar eviccion de archivos.

$VenvRoot = if ($env:VENV) { $env:VENV } else { "$env:USERPROFILE\.venvs\unibabot" }
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "[setup] Creando venv en $VenvRoot ..."
python -m venv $VenvRoot

Write-Host "[setup] Instalando dependencias Python ..."
& "$VenvRoot\Scripts\pip" install --upgrade pip --quiet
& "$VenvRoot\Scripts\pip" install -r "$Root\requirements-api.txt"

Write-Host "[setup] Instalando dependencias Node ..."
npm install --prefix "$Root\web" --silent

Write-Host "[setup] Listo."
Write-Host "  Siguiente paso: .\scripts\dev.ps1"
Write-Host "  (Asegurate de que Redis y Ollama esten corriendo antes de arrancar.)"

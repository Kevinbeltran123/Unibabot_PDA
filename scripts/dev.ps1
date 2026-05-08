# Levanta los 4 procesos del stack en Windows (nativo o WSL2).
# Uso: .\scripts\dev.ps1
# Requiere: redis-server en PATH, venv en $env:USERPROFILE\.venvs\unibabot, deps de web instaladas.

$VenvRoot = if ($env:VENV) { $env:VENV } else { "$env:USERPROFILE\.venvs\unibabot" }
$Root = Split-Path -Parent $PSScriptRoot

# Verificar redis
try { redis-cli ping | Out-Null } catch {
    Write-Error "Redis no esta corriendo. Inicialo con: redis-server"
    exit 1
}

if (-not (Test-Path "$VenvRoot\Scripts\python.exe")) {
    Write-Error "venv no encontrado en $VenvRoot"
    Write-Host "  python -m venv $VenvRoot"
    Write-Host "  & '$VenvRoot\Scripts\pip' install -r requirements-api.txt"
    exit 1
}

Set-Location $Root

Write-Host "[dev] Iniciando API en :8000 ..."
$api = Start-Process "$VenvRoot\Scripts\uvicorn.exe" `
    -ArgumentList "src.api.main:app","--reload","--port","8000" `
    -PassThru -NoNewWindow

Write-Host "[dev] Iniciando worker RQ ..."
$worker = Start-Process "$VenvRoot\Scripts\python.exe" `
    -ArgumentList "-m","src.api.jobs.worker" `
    -PassThru -NoNewWindow

Write-Host "[dev] Iniciando frontend en :3000 ..."
$web = Start-Process "npm.cmd" `
    -ArgumentList "run","dev" `
    -WorkingDirectory "$Root\web" `
    -PassThru -NoNewWindow

Write-Host "[dev] Stack corriendo. Ctrl+C para detener todo."
try { Wait-Process -Id $api.Id,$worker.Id,$web.Id }
finally {
    $api,$worker,$web | ForEach-Object { if (-not $_.HasExited) { $_.Kill() } }
    Write-Host "[dev] Detenido."
}

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SetupScript = Join-Path $ProjectRoot "scripts\setup.ps1"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath $PythonExe)) {
    Write-Host ".venv is missing. Running scripts\setup.ps1 first."
    & $SetupScript
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

$BindHost = & $PythonExe -c "from app.settings import load_config; print(load_config().get('app', {}).get('host', '127.0.0.1'))"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($BindHost)) {
    Write-Error "Failed to read app.host from config\config.yaml."
    exit 1
}

$BindPort = & $PythonExe -c "from app.settings import load_config; print(load_config().get('app', {}).get('port', 8787))"
if ($LASTEXITCODE -ne 0 -or $BindPort -notmatch '^\d+$') {
    Write-Error "Failed to read a valid app.port from config\config.yaml."
    exit 1
}

Write-Host "Starting LongPathGuard at http://$BindHost`:$BindPort"
& $PythonExe -m uvicorn app.main:app --host $BindHost --port $BindPort
exit $LASTEXITCODE

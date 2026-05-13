$ErrorActionPreference = "Stop"

$ServiceName = "LongPathGuard"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LocalNssm = Join-Path $ProjectRoot "scripts\tools\nssm.exe"
$NssmCommand = $null

if (Test-Path $LocalNssm) {
    $NssmCommand = $LocalNssm
} else {
    $Found = Get-Command "nssm.exe" -ErrorAction SilentlyContinue
    if ($Found) {
        $NssmCommand = $Found.Source
    }
}

if (-not $NssmCommand) {
    Write-Host "nssm.exe was not found."
    Write-Host "Download NSSM and place nssm.exe into scripts\tools\nssm.exe, or add it to PATH."
    Write-Host "NSSM website: https://nssm.cc/download"
    exit 1
}

Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BindHost = & $PythonExe -c "from app.settings import load_config; print(load_config().get('app', {}).get('host', '127.0.0.1'))"
if ([string]::IsNullOrWhiteSpace($BindHost)) {
    $BindHost = "127.0.0.1"
}
$BindPort = & $PythonExe -c "from app.settings import load_config; print(load_config().get('app', {}).get('port', 8787))"
if ($BindPort -notmatch '^\d+$') {
    $BindPort = "8787"
}
$AppParameters = "-m uvicorn app.main:app --host $BindHost --port $BindPort"

& $NssmCommand install $ServiceName $PythonExe $AppParameters
& $NssmCommand set $ServiceName AppDirectory $ProjectRoot
& $NssmCommand set $ServiceName Start SERVICE_AUTO_START
& $NssmCommand set $ServiceName AppStdout (Join-Path $ProjectRoot "data\service.out.log")
& $NssmCommand set $ServiceName AppStderr (Join-Path $ProjectRoot "data\service.err.log")
& $NssmCommand set $ServiceName AppExit Default Restart
& $NssmCommand set $ServiceName AppThrottle 15000

Write-Host "Service $ServiceName installed."
Write-Host "Service will run on $BindHost`:$BindPort."
Write-Host "Start it with: .\scripts\start_service.ps1"

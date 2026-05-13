$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

$BindHost = & ".\.venv\Scripts\python.exe" -c "from app.settings import load_config; print(load_config().get('app', {}).get('host', '127.0.0.1'))"
if ([string]::IsNullOrWhiteSpace($BindHost)) {
    $BindHost = "127.0.0.1"
}

$BindPort = & ".\.venv\Scripts\python.exe" -c "from app.settings import load_config; print(load_config().get('app', {}).get('port', 8787))"
if ($BindPort -notmatch '^\d+$') {
    $BindPort = "8787"
}

& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --host $BindHost --port $BindPort

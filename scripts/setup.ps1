$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$ConfigDir = Join-Path $ProjectRoot "config"
$DataDir = Join-Path $ProjectRoot "data"
$ConfigPath = Join-Path $ConfigDir "config.yaml"
$ExampleConfigPath = Join-Path $ConfigDir "config.example.yaml"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

function Assert-LastExitCode {
    param([string]$Message)
    if ($LASTEXITCODE -ne 0) {
        Write-Error $Message
        exit $LASTEXITCODE
    }
}

Set-Location $ProjectRoot

$PythonCommand = Get-Command "python.exe" -ErrorAction SilentlyContinue
if (-not $PythonCommand) {
    Write-Error "Python was not found in PATH. Install 64-bit Python 3.12, 3.13, or 3.14 and try again."
    exit 1
}

& $PythonCommand.Source -c "import sys; raise SystemExit(0 if (3, 12) <= sys.version_info[:2] <= (3, 14) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Error "LongPathGuard requires Python 3.12, 3.13, or 3.14. Check with: python --version"
    exit 1
}

New-Item -ItemType Directory -Path $ConfigDir -Force | Out-Null
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    if (-not (Test-Path -LiteralPath $ExampleConfigPath)) {
        Write-Error "Missing config\config.example.yaml. The local configuration was not created."
        exit 1
    }
    Copy-Item -LiteralPath $ExampleConfigPath -Destination $ConfigPath
    Write-Host "Created config\config.yaml from config.example.yaml."
} else {
    Write-Host "Keeping existing config\config.yaml."
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    & $PythonCommand.Source -m venv (Join-Path $ProjectRoot ".venv")
    Assert-LastExitCode "Failed to create .venv."
}

& $VenvPython -m pip install --upgrade pip
Assert-LastExitCode "Failed to update pip."
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
Assert-LastExitCode "Failed to install requirements.txt."

Write-Host "LongPathGuard setup completed successfully."
Write-Host "Next: edit config\config.yaml, then run .\scripts\run.ps1"


$ErrorActionPreference = "Stop"

$ServiceName = "LongPathGuard"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SetupScript = Join-Path $ProjectRoot "scripts\setup.ps1"
$LocalNssm = Join-Path $ProjectRoot "scripts\tools\nssm.exe"
$NssmCommand = $null

function Assert-LastExitCode {
    param([string]$Message)
    if ($LASTEXITCODE -ne 0) {
        Write-Error $Message
        exit $LASTEXITCODE
    }
}

if (Test-Path -LiteralPath $LocalNssm) {
    $NssmCommand = $LocalNssm
} else {
    $FoundNssm = Get-Command "nssm.exe" -ErrorAction SilentlyContinue
    if ($FoundNssm) {
        $NssmCommand = $FoundNssm.Source
    }
}

if (-not $NssmCommand) {
    Write-Error "nssm.exe was not found. Place it at scripts\tools\nssm.exe or add it to PATH. NSSM is not downloaded automatically."
    exit 1
}

if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
    Write-Error "Service '$ServiceName' already exists. Use the existing service or run scripts\uninstall_service.ps1 first."
    exit 1
}

& $SetupScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Set-Location $ProjectRoot
$DataDir = Join-Path $ProjectRoot "data"
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null

$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
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

$AppParameters = "-m uvicorn app.main:app --host $BindHost --port $BindPort"

& $NssmCommand install $ServiceName $PythonExe
Assert-LastExitCode "NSSM failed to create service '$ServiceName'."
& $NssmCommand set $ServiceName AppParameters $AppParameters
Assert-LastExitCode "Failed to configure service arguments."
& $NssmCommand set $ServiceName AppDirectory $ProjectRoot
Assert-LastExitCode "Failed to configure the service working directory."
& $NssmCommand set $ServiceName Start SERVICE_AUTO_START
Assert-LastExitCode "Failed to configure automatic startup."
& $NssmCommand set $ServiceName AppStdout (Join-Path $DataDir "service.out.log")
Assert-LastExitCode "Failed to configure service stdout."
& $NssmCommand set $ServiceName AppStderr (Join-Path $DataDir "service.err.log")
Assert-LastExitCode "Failed to configure service stderr."
& $NssmCommand set $ServiceName AppExit Default Restart
Assert-LastExitCode "Failed to configure restart on failure."
& $NssmCommand set $ServiceName AppThrottle 15000
Assert-LastExitCode "Failed to configure restart throttling."

Write-Host "Service '$ServiceName' installed for http://$BindHost`:$BindPort"
Write-Host "Start:     .\scripts\start_service.ps1"
Write-Host "Stop:      .\scripts\stop_service.ps1"
Write-Host "Uninstall: .\scripts\uninstall_service.ps1"

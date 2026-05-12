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
    Write-Host "nssm.exe was not found. Remove the service manually or add nssm.exe to PATH."
    exit 1
}

& $NssmCommand stop $ServiceName
& $NssmCommand remove $ServiceName confirm
Write-Host "Service $ServiceName removed."

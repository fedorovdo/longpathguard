$ErrorActionPreference = "Stop"
Stop-Service -Name "LongPathGuard"
Write-Host "Service LongPathGuard stopped."

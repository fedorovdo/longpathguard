$ErrorActionPreference = "Stop"
Start-Service -Name "LongPathGuard"
Write-Host "Service LongPathGuard started."

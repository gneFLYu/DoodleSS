# Canonical launcher for the current HFPSS Studio application.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "HFPSS Studio: http://127.0.0.1:5078/"
python backend/app.py

$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

docker compose up -d db
docker compose --profile tools run --rm db-seed

Write-Host ""
Write-Host "PostgreSQL is ready for the desktop app:"
Write-Host "  database: performance_db"
Write-Host "  user:     postgres"
Write-Host "  password: 1"
Write-Host "  host:     localhost"
Write-Host "  port:     5432"
Write-Host ""
Write-Host "Now run: dist\MPT Journal\MPT Journal.exe"

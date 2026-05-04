$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

python -m PyInstaller `
  --name "MPT Journal" `
  --windowed `
  --noconfirm `
  --clean `
  --add-data "templates;templates" `
  --add-data "core\templates;core\templates" `
  --add-data "users\templates;users\templates" `
  --add-data "grading\templates;grading\templates" `
  --add-data "reports\templates;reports\templates" `
  --add-data "templates\registration;templates\registration" `
  --add-data "media;media" `
  --hidden-import "psycopg" `
  --hidden-import "psycopg_binary" `
  --hidden-import "drf_spectacular" `
  --hidden-import "rest_framework" `
  --hidden-import "config.api_urls" `
  --hidden-import "config.api_viewsets" `
  --hidden-import "config.api_serializers" `
  --hidden-import "grading.api_views" `
  --hidden-import "grading.serializers" `
  desktop_app.py

Write-Host ""
Write-Host "Done: dist\MPT Journal\MPT Journal.exe"

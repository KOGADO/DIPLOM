$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $projectRoot

$seedDir = Join-Path $projectRoot "docker\seed"
$seedPath = Join-Path $seedDir "initial_data.json"

New-Item -ItemType Directory -Force -Path $seedDir | Out-Null

python manage.py dumpdata `
  --natural-foreign `
  --natural-primary `
  --indent 2 `
  --exclude contenttypes `
  --exclude auth.Permission `
  --exclude sessions.Session `
  --exclude admin.LogEntry `
  --output $seedPath

$text = Get-Content -Raw -Encoding Default -Path $seedPath
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($seedPath, $text, $utf8NoBom)

python -m json.tool $seedPath | Out-Null

Write-Host "Seed exported: docker\seed\initial_data.json"

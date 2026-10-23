# Builds dist\NightreignRatingOverlay.exe (single file, no console window).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
.venv\Scripts\python -m pip install -q -e ".[dev]"
.venv\Scripts\python -m pytest -q
if ($LASTEXITCODE) { exit $LASTEXITCODE }
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed `
    --name NightreignRatingOverlay `
    --paths src `
    --add-data "src/nr_overlay/static;nr_overlay/static" `
    src/nr_overlay/__main__.py
if ($LASTEXITCODE) { Write-Host "Build failed. Is NightreignRatingOverlay.exe still running?"; exit $LASTEXITCODE }
Copy-Item LICENSE, THIRD_PARTY_NOTICES.txt dist
Write-Host "Built: $PSScriptRoot\dist\NightreignRatingOverlay.exe"

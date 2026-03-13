$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual environment not found at .venv. Create it first."
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

& $python -m pip install --disable-pip-version-check --no-input -r requirements.txt

if (Test-Path "$root\build") {
    Remove-Item "$root\build" -Recurse -Force
}

if (Test-Path "$root\dist") {
    Remove-Item "$root\dist" -Recurse -Force
}

& $python "$root\tools\generate_icon.py"

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name Ellie `
    --icon "$root\build\ellie.ico" `
    --add-data "$root\data\taskmng.db;data" `
    --add-data "$root\Logo\EliieAppN.png;Logo" `
    "$root\main.py"

$releaseTarget = Join-Path (Split-Path -Parent $root) "Ellie.exe"
Copy-Item "$root\dist\Ellie.exe" $releaseTarget -Force

Write-Host ""
Write-Host "Build completed:" -ForegroundColor Green
Write-Host "  $releaseTarget"

# VoxTerrae portable build (Windows 11, PowerShell). Run from anywhere:  powershell -ExecutionPolicy Bypass -File build\build_win.ps1
# Produces dist\VoxTerrae.exe (single portable file). Needs Python 3.11+ on PATH.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
Write-Host "== VoxTerrae build in $root"
if (-not (Test-Path ".venv")) { py -3.11 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
& .\.venv\Scripts\python.exe -m pip install --quiet "PySide6-Essentials>=6.8" "qasync>=0.27" "pyinstaller>=6.10" pytest
Write-Host "== unit tests"
$env:PYTHONPATH = "$root\src"
& .\.venv\Scripts\python.exe -m pytest -q tests\test_message.py tests\test_store.py
if ($LASTEXITCODE -ne 0) { throw "unit tests failed" }
Write-Host "== build"
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean build\voxterrae.spec
if (-not (Test-Path "dist\VoxTerrae.exe")) { throw "no exe produced" }
$exe = Get-Item "dist\VoxTerrae.exe"
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
Write-Host ("== OK  {0}  {1:N0} bytes  sha256 {2}" -f $exe.FullName, $exe.Length, $hash)
Write-Host "== smoke (demo render, no network): dist\VoxTerrae.exe --demo --shot dist\smoke.png 1280x720"
& $exe.FullName --demo --shot dist\smoke.png 1280x720
if (Test-Path "dist\smoke.png") { Write-Host "== smoke render written: dist\smoke.png" } else { Write-Warning "smoke render missing" }

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
$env:QT_QPA_PLATFORM = "offscreen"; $env:VOXTERRAE_NO_UPDATE_CHECK = "1"
& .\.venv\Scripts\python.exe -m pytest -q tests
if ($LASTEXITCODE -ne 0) { throw "tests failed" }
Remove-Item Env:QT_QPA_PLATFORM
Write-Host "== build"
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean build\voxterrae.spec
if (-not (Test-Path "dist\VoxTerrae.exe")) { throw "no exe produced" }
$exe = Get-Item "dist\VoxTerrae.exe"
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash
Write-Host ("== OK  {0}  {1:N0} bytes  sha256 {2}" -f $exe.FullName, $exe.Length, $hash)
Write-Host "== smoke: run the built exe itself (a windowed exe returns to the console at once, so wait on the process)"
if (Test-Path "dist\smoke.png") { Remove-Item "dist\smoke.png" }
$p = Start-Process -FilePath $exe.FullName -ArgumentList '--demo','--shot','dist\smoke.png','1280x720','--after','1' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw ("exe smoke run exited {0}: the build does not start" -f $p.ExitCode) }
if (-not (Test-Path "dist\smoke.png")) { throw "exe smoke run produced no render: the build does not start" }
Write-Host "== smoke OK: dist\smoke.png written by the exe itself"

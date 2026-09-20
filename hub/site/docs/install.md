---
title: Install
summary: Get VoxTerrae running on Windows 11, from the portable exe or from source.
order: 1
---
## Portable exe (Windows 11)
1. Download `VoxTerrae.exe` from the [download page](/download). One file, no installer, no admin rights.
2. Put it anywhere (Desktop, a USB stick). Double-click.
3. Windows may show **"Windows protected your PC"**. This is SmartScreen reacting to a new, not-yet-signed program, not a malware verdict. Click **More info → Run anyway**, or verify the file first (see [Verify a download](/docs/verify)). The [roadmap](/releases) has code signing scheduled.

Your data lives in `%LOCALAPPDATA%\VoxTerrae\` (`voxterrae.db` for history, `tls_pins.json` for pinned EFnet certificates, settings). Delete that folder to reset everything.

## From source (any OS with Python 3.11+)
```
pip install "PySide6-Essentials>=6.8" "qasync>=0.27"
set PYTHONPATH=src           # PowerShell: $env:PYTHONPATH="src"
python -m voxterrae.app
```
Build your own portable exe on Windows: `powershell -ExecutionPolicy Bypass -File build\build_win.ps1`. The script runs the unit tests, builds `dist\VoxTerrae.exe`, prints its SHA-256 and writes a smoke render.

## Requirements
Windows 10 1809 or later (Windows 11 recommended), about 120 MB of disk for the extracted runtime, outbound TCP 6697 (TLS) to `irc.warheatmap.app` and the EFnet servers. Port 6667 is used only as a last resort on EFnet.

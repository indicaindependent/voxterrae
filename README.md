# VoxTerrae

The door from the map to the room. A WarHeatMap.app-branded IRC client (Python / PySide6) hard-wired to two networks:

| Network | Servers | Mode |
|---|---|---|
| **HOME** `irc.warheatmap.app` | 6697, CA-verified TLS | IRCv3: history, reactions, replies, typing, read markers |
| **EFnet** | `irc.efnet.nl` 6697 (CA) → `irc.prison.net` / `irc.underworld.no` / `irc.choopa.net` 6697 (self-signed, pinned on first use) → `irc.prison.net` 6667 plaintext last resort | classic: five porch rooms, no client tags, no link previews |

## Run from source
```
pip install "PySide6-Essentials>=6.8" "qasync>=0.27"
set PYTHONPATH=src          # PowerShell: $env:PYTHONPATH="src"
python -m voxterrae.app --live yourhandle
python -m voxterrae.app --demo                      # fictional sample data, no network
python -m voxterrae.app --demo --shot out.png 1280x720
```

## Build the portable exe (Windows 11)
```
powershell -ExecutionPolicy Bypass -File build\build_win.ps1
```
Runs the unit tests, builds `dist\VoxTerrae.exe` (one file, no installer), prints its SHA-256, and writes a smoke render.

## Tests
`pytest tests/test_message.py tests/test_store.py` are offline. `tests/test_live_*.py` talk to the live networks (probe nick `vt-*`, room `#vt-m0-test`).

## Commands
`/search words` (local full-text, per network) · `/ask question` (Axiom, HOME rooms) · `/reply <msgid> text` · `/react <msgid> 🔥` · `/join #room` · `/me action` · right-click a message for Reply / React / Copy · Ctrl+click = 👍

Data lives in `%LOCALAPPDATA%\VoxTerrae\` (`voxterrae.db`, `tls_pins.json`). MIT licence; Qt under LGPLv3.

## Update check

Once per launch the client GETs `https://voxterrae.app/api/latest.json` (no identifiers, strict TLS, explicit user agent) and, if a newer version is listed, adds one system line to the HOME rooms and a note to the window title. It never downloads or installs anything. `VOXTERRAE_NO_UPDATE_CHECK=1` disables it; `VOXTERRAE_UPDATE_FEED=<url>` points it elsewhere (tests use a local server).

## Tests

`pytest` runs the offline suite (parser, store, update check) and SKIPS the live tests. The live tests connect to the real HOME network and to EFnet (a private throwaway room only, never a public channel) and are opt-in: `VOXTERRAE_LIVE_TESTS=1 pytest`. The `tests/*_proof.py` scripts and `tests/render_live.py` need the same variable.

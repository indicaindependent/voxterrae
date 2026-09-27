# VoxTerrae

The door from the map to the room. A WarHeatMap.app-branded IRC client (Python / PySide6) hard-wired to one network, EFnet, where `#warheatmap` is home:

| Network | Servers | Mode |
|---|---|---|
| **EFnet** | `irc.efnet.nl` 6697 (CA) → `irc.prison.net` / `irc.underworld.no` / `irc.choopa.net` 6697 (self-signed, pinned on first use) → `irc.prison.net` 6667 plaintext last resort | classic: auto-joins `#warheatmap` only (`/join` anything else), no client tags, no link previews |

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
`pytest tests/test_message.py tests/test_store.py` are offline. `tests/test_live_*.py` talk to the live networks (probe nick `vt-*`, a fresh throwaway room `#vt-<hex>` per run).

## Commands and keys
`/join` `/part` `/msg` `/me` `/search` (local full-text, per network) `/ask` (Axiom, in #warheatmap) `/reply` `/react` (need message ids; reserved for the VoxTerrae layer) `/topic` `/whois` `/nick` `/clear` `/help` `/raw`. Type `/` for the popup.
Ctrl+K quick switcher · Alt+Up/Down rooms · Alt+A next unread · Ctrl+1..9 jump · Ctrl+, settings · Ctrl+. rail · Ctrl+= / Ctrl+- text size · Tab completes nicks · Shift+Enter new line · hover or right-click a message for Reply / React / Copy · Ctrl+click = 👍. Full list: `docs/commands.md` on the hub.

## What 0.1.2 adds
Windows 11 polish and hardening: dark title bar matched to the theme, taskbar identity, single-instance guard, close-to-tray with a quit in the tray menu, crash dialog + rotating log in `%LOCALAPPDATA%\VoxTerrae\logs`, persisted splitter layout. Timeline: per-nick colours, clickable links, `/me` actions, folded join/leave lines, hover actions, unread separator, jump-to-latest, empty states, compact single-line mode. Composer: multi-line, history, Tab completion, command popup, byte counter. Rooms: collapsible networks, unread + mention pills, right-click menu. Members: rank badges, filter, live updates on join/part/quit/nick. Settings dialog (Ctrl+,), About, quick switcher (Ctrl+K), status bar with per-network lag, reconnect banner, private conversations from the members panel.

Data lives in `%LOCALAPPDATA%\VoxTerrae\` (`voxterrae.db`, `tls_pins.json`). MIT licence; Qt under LGPLv3.

## The VoxTerrae Layer (0.3.0)
A small metadata sidecar at `layer.voxterrae.app` that carries profiles, reactions, replies and presence for VoxTerrae users
over plain EFnet. It never stores message text: only a 12-hex hash per message (`sha256(room\nnick\nnormalized text\nminute)[:12]`),
reactions, reply links, pins and the profile you write. Nick verification is a one-time code over IRC from cablepair, signed
with a key that never leaves your machine. `/layer wipe` deletes everything held about you. Turn it off in Settings → Layer.

## Update check

Once per launch the client GETs `https://voxterrae.app/api/latest.json` (no identifiers, strict TLS, explicit user agent) and, if a newer version is listed, adds one system line to your rooms and a note to the window title. It never downloads or installs anything. `VOXTERRAE_NO_UPDATE_CHECK=1` disables it; `VOXTERRAE_UPDATE_FEED=<url>` points it elsewhere (tests use a local server).

## Tests

`pytest` runs the offline suite (parser, store, update check) and SKIPS the live tests. The live tests connect to the real EFnet (#warheatmap, or a private throwaway room; never another public channel) and are opt-in: `VOXTERRAE_LIVE_TESTS=1 pytest`. The `tests/*_proof.py` scripts and `tests/render_live.py` need the same variable.

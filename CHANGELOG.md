# Changelog

## 0.1.2 (unreleased)
Polish and hardening pass. No protocol changes; the local store format is unchanged.

**Windows 11 shell:** dark title bar and caption colours matched to the theme (DWM), explicit AppUserModelID for taskbar grouping, single-instance guard (a second launch raises the first window), close-to-tray with Quit in the tray menu and a one-time hint, crash guard writing `%LOCALAPPDATA%\VoxTerrae\logs\crash-*.log` and showing a dialog, rotating `voxterrae.log`, HiDPI pass-through rounding, persisted splitter sizes, 900x560 minimum.

**Timeline:** stable per-nick colours, clickable links with tooltips, `/me` action rows, folded join/leave/rename lines, hover Reply/React/Copy buttons, NEW MESSAGES separator, day dividers, jump-to-latest pill with a count, empty states per room kind, compact single-line layout (Settings), optional always-on timestamps, text size 14 to 22 px (Ctrl+= / Ctrl+-), BOT badge as a drawn tag.

**Composer:** multi-line box that grows to six lines (Shift+Enter), sent-message history (Up/Down), Tab completion for nicks and commands, `/` command popup, byte counter with a warning past 400 bytes, send button, disabled state while a network is down.

**Rooms and members:** collapsible network groups, unread and mention pills, kind icons (room / private / network), right-click Mark as read / Leave / Close, Alt+Up/Down and Ctrl+1..9 navigation, Alt+A next unread, Ctrl+K quick switcher. Members panel with rank badges, count and op count, filter box for large rooms, live updates on JOIN/PART/QUIT/KICK/NICK, double-click to mention, right-click Mention / Message / Whois / Copy.

**Commands:** `/msg` `/query` `/whois` `/topic` `/nick` `/clear` `/help`; whois replies and common errors (nick in use, no such nick, cannot send) appear as system lines in the current room; private conversations open as rail rows on incoming messages too.

**Status bar:** per-network state chip with measured PING round-trip in ms, TLS marker, version pill (About), update pill when a newer release is listed.

**Bridge fixes:** the connection line and your own nick are announced from the status loop (the 001 reply is consumed during connect and never reached the UI before), NAMES entries strip `!user@host` (userhost-in-names), history playback no longer creates presence lines or a second "joined" line, and the history summary counts messages rather than raw events.

**Rail:** the WarDesk card is hidden until real data is wired (0.1.1 showed sample copy on live connections); the map tile opens warheatmap.app.

## 0.1.1
The exe starts. `build/launcher.py` entry outside the package, absolute imports in `__main__.py`, release workflow smoke-runs the built exe before publishing.

## 0.1.0
Withdrawn: the frozen exe crashed at launch (relative import from a top-level script). Source release only.

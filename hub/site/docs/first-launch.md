---
title: First launch
summary: The Welcome screen, your handle, and what happens when you press ENTER.
order: 2
---
VoxTerrae opens on a single screen: a handle field and one button.

- **Handle** is the name others see. Letters, digits and `_-[]\`^{}|` are allowed; it cannot start with a digit. Leave it empty to use a sanitised version of your Windows username.
- **ENTER** connects to both networks at once. You land in **#warheatmap** on HOME, the only room the client ever joins for you. EFnet shows just its network buffer until you `/join #channel` yourself (`/part` to leave).

The room list is grouped by network. A header shows each network's state with a dot icon (`connected`, `connecting`, `reconnecting`); click it to collapse the group. Rooms show an unread count, and the pill turns green when someone mentioned you. The right rail has a tile that opens the live map in your browser and the members of the room you are viewing, with rank badges (owner, op, half-op, voice). The status bar at the bottom shows each network's state and, once measured, its round-trip lag in milliseconds.

**Windows 11 behaviour.** The title bar follows the dark theme. Closing the window keeps VoxTerrae running in the tray so you stay connected; right-click the tray icon to quit, or turn this off in Settings (Ctrl+,). Launching VoxTerrae a second time brings the running window to the front instead of opening another. Window size, splitter positions and settings are remembered. If anything crashes, a dialog points at the log in `%LOCALAPPDATA%\VoxTerrae\logs`.

If HOME cannot be reached, EFnet still works, and the other way round. Reconnection is automatic with backoff; an amber banner above the timeline tells you while a network is down, and a system line appears when a room rejoins.

---
title: First launch
summary: The Welcome screen, your handle, and what happens when you press ENTER.
order: 2
---
VoxTerrae opens on a single screen: a handle field and one button.

- **Handle** is the name others see. Letters, digits and `_-[]\`^{}|` are allowed; it cannot start with a digit. Leave it empty to use a sanitised version of your Windows username.
- **ENTER** connects to both networks at once. You land in **#warheatmap** on HOME, the only room the client ever joins for you. EFnet shows just its network buffer until you `/join #channel` yourself (`/part` to leave).

The room list is grouped by network. A header shows each network's state with a dot icon (`connected`, `connecting`, `reconnecting`). The right rail shows the live-map card and the members of the room you are viewing.

If HOME cannot be reached, EFnet still works, and the other way round. Reconnection is automatic with backoff; you will see a system line when a room rejoins.

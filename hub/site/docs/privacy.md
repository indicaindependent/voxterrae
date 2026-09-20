---
title: Privacy
summary: What the client stores, what this site stores, and what leaves your machine.
order: 6
---
## The client
Stored locally in `%LOCALAPPDATA%\VoxTerrae\`: your message history (`voxterrae.db`), pinned EFnet certificate fingerprints (`tls_pins.json`), your handle and window geometry. Nothing is uploaded anywhere except the IRC traffic you send to the networks you are connected to.

IRC is a public medium. Your messages in a channel are visible to everyone in it and, on HOME, kept in server history so people can catch up. Your IP address is visible to the IRC servers you connect to (HOME cloaks hostnames; EFnet servers vary).

The update check fetches `/api/latest.json` from this site once per launch: a plain GET with no identifiers, sent with a `VoxTerrae/<version>` user agent over strict TLS. If a newer version exists you get one system line in your HOME rooms and a note in the window title; nothing is downloaded or installed for you. Set `VOXTERRAE_NO_UPDATE_CHECK=1` to turn it off, or `VOXTERRAE_UPDATE_FEED` to point it at your own feed.

## This site
No cookies, no trackers, no third-party scripts, no external fonts. Cloudflare serves the pages and terminates TLS; its standard edge logs apply. We do not run analytics.

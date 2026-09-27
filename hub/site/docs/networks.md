---
title: EFnet and #warheatmap
summary: Since 0.2.0 VoxTerrae lives on one network. What that means, and what the client does about certificates.
order: 3
---
## One network: EFnet
Since **0.2.0** VoxTerrae connects to exactly one IRC network, **EFnet**, and joins exactly one room for you: **#warheatmap**. That room is home. Everything else is a `/join` away, and `/part` leaves it again.

The project-run HOME network (`irc.warheatmap.app`) was retired on 2026-09-26. Older clients (0.1.x) still try to reach it and will show it as unreachable; update to 0.2.0 or later.

## Classic IRC, modern client
EFnet is the 1990 original: no services, no accounts, no server-side history and no message ids. VoxTerrae keeps what it can do locally: your own scrollback and full-text search are stored on your machine, notifications, mentions and unread counts work as you expect, and links are clickable. Reactions and replies by id are not possible on plain EFnet; use **Quote**. A VoxTerrae-to-VoxTerrae layer that adds profiles, reactions and replies between people who both run the client (invisible to everyone else) is in design; see the release notes when it lands.

## Certificates
Most EFnet servers present **self-signed** TLS certificates. VoxTerrae handles this with **trust on first use**: the first time it meets a server it records the certificate's SHA-256 fingerprint in `tls_pins.json`; if the fingerprint ever changes it refuses to connect and tells you. `irc.efnet.nl` has a public CA certificate and is tried first. Plaintext on 6667 is the very last fallback and is labelled as such in the network buffer.

## CTCP
EFnet's drone monitors send a `CTCP VERSION` request to every new client. Ignoring it is how clients get banned. VoxTerrae answers VERSION, PING and CLIENTINFO automatically and logs the exchange in the network buffer instead of opening a message window.

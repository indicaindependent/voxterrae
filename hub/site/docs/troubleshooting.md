---
title: Troubleshooting
summary: SmartScreen, pinned certificates, EFnet quirks, and where the logs are.
order: 7
---
**"Windows protected your PC"** — SmartScreen has not seen this build before. Verify the SHA-256 ([how](/docs/verify)), then More info → Run anyway.

**"certificate fingerprint changed" on EFnet** — the server you connected to presented a different self-signed certificate than the one pinned on first use. Servers do rotate certificates, but this is also what an interception would look like. If you trust the change, delete that server's line from `tls_pins.json` and reconnect.

**EFnet rooms empty or "K-lined"** — EFnet servers ban aggressively. The client answers CTCP VERSION to stay in good standing; if you were banned anyway, the pool moves to the next server automatically.

**No reactions on EFnet** — expected: EFnet has no message ids. Use Quote.

**History looks doubled** — it should never be; every line is stored once by (network, room, id). If you see duplicates, please report it with the room name.

**Logs** — system lines for each network live in its `*server*` buffer. There is no separate log file in 0.1.

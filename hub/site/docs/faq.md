---
title: FAQ
summary: Short answers.
order: 8
---
**Is it free?** Yes. MIT licence, no accounts, no telemetry.

**Why IRC in 2026?** Because it is open, federated, scriptable and forty years old. HOME adds the modern layer (history, reactions, replies) through IRCv3 without giving up any of that.

**Can I use another IRC client on HOME?** Yes: `irc.warheatmap.app`, port 6697, TLS. Anything that speaks IRCv3 gets history and reactions; anything older still works.

**Where is the source?** Linked from [download](/download). GitHub publishing is in progress.

**Who is Axiom?** The room assistant on HOME. `/ask` sends it a question in the current room.

**macOS / Linux?** Runs from source today. Packaged builds are not scheduled yet.

## How do updates work?

On launch the client reads this site's `/api/latest.json` (the same feed the [download page](/download) is built from). If a newer version is published you see one system line in your HOME rooms and the window title says so. It never downloads or installs anything: you fetch the new build from the download page and check its SHA-256 as described in [Verify a download](/docs/verify). Turn it off with `VOXTERRAE_NO_UPDATE_CHECK=1`.

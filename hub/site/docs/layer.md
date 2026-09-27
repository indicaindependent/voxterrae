---
title: The VoxTerrae Layer
---
# The VoxTerrae Layer

Plain EFnet has no reactions, no threads, no profiles. VoxTerrae 0.3.0 adds them for people using VoxTerrae, on top of
ordinary IRC, without running a chat server: a small service at `layer.voxterrae.app` holds metadata only.

## What it does
- **Profile card**: display name, pronouns, bio, time zone, links, badges. `/profile nick` shows one, `/profile edit` writes yours.
- **Reactions** on any message, **replies with context** (a short `> <nick> quote…` line also goes to IRC so everyone follows),
  **who else is here with VoxTerrae**, typing indicators.
- **Images**: `/upload C:\path\photo.png` posts a link that lives 30 days. Anyone can report an image; room ops can take it down.

## What leaves your computer, and what never does
Leaves: your nick, a 12-character hash of each message you send (room, nick, normalized text, minute; never the text),
your reactions, the profile you write, images you upload. Never: message text, private messages, your key.

## How your nick is verified
Once per session the layer asks cablepair (the bot in #warheatmap) to send you a one-time code over IRC. VoxTerrae signs it
with a key made on your machine (`layer_key` in the profile folder) and gets a 24-hour token. No account, no email, no password.
A profile card says "verified 3 min ago" so you know how fresh a claim is; EFnet has no nick ownership, so this is the honest ceiling.

## Turning it off, erasing everything
Settings → Layer unticks it; `/layer off` for one session; `/layer wipe` deletes every record tied to your key and the key itself.

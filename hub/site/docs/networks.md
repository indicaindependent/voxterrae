---
title: HOME and EFnet
summary: Why the two networks look different, and what the client does about certificates.
order: 3
---
## HOME · irc.warheatmap.app
Our own IRCv3 server (Ergo). It supports the modern features: server-side history, reactions, replies, typing indicators, read markers, multi-line messages, message ids. TLS on 6697 with a public CA certificate; the client refuses anything else.

## EFnet
A 1990s network with no services and no message ids. Reactions and replies are not possible there, so the client switches to **classic mode**: plain lines, `/me`, quoting instead of replying. No rooms are joined automatically on EFnet: use `/join #room` for anything you want to be in.

Most EFnet servers present **self-signed** TLS certificates. VoxTerrae handles this with **trust on first use**: the first time it meets a server it records the certificate's SHA-256 fingerprint in `tls_pins.json`; if the fingerprint ever changes it refuses to connect and tells you. `irc.efnet.nl` has a public CA certificate and is tried first. Plaintext on 6667 is the very last fallback and is labelled as such in the network buffer.

## CTCP
EFnet's drone monitors send a `CTCP VERSION` request to every new client. Ignoring it is how clients get banned. VoxTerrae answers VERSION, PING and CLIENTINFO automatically and logs the exchange in the network buffer instead of opening a message window.

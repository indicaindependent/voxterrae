"""Built-in networks. VoxTerrae is hard-wired to two: HOME (irc.warheatmap.app) and EFnet.
Both connect at launch. Everything here is public information (hostnames, channels)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass(frozen=True)
class Server:
    host: str
    port: int = 6697
    tls: bool = True
    tls_verify: str = "strict"   # "strict" | "tofu"

@dataclass(frozen=True)
class Network:
    key: str                     # short id used in room keys: "home", "efnet"
    name: str                    # display
    servers: List[Server]        # tried in order; the first that completes registration wins
    autojoin: List[str]
    home_channel: str
    ircv3: bool                  # request draft/* extras and send client-only tags
    link_previews: bool          # fetch OpenGraph previews (never on EFnet: IP leak to arbitrary URLs)
    sasl: bool                   # offer SASL when an account is configured
    nick_suffix: str = ""        # appended to the handle to avoid collisions on big networks
    blurb: str = ""

HOME = Network(
    key="home", name="HOME · warheatmap", ircv3=True, link_previews=True, sasl=True,
    servers=[Server("irc.warheatmap.app", 6697, True, "strict")],
    autojoin=["#warheatmap"], home_channel="#warheatmap",
    blurb="The WarHeatMap community network (Ergo, IRCv3). History, reactions, read markers.",
)
# Measured Sep 20 2026 from the sandbox: irc.efnet.nl presents a CA-signed cert on 6697; prison.net,
# underworld.no, choopa.net and irc.efnet.org present SELF-SIGNED certs on 6697 (so: tofu pinning), and
# prison.net also answers plaintext 6667 (kept last, plaintext is the last resort, never the default).
EFNET = Network(
    key="efnet", name="EFnet", ircv3=False, link_previews=False, sasl=False, nick_suffix="",
    servers=[
        Server("irc.efnet.nl", 6697, True, "strict"),
        Server("irc.prison.net", 6697, True, "tofu"),
        Server("irc.underworld.no", 6697, True, "tofu"),
        Server("irc.choopa.net", 6697, True, "tofu"),
        Server("irc.prison.net", 6667, False, "strict"),
    ],
    autojoin=["#phpnuke", "#wk", "#OGhomecoming", "#ComebacktoIRC", "#VetsHateDiscord"],
    home_channel="#phpnuke",
    blurb="The 1990 original. No services, no history: what you see is what was said while you were here.",
)
BUILTIN: List[Network] = [HOME, EFNET]

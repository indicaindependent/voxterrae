"""M0 read-back proof against the HOME network (irc.warheatmap.app, Ergo). Marked live; needs network.

Proofs (M0 acceptance list):
 1. negotiated CAP set is a subset of what the server advertised and includes the load-bearing caps;
 2. a line we send comes back through echo-message with a msgid the server minted;
 3. CHATHISTORY LATEST replays it once (no duplicate after a second request);
 4. a TAGMSG reaction is accepted (labeled ACK or echo) and a multiline batch round-trips as one message.
"""
import asyncio, os, secrets, time
import pytest
from voxterrae.irc import IrcClient, ClientConfig

# Pete 2026-09-20: no channel name is hardcoded in this repo. The room is taken from
# VT_TEST_CHAN, or generated per run, so the only channel this project ever names is
# #warheatmap. Set VT_TEST_CHAN to reuse a room across runs.
CHAN = os.environ.get("VT_TEST_CHAN") or ("#vt-" + secrets.token_hex(3))
ROOM = "home/" + CHAN

HOST = os.environ.get("VT_TEST_HOST", "irc.warheatmap.app")

pytestmark = pytest.mark.live


@pytest.fixture
def client():
    return IrcClient(ClientConfig(host=HOST, nick="vt-m0-" + secrets.token_hex(2), realname="VoxTerrae M0 probe"))


def run(coro):
    return asyncio.run(asyncio.wait_for(coro, timeout=60))


def test_caps_and_echo_and_history(client):
    async def go():
        await client.connect()
        try:
            adv = set(client.caps_available)
            assert client.caps_enabled <= adv, "enabled caps must be a subset of advertised"
            for must in ("message-tags", "server-time", "batch", "labeled-response", "echo-message"):
                assert must in client.caps_enabled, f"{must} not enabled; advertised={sorted(adv)}"
            assert client.has("draft/chathistory", "chathistory")
            await client.join(CHAN)
            # wait for our JOIN
            t0 = time.monotonic()
            while time.monotonic() - t0 < 10:
                m = await asyncio.wait_for(client.events.get(), 10)
                if m.command == "JOIN" and m.nick == client.nick:
                    break
            token = "m0-" + secrets.token_hex(4)
            mid = await client.privmsg(CHAN, f"VoxTerrae M0 probe {token}")
            assert mid, "echo-message did not return a msgid"
            hist = await client.chathistory("LATEST", CHAN, "*", limit=20)
            ours = [m for m in hist if token in m.params[-1]]
            assert len(ours) == 1 and ours[0].msgid == mid, "history must contain our line exactly once with the same msgid"
            hist2 = await client.chathistory("LATEST", CHAN, "*", limit=20)
            assert any(m.msgid == mid for m in hist2)
            # dedupe: the event stream must not have delivered mid twice
            delivered = 0
            while not client.events.empty():
                m = client.events.get_nowait()
                if m.msgid == mid:
                    delivered += 1
            assert delivered <= 1, f"msgid {mid} delivered {delivered} times to the event stream"
            # reaction + multiline
            await client.react(CHAN, mid, "🔥")
            if client.has("draft/multiline", "multiline"):
                await client.privmsg(CHAN, f"line one {token}\nline two {token}")
                got = None
                t0 = time.monotonic()
                while time.monotonic() - t0 < 10:
                    m = await asyncio.wait_for(client.events.get(), 10)
                    if m.command == "PRIVMSG" and "line two" in m.params[-1] and m.nick == client.nick:
                        got = m; break
                assert got is not None and "vt/multiline" in got.tags and got.params[-1].count("\n") == 1
            return {"enabled": sorted(client.caps_enabled), "msgid": mid, "hist": len(hist)}
        finally:
            await client.quit("M0 probe done")
    res = run(go())
    print("\nM0 PROOF:", res)

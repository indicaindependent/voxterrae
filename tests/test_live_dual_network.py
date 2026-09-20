"""Live proof: HOME and EFnet connected simultaneously from one process via NetworkSession.
Proofs: both register; HOME negotiates IRCv3 (message-tags) and EFnet does not; we JOIN a private throwaway room on
EFnet (never a public one) and see our own NAMES there; client tags are never sent on EFnet; a HOME message echoes.
Opt-in: VOXTERRAE_LIVE_TESTS=1 (see conftest.py). The EFnet session used here has NO autojoin so the test never
enters anyone else's channel."""
import asyncio, secrets, time, os
from dataclasses import replace
import pytest
from voxterrae.irc.networks import HOME, EFNET
from voxterrae.irc.session import NetworkSession
pytestmark = pytest.mark.live

def test_dual_network():
    async def go():
        seen = {"home": [], "efnet": []}
        def on_event(sess, m): seen[sess.net.key].append(m)
        handle = "vt" + secrets.token_hex(3)
        pins = {}
        efnet_quiet = replace(EFNET, autojoin=[])     # no public rooms: the test owns its own throwaway channel
        room = "#vt-test-" + secrets.token_hex(3)
        home = NetworkSession(HOME, handle, pins, on_event); ef = NetworkSession(efnet_quiet, handle, pins, on_event)
        home.start(); ef.start()
        t0 = time.monotonic()
        while time.monotonic() - t0 < 45 and not (home.state == "connected" and ef.state == "connected"):
            await asyncio.sleep(0.5)
        try:
            assert home.state == "connected", f"HOME state {home.state}"
            assert ef.state == "connected", f"EFnet state {ef.state}"
            hc, ec = home.client, ef.client
            assert "message-tags" in hc.caps_enabled and hc.has("draft/chathistory", "chathistory")
            assert "message-tags" not in ec.caps_enabled and not ec.cfg.client_tags
            # EFnet: join our own empty room and read NAMES back (353) -- proves JOIN + NAMES parsing without touching a public channel
            await ec.join(room)
            names = []
            t1 = time.monotonic()
            while time.monotonic() - t1 < 25:
                for m in seen["efnet"]:
                    if m.command == "353" and m.params[-2].lower() == room.lower():
                        names += m.params[-1].split()
                if names: break
                await asyncio.sleep(0.5)
            assert any(n.lstrip("@%+~&").lower() == handle.lower() for n in names), f"our nick missing from NAMES {room}: {names}"
            # client tags must be a no-op on EFnet (sent into our own room only)
            await ec.react(room, "nonexistent", "🔥"); await ec.typing(room)
            # HOME echo in the test room
            await hc.join("#vt-m0-test"); await asyncio.sleep(1.0)
            mid = await hc.privmsg("#vt-m0-test", f"dual-network probe {handle}")
            assert mid
            return {"home_server": home.server_used, "efnet_server": ef.server_used, "efnet_caps": sorted(ec.caps_enabled),
                    "efnet_pins": pins, "efnet_room": room, "efnet_names": names, "home_msgid": mid, "efnet_events": len(seen["efnet"]), "home_events": len(seen["home"])}
        finally:
            await home.stop(); await ef.stop()
    res = asyncio.run(asyncio.wait_for(go(), timeout=120))
    print("\nDUAL PROOF:", res)

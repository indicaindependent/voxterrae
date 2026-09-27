"""LIVE proof of the VoxTerrae Layer end to end on real EFnet (VOXTERRAE_LIVE_TESTS=1 to run; never in CI).
A full VoxTerrae (window + bridge) verifies its nick through cablepair's NOTICE, joins a throwaway room, says a line;
a second, independent layer identity (plain IrcClient + LayerClient) reacts to it and posts a quote-line reply.
Passes when the first client's timeline shows the reaction and the reply context, both delivered by the layer."""
import os, sys
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1": sys.exit("live proof: set VOXTERRAE_LIVE_TESTS=1")
import asyncio, secrets, tempfile, time
os.environ["QT_QPA_PLATFORM"] = "offscreen"; os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="vt_a_")
sys.path.insert(0, os.path.dirname(__file__))
from _room import throwaway_room
from PySide6.QtWidgets import QApplication
import qasync
from voxterrae.app.main_window import MainWindow
from voxterrae.app.bridge import Bridge
from voxterrae.app.layer import LayerClient, quote_line
from voxterrae.irc.client import IrcClient, ClientConfig

ROOM = throwaway_room(); A = "vtla" + secrets.token_hex(2); B = "vtlb" + secrets.token_hex(2); token = secrets.token_hex(2)
app = QApplication([]); loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
win = MainWindow("darkops"); win.prefs.layer_enabled = True; win.stack.setCurrentWidget(win.chat); win.show(); br = Bridge(win, A)
out = {}
async def drive():
    br.start()
    try:
        for _ in range(120):
            await asyncio.sleep(0.5)
            if all(s.state == "connected" for s in br.sessions.values()) and br.sessions: break
        for _ in range(200):   # wait for the bridge's own claim (NOTICE from cablepair -> token)
            await asyncio.sleep(0.5)
            if br.layer.ready: break
        out["a_verified"] = br.layer.ready; assert br.layer.ready, "A never verified: " + br.layer.last_error
        s = br.sessions["efnet"]; await s.client.join(ROOM); await asyncio.sleep(2); key = "efnet/" + ROOM; win.show_room(key)
        await asyncio.sleep(2); out["a_ws_room"] = br.layer._ws_room
        # ---- peer B: its own key, its own claim, plain IrcClient
        os.environ["LOCALAPPDATA"] = tempfile.mkdtemp(prefix="vt_b_"); lb = LayerClient(os.environ["LOCALAPPDATA"])
        cb = IrcClient(ClientConfig(host="irc.underworld.no", nick=B, tls_verify="tofu")); seen = []
        cb.on(lambda m: (lb.feed_notice(m.params[-1]) if getattr(m, "command", "") == "NOTICE" else None, seen.append(m) if getattr(m, "command", "") == "PRIVMSG" else None))
        await cb.connect(); await asyncio.sleep(2); await cb.join(ROOM); await asyncio.sleep(1.5)
        out["b_verified"] = await lb.claim(B); assert out["b_verified"], "B claim failed: " + lb.last_error
        br._on_send(key, f"layer proof line {token}"); await asyncio.sleep(3)
        it = next(x for x in win.models[key].items if x.kind == "msg" and token in x.text); out["a_vid"] = br.layer.vid_of(ROOM, it.msgid)
        # B registers A's line as it saw it, then reacts + replies through the layer
        pm = next(m for m in seen if token in m.params[-1]); ts = time.time()
        b_mid = "B-" + pm.params[-1][:8]; lb.register(ROOM, A, pm.params[-1], ts, b_mid)
        out["vid_match"] = lb.vid_of(ROOM, b_mid) in (out["a_vid"],) or out["a_vid"] in lb.vidmap[ROOM.lower()]
        out["b_react"] = await lb.react(ROOM, b_mid, "🔥")
        reply_text = f"reply from B {token}"; await cb.privmsg(ROOM, quote_line(A, pm.params[-1])); await asyncio.sleep(0.3); await cb.privmsg(ROOM, reply_text)
        rid = "B-reply"; lb.register(ROOM, B, reply_text, time.time(), rid, mine=True); await asyncio.sleep(0.5)
        out["b_link"] = await lb.link_reply(ROOM, rid, b_mid)
        for _ in range(30):
            await asyncio.sleep(0.5)
            rep = next((x for x in win.models[key].items if x.kind == "msg" and x.nick == B and reply_text in x.text), None)
            if it.reactions.get("🔥") and rep and rep.reply_to_nick: break
        out["a_sees_reaction"] = dict(it.reactions); out["a_sees_reply_context"] = bool(rep and rep.reply_to_nick == A)
        out["a_sees_quote_line"] = any(x.kind == "msg" and x.text.startswith(f"> <{A}>") for x in win.models[key].items)
        prof_ok = await lb.put_profile({"display_name": "Peer B", "bio": "proof"}); pa = await br.layer.get_profile(B)
        out["profile_roundtrip"] = bool(prof_ok and pa and pa.get("display_name") == "Peer B")
        out["b_wipe"] = await lb.wipe(); await cb.quit()
    except Exception as e:
        import traceback; out["FAILED"] = repr(e); out["where"] = traceback.format_exc().splitlines()[-3][:160]
    finally:
        print("LAYER PROOF:", out); await br.layer.unwatch(); await br.stop(); app.quit()
with loop: loop.run_until_complete(drive())

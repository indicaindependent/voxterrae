"""Render the REAL app on REAL connections (HOME + EFnet) for the hub screenshots. Offscreen Qt.
   python tests/render_live.py renders/vt_LIVE_dual_1280x720.png renders/vt_M3_replymode_1280x720.png"""
import os, sys
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1":
    sys.exit("live proof: connects to real IRC networks; set VOXTERRAE_LIVE_TESTS=1 to run")
import asyncio, secrets, sys
from PySide6.QtWidgets import QApplication
import qasync
from voxterrae.app.main_window import MainWindow
from voxterrae.app.bridge import Bridge
from voxterrae.irc import IrcClient, ClientConfig
from voxterrae.irc.networks import HOME, EFNET

# Pete 2026-09-20: no channel name is hardcoded in this repo. The room is taken from
# VT_TEST_CHAN, or generated per run, so the only channel this project ever names is
# #warheatmap. Set VT_TEST_CHAN to reuse a room across runs.
CHAN = os.environ.get("VT_TEST_CHAN") or ("#vt-" + secrets.token_hex(3))
ROOM = "home/" + CHAN
out_live, out_reply = sys.argv[1], sys.argv[2]
handle = "vtrender" + secrets.token_hex(1); token = secrets.token_hex(2)
app = QApplication([]); loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
win = MainWindow(); win.resize(1280, 720); win.stack.setCurrentWidget(win.chat); win.show(); br = Bridge(win, handle, [HOME, EFNET])
async def run():
    br.start()
    for _ in range(90):
        await asyncio.sleep(0.5)
        if all(s.state == "connected" for s in br.sessions.values()): break
    await asyncio.sleep(6); win.show_room("home/#warheatmap"); app.processEvents(); win.grab().save(out_live)
    # reply-mode shot in the probe room: a peer posts, mentions us; we reply + react; reply strip open on the last line
    await br.sessions["home"].client.join(CHAN); await asyncio.sleep(2); win.show_room(ROOM)
    other = IrcClient(ClientConfig(host="irc.warheatmap.app", nick="cartographer" + secrets.token_hex(1))); await other.connect(); await other.join(CHAN); await asyncio.sleep(1.5)
    await other.privmsg(CHAN, "new event card up for the Hormuz lane, anyone watching the tanker count tonight?"); await asyncio.sleep(1)
    pmid = await other.privmsg(CHAN, f"{handle} the map shows 3 transits since 18:00, does the desk brief agree? {token}"); await asyncio.sleep(2)
    items = [i for i in win.models[ROOM].items if i.kind == "msg" and token in i.text]
    win.set_reply(items[0]); win.composer.setText("checking the 20:00 brief now, it counted 4 with one turnaround"); win._send(); await asyncio.sleep(2)
    win.send_react.emit(ROOM, items[0].msgid, "👀"); await asyncio.sleep(1.5)
    await other.privmsg(CHAN, "that turnaround is the one the OSINT thread flagged, good catch"); await asyncio.sleep(1.5)
    last = [i for i in win.models[ROOM].items if i.kind == "msg"][-1]
    win.set_reply(last); win.composer.setText("pinning it to the room with /ask"); app.processEvents(); win.grab().save(out_reply)
    print("RENDER:", {"title": win.windowTitle(), "nets": {k: s.state for k, s in br.sessions.items()}, "rooms": win.rooms.count() if hasattr(win.rooms, 'count') else 'n/a', "reactions": items[0].reactions})
    await other.quit(); await br.stop(); app.quit()
with loop:
    loop.create_task(run()); loop.run_forever()

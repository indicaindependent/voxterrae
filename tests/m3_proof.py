"""M3 proof: real app, HOME; a second raw client mentions us -> notify() fires (tray badge / title); typing + read marker sent; reply + react round-trip."""
import os, sys
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1":
    sys.exit("live proof: connects to real IRC networks; set VOXTERRAE_LIVE_TESTS=1 to run")
import asyncio, secrets, sys
from PySide6.QtWidgets import QApplication
import qasync
from voxterrae.app.main_window import MainWindow
from voxterrae.app.bridge import Bridge
from voxterrae.irc import IrcClient, ClientConfig
from voxterrae.irc.networks import HOME
from _room import throwaway_room
ROOM = throwaway_room()
handle = "vtm3" + secrets.token_hex(2); token = secrets.token_hex(3)
app = QApplication([]); loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
win = MainWindow(); win.stack.setCurrentWidget(win.chat); win.show(); br = Bridge(win, handle, [HOME])
async def run():
    br.start()
    for _ in range(60):
        await asyncio.sleep(0.5)
        if br.sessions["home"].state == "connected": break
    await asyncio.sleep(3); await br.sessions["home"].client.join(ROOM); await asyncio.sleep(2)
    win.show_room("home/"+ROOM)
    other = IrcClient(ClientConfig(host="irc.warheatmap.app", nick="vtpeer" + secrets.token_hex(2))); await other.connect(); await other.join(ROOM); await asyncio.sleep(1.5)
    # typing from us
    win.composer.setText("x"); win.composer.textEdited.emit("x"); await asyncio.sleep(1)
    # peer mentions us -> our window is not "active" offscreen, so notify() must fire
    win.show_room("home/#warheatmap")   # look elsewhere so the mention arrives in a room that is NOT on screen
    pmid = await other.privmsg(ROOM, f"hey {handle} look at this {token}"); await asyncio.sleep(2.5)
    notified = (win.unread_total, win.windowTitle(), win.rooms._unread.get("home/"+ROOM))
    win.show_room("home/"+ROOM)
    # we reply + react through the UI signals
    items = [i for i in win.models["home/"+ROOM].items if i.kind == "msg" and token in i.text]
    assert items and items[0].highlight, f"mention not highlighted: {[(i.nick, i.text) for i in win.models['home/'+ROOM].items if i.kind=='msg'][-3:]}"
    win.set_reply(items[0]); win.composer.setText(f"got it {token}"); win._send(); await asyncio.sleep(2.5)
    win.send_react.emit("home/"+ROOM, items[0].msgid, "🔥"); await asyncio.sleep(2)
    msgs = [i for i in win.models["home/"+ROOM].items if i.kind == "msg"]
    mine = [i for i in msgs if i.is_me and f"got it {token}" in i.text]
    print("M3 PROOF:", {"notify(unread,title,room_badge)": notified, "after_switch_title": win.windowTitle(), "mention_msgid": pmid,
          "reply_shown_with_context": bool(mine and mine[0].reply_to_nick == other.nick), "reactions_on_parent": items[0].reactions,
          "store_reactions": br.store.reactions("home", ROOM, pmid), "read_marker": br.store.read_marker("home", ROOM) is not None,
          "tray": bool(win.tray)})
    await other.quit(); await br.stop(); app.quit()
with loop:
    loop.create_task(run()); loop.run_forever()

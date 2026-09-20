"""0.1.2 live proof (opt-in): a peer joins the throwaway room (presence fold + member list grows), sends a DM (rail row
opens, notify fires), changes nick (member list renames), parts (member list shrinks). Real HOME network."""
import os, sys, asyncio, secrets
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1": sys.exit("set VOXTERRAE_LIVE_TESTS=1")
sys.path.insert(0, "tests"); sys.path.insert(0, "src")
from PySide6.QtWidgets import QApplication; import qasync
from voxterrae.app.main_window import MainWindow; from voxterrae.app.bridge import Bridge
from voxterrae.irc import IrcClient, ClientConfig; from voxterrae.irc.networks import HOME
from _room import throwaway_room
ROOM = throwaway_room(); handle = "vt012p" + secrets.token_hex(1); peer = "peer" + secrets.token_hex(2); tok = secrets.token_hex(2)
app = QApplication([]); loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
win = MainWindow(); win.stack.setCurrentWidget(win.chat); win.show(); br = Bridge(win, handle, [HOME]); out = {}
async def run():
    br.start()
    for _ in range(60):
        await asyncio.sleep(0.5)
        if br.sessions["home"].state == "connected": break
    await asyncio.sleep(2); await br.sessions["home"].client.join(ROOM); await asyncio.sleep(2); win.show_room("home/" + ROOM)
    other = IrcClient(ClientConfig(host="irc.warheatmap.app", nick=peer)); await other.connect(); await other.join(ROOM); await asyncio.sleep(2)
    key = "home/" + ROOM; out["members_after_join"] = sorted(win.rail.members.nicks()); out["presence_line"] = [i.text for i in win.models[key].items if i.sub == "presence"]
    await other.privmsg(handle, f"psst {tok}"); await asyncio.sleep(2)
    out["dm_room_in_rail"] = f"home/{peer}" in win.rooms.keys(); out["dm_text_ok"] = any(tok in i.text for i in win.models.get(f"home/{peer}", type("m", (), {"items": []})).items)
    out["unread_total_after_dm"] = win.unread_total
    await other.send_raw(f"NICK {peer}x"); await asyncio.sleep(2); out["members_after_nick"] = sorted(win.rail.members.nicks())
    await other.send_raw(f"PART {ROOM}"); await asyncio.sleep(2); out["members_after_part"] = sorted(win.rail.members.nicks()); out["presence_fold"] = [i.text for i in win.models[key].items if i.sub == "presence"]
    out["meta"] = win.meta.text()
    await other.quit(); await br.stop(); print("P012 PROOF:", out); app.quit()
with loop:
    loop.create_task(run()); loop.run_forever()

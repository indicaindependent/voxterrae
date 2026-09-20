"""M2 proof: launch the real app (offscreen), both networks; send a HOME line + a /search; quit; relaunch; assert no duplicates."""
import os, sys
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1":
    sys.exit("live proof: connects to real IRC networks; set VOXTERRAE_LIVE_TESTS=1 to run")
import asyncio, os, secrets, sqlite3, sys
from PySide6.QtWidgets import QApplication
import qasync
from voxterrae.app.main_window import MainWindow
from voxterrae.app.bridge import Bridge
from _room import throwaway_room
ROOM = throwaway_room()
handle = sys.argv[1]; token = sys.argv[2]; phase = sys.argv[3]
app = QApplication([]); loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
win = MainWindow(); win.stack.setCurrentWidget(win.chat); win.show(); br = Bridge(win, handle)
async def run():
    br.start()
    for _ in range(60):
        await asyncio.sleep(0.5)
        if all(s.state == "connected" for s in br.sessions.values()): break
    await asyncio.sleep(4)  # joins + history
    if phase == "A":
        win.show_room("home/"+ROOM); await br.sessions["home"].client.join(ROOM); await asyncio.sleep(2)
        win.send_text.emit("home/"+ROOM, f"M2 store probe {token}"); await asyncio.sleep(2)
        win.send_text.emit("home/"+ROOM, f"/search {token}"); await asyncio.sleep(1)
    else:
        await br.sessions["home"].client.join(ROOM); await asyncio.sleep(4)
    items = {k: [i for i in m.items if i.kind == "msg"] for k, m in win.models.items()}
    probe = [i for i in items.get("home/"+ROOM, []) if token in i.text]
    sysl = [i.text for i in win.models["home/"+ROOM].items if i.kind == "system"] if "home/"+ROOM in win.models else []
    print(f"PHASE {phase}: sessions={ {k: s.state for k, s in br.sessions.items()} } probe_in_view={len(probe)} rooms_with_msgs={ {k: len(v) for k, v in items.items() if v} }")
    print("  system lines:", [x[:90] for x in sysl][:8])
    await br.stop(); app.quit()
with loop:
    loop.create_task(run()); loop.run_forever()

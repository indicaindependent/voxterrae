"""Render the REAL app on REAL connections (EFnet) for the hub screenshots. Offscreen Qt.
   python tests/render_live.py out_live.png   (local proofs only; the repo ships demo renders, which contain no real users)"""
import os, sys
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1":
    sys.exit("live proof: connects to real IRC networks; set VOXTERRAE_LIVE_TESTS=1 to run")
import asyncio, secrets, sys
from PySide6.QtWidgets import QApplication
import qasync
from voxterrae.app.main_window import MainWindow
from voxterrae.app.bridge import Bridge
from voxterrae.irc import IrcClient, ClientConfig
from voxterrae.irc.networks import EFNET


out_live = sys.argv[1]
handle = "vtrender" + secrets.token_hex(1); token = secrets.token_hex(2)
app = QApplication([]); loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
win = MainWindow(); win.resize(1280, 720); win.stack.setCurrentWidget(win.chat); win.show(); br = Bridge(win, handle, [EFNET])
async def run():
    br.start()
    for _ in range(90):
        await asyncio.sleep(0.5)
        if all(s.state == "connected" for s in br.sessions.values()): break
    await asyncio.sleep(6); win.show_room("efnet/#warheatmap"); app.processEvents(); win.grab().save(out_live)
    # (0.2.0) the reply/react shot needed the retired IRCv3 HOME network; plain EFnet has no message ids, so only the live room shot is rendered

    print("RENDER:", {"title": win.windowTitle(), "nets": {k: s.state for k, s in br.sessions.items()}, "rooms": win.rooms.count() if hasattr(win.rooms, "count") else "n/a"})
    await br.stop(); app.quit()
with loop:
    loop.create_task(run()); loop.run_forever()

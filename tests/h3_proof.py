"""H3 proof: the REAL app on the REAL HOME network. Run A: staged feed says 0.1.1 -> system line in HOME rooms + title. Run B: real hub feed -> current, title untouched."""
import os, sys
if os.environ.get("VOXTERRAE_LIVE_TESTS") != "1":
    sys.exit("live proof: connects to real IRC networks; set VOXTERRAE_LIVE_TESTS=1 to run")
import asyncio, json, os, secrets, sys, threading, http.server
from PySide6.QtWidgets import QApplication
import qasync
from voxterrae.app.main_window import MainWindow
from voxterrae.app.bridge import Bridge
from voxterrae.app.updates import check_async, FEED_URL
from voxterrae.irc.networks import HOME
staged = sys.argv[1] == "staged"
if staged:
    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            b = json.dumps({"version": "0.1.1", "url": "https://voxterrae.app/releases/0.1.1"}).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(b)
        def log_message(self, *a): pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
    feed = f"http://127.0.0.1:{srv.server_port}/api/latest.json"
else:
    feed = FEED_URL
app = QApplication([]); loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
win = MainWindow(); win.stack.setCurrentWidget(win.chat); win.show(); br = Bridge(win, "vth3" + secrets.token_hex(2), [HOME])
async def run():
    br.start()
    for _ in range(60):
        await asyncio.sleep(0.5)
        if br.sessions["home"].state == "connected": break
    await asyncio.sleep(2)
    check_async(win.update_result.emit, url=feed)          # exactly what __main__.start_live does
    for _ in range(40):
        await asyncio.sleep(0.25)
        if win.update_state.get("status") != "unchecked": break
    await asyncio.sleep(0.5)
    lines = [i.text for i in win.models["home/#warheatmap"].items if i.kind == "system" and "is available" in i.text]
    print("H3 PROOF", "staged" if staged else "real", {"update_state": win.update_state, "title": win.windowTitle(), "system_lines_in_#warheatmap": lines})
    await br.stop(); app.quit()
with loop:
    loop.create_task(run()); loop.run_forever()

"""VoxTerrae entry point.
  python -m voxterrae.app                       -> Welcome screen, ENTER connects (the exe's double-click path)
  python -m voxterrae.app --live HANDLE         -> skip Welcome, connect as HANDLE
  python -m voxterrae.app --demo [--welcome]    -> fictional sample data, no network
  ... --shot out.png 1280x720 [--after SECONDS] -> render to PNG and exit (offscreen proofs)
"""
import argparse, asyncio, getpass, os, re, sys

def _default_handle() -> str:
    raw = os.environ.get("VOXTERRAE_HANDLE") or getpass.getuser() or "guest"
    h = re.sub(r"[^A-Za-z0-9_\-\[\]\\`^{}|]", "", raw)[:16]
    return h if h and not h[0].isdigit() else "vt_" + h

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--demo", action="store_true"); ap.add_argument("--live", metavar="HANDLE")
    ap.add_argument("--theme", default=None); ap.add_argument("--shot", nargs=2, metavar=("PNG", "WxH")); ap.add_argument("--after", type=float, default=8.0)
    ap.add_argument("--welcome", action="store_true")
    a = ap.parse_args(argv)
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings
    import qasync
    from .main_window import MainWindow
    from .bridge import Bridge
    app = QApplication(sys.argv[:1]); app.setApplicationName("VoxTerrae"); app.setOrganizationName("VoxTerrae")
    settings = QSettings("VoxTerrae", "VoxTerrae")
    theme = a.theme or settings.value("theme", "darkops")
    win = MainWindow(theme)
    loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
    state = {"bridge": None}

    def start_live(handle: str):
        handle = (handle or "").strip() or settings.value("handle", "") or _default_handle()
        settings.setValue("handle", handle)
        state["bridge"] = Bridge(win, handle); state["bridge"].start()
        win.stack.setCurrentWidget(win.chat)
        if not os.environ.get("VOXTERRAE_NO_UPDATE_CHECK"):
            from .updates import check_async
            from .updates import FEED_URL
            check_async(win.update_result.emit, url=os.environ.get("VOXTERRAE_UPDATE_FEED") or FEED_URL)

    win.welcome.handle.setText(settings.value("handle", "")); win.welcome.handle.setPlaceholderText(f"handle (default: {_default_handle()})")
    win.welcome.enter.connect(start_live)

    async def shot_and_quit():
        await asyncio.sleep(a.after if (a.live or not a.demo) else 0.3)
        w, h = (int(x) for x in a.shot[1].lower().split("x")); win.resize(w, h); win.view.scrollToBottom()
        await asyncio.sleep(0.5)
        ok = win.grab().save(a.shot[0])
        b = state["bridge"]; rooms = {k: len(m.items) for k, m in win.models.items() if m.items}
        print("shot", a.shot[0], ok, w, h, {k: s.state for k, s in b.sessions.items()} if b else "no-bridge", "items/room:", rooms)
        if b: await b.stop()
        app.quit()

    if a.demo:
        from .demo import populate; populate(win)
        if not a.welcome: win.stack.setCurrentWidget(win.chat)
    elif a.live:
        loop.call_soon(start_live, a.live)   # sessions create asyncio tasks, so this must run inside the loop
    win.show()
    with loop:
        if a.shot: loop.create_task(shot_and_quit())
        loop.run_forever()
    return 0

if __name__ == "__main__":
    sys.exit(main())

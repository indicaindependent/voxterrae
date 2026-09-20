"""Windows 11 integration and process hardening (0.1.2). Every function is a no-op off Windows and never raises:
a cosmetic call must never take the app down.
  - dark title bar + caption/border colours matched to the theme (DWM attributes, Win11 22000+)
  - AppUserModelID so the taskbar groups our windows and toasts carry our name
  - single-instance guard: a second launch raises the first window instead of opening twice
  - crash guard: uncaught exceptions are written to %LOCALAPPDATA%\\VoxTerrae\\logs and shown in a dialog
  - rotating file log next to the profile"""
from __future__ import annotations
import ctypes, logging, logging.handlers, os, sys, traceback, datetime
from typing import Callable, Optional

APP_ID = "IndicaIndependent.VoxTerrae"

def profile_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    d = os.path.join(base, "VoxTerrae"); os.makedirs(d, exist_ok=True); return d

def log_dir() -> str:
    d = os.path.join(profile_dir(), "logs"); os.makedirs(d, exist_ok=True); return d

def setup_logging(level: int = logging.INFO) -> str:
    path = os.path.join(log_dir(), "voxterrae.log")
    root = logging.getLogger()
    if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        h = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")); root.addHandler(h)
    root.setLevel(level); return path

def set_app_id(app_id: str = APP_ID) -> bool:
    if sys.platform != "win32": return False
    try: ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id); return True
    except Exception: return False

def _rgb(hexcol: str) -> int:
    h = hexcol.lstrip("#"); r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16); return r | (g << 8) | (b << 16)

def apply_dark_titlebar(hwnd: int, caption_hex: str = "#0c1219", border_hex: str = "#1c2b38", text_hex: str = "#dbe6ee") -> bool:
    """DWMWA_USE_IMMERSIVE_DARK_MODE (20), DWMWA_BORDER_COLOR (34), DWMWA_CAPTION_COLOR (35), DWMWA_TEXT_COLOR (36)."""
    if sys.platform != "win32" or not hwnd: return False
    try:
        dwm = ctypes.windll.dwmapi; ok = True
        for attr, val in ((20, 1), (35, _rgb(caption_hex)), (34, _rgb(border_hex)), (36, _rgb(text_hex))):
            v = ctypes.c_int(val); r = dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), ctypes.c_uint(attr), ctypes.byref(v), ctypes.sizeof(v))
            ok = ok and (r == 0)
        return ok
    except Exception: return False

class SingleInstance:
    """QLocalServer-based guard. First process listens; later ones send 'raise' and exit. Stale sockets are removed."""
    def __init__(self, name: str = "voxterrae-single-instance", on_raise: Optional[Callable[[], None]] = None):
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        self.name = name; self.on_raise = on_raise; self.server: Optional[QLocalServer] = None; self.is_primary = True
        sock = QLocalSocket(); sock.connectToServer(name)
        if sock.waitForConnected(300):
            sock.write(b"raise\n"); sock.flush(); sock.waitForBytesWritten(300); sock.disconnectFromServer(); self.is_primary = False; return
        QLocalServer.removeServer(name); self.server = QLocalServer(); self.server.newConnection.connect(self._incoming); self.server.listen(name)
    def _incoming(self):
        s = self.server.nextPendingConnection()
        if s is None: return
        s.readyRead.connect(lambda: (s.readAll(), self.on_raise and self.on_raise(), s.disconnectFromServer()))

def install_crash_guard(app_version: str, show_dialog: bool = True) -> None:
    """Write every uncaught exception to logs/crash-<stamp>.log and tell the user where it is. Qt keeps running when it can."""
    log = logging.getLogger("voxterrae.crash")
    def hook(exc_type, exc, tb):
        text = "".join(traceback.format_exception(exc_type, exc, tb)); stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(log_dir(), f"crash-{stamp}.log")
        try:
            with open(path, "w", encoding="utf-8") as f: f.write(f"VoxTerrae {app_version} · Python {sys.version.split()[0]} · {sys.platform}\n\n{text}")
        except Exception: path = "(could not write crash log)"
        log.error("uncaught: %s", text)
        if show_dialog:
            try:
                from PySide6.QtWidgets import QApplication, QMessageBox
                if QApplication.instance() is not None:
                    m = QMessageBox(); m.setIcon(QMessageBox.Critical); m.setWindowTitle("VoxTerrae hit a problem")
                    m.setText("Something went wrong inside VoxTerrae. The window stays open; if things look wrong, restart it.")
                    m.setInformativeText(f"Details were saved to:\n{path}\n\nPlease attach that file when you report it at github.com/indicaindependent/voxterrae/issues.")
                    m.setDetailedText(text); m.exec()
            except Exception: pass
    sys.excepthook = hook

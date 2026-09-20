"""Inline SVG icon set for the chrome. Pete's rule: no emoji or text glyphs as UI decoration, clean SVG all the way.
   Message CONTENT (reaction payloads such as 👍) is not chrome and is untouched. Every icon is a single-colour path
   rendered through QSvgRenderer into a cached QPixmap at the device pixel ratio, so it stays crisp on HiDPI."""
from __future__ import annotations
from typing import Dict, Tuple
from PySide6.QtCore import Qt, QByteArray, QRectF, QSize
from PySide6.QtGui import QPixmap, QPainter, QIcon, QGuiApplication
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

# 24x24 viewBox, fill/stroke colour injected as {c}
_SVG: Dict[str, str] = {
    # brand mark: outer rounded square + solid inner square (same shape as the tray icon)
    "mark":    '<rect x="2" y="2" width="20" height="20" rx="4" fill="none" stroke="{c}" stroke-width="2.2"/><rect x="7.5" y="7.5" width="9" height="9" fill="{c}"/>',
    "dot":     '<circle cx="12" cy="12" r="5" fill="{c}"/>',                                   # connected
    "ring":    '<circle cx="12" cy="12" r="4.4" fill="none" stroke="{c}" stroke-width="1.8"/>',  # connecting / reconnecting
    "square":  '<rect x="4" y="4" width="16" height="16" rx="2.5" fill="{c}"/>',                # theatre marker
    "star":    '<path d="M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2l-5.7 3.1 1.2-6.4L2.8 9.5l6.4-.8z" fill="{c}"/>',
    "close":   '<path d="M6 6l12 12M18 6L6 18" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>',
    "reply":   '<path d="M5 4v8a3 3 0 0 0 3 3h10M14 11l4 4-4 4" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "chevron": '<path d="M9 6l6 6-6 6" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    "chevron_down": '<path d="M6 9l6 6 6-6" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    "hash":    '<path d="M9 3L7 21M17 3l-2 18M4 8h17M3 16h17" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "at":      '<circle cx="12" cy="12" r="4" fill="none" stroke="{c}" stroke-width="2"/><path d="M16 12v1.5a2.5 2.5 0 0 0 5 0V12a9 9 0 1 0-3.5 7.1" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "server":  '<rect x="3" y="4" width="18" height="6" rx="2" fill="none" stroke="{c}" stroke-width="2"/><rect x="3" y="14" width="18" height="6" rx="2" fill="none" stroke="{c}" stroke-width="2"/><circle cx="7" cy="7" r="1.2" fill="{c}"/><circle cx="7" cy="17" r="1.2" fill="{c}"/>',
    "send":    '<path d="M4 12L20 4l-4 16-4-7z" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/><path d="M12 13l8-9" fill="none" stroke="{c}" stroke-width="2"/>',
    "settings":'<circle cx="12" cy="12" r="3" fill="none" stroke="{c}" stroke-width="2"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" fill="none" stroke="{c}" stroke-width="1.6" stroke-linejoin="round"/>',
    "search":  '<circle cx="11" cy="11" r="6.5" fill="none" stroke="{c}" stroke-width="2.2"/><path d="M20 20l-4-4" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>',
    "copy":    '<rect x="9" y="9" width="12" height="12" rx="2" fill="none" stroke="{c}" stroke-width="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "plus":    '<path d="M12 5v14M5 12h14" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>',
    "react":   '<circle cx="12" cy="12" r="9" fill="none" stroke="{c}" stroke-width="2"/><path d="M8 14s1.5 2 4 2 4-2 4-2" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/><circle cx="9" cy="10" r="1.1" fill="{c}"/><circle cx="15" cy="10" r="1.1" fill="{c}"/>',
    "users":   '<circle cx="9" cy="8" r="3.5" fill="none" stroke="{c}" stroke-width="2"/><path d="M3 20a6 6 0 0 1 12 0" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M21 20a6 6 0 0 0-4-5.6" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "link":    '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1.5 1.5M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1.5-1.5" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "warning": '<path d="M12 3L2 21h20z" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/><path d="M12 10v5" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="18" r="1.2" fill="{c}"/>',
    "arrow_down": '<path d="M12 4v16M5 13l7 7 7-7" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>',
    "lock":    '<rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="{c}" stroke-width="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4" fill="none" stroke="{c}" stroke-width="2"/>',
    "unlock":  '<rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="{c}" stroke-width="2"/><path d="M8 11V7a4 4 0 0 1 7.5-2" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "bell":    '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/><path d="M10 21a2 2 0 0 0 4 0" fill="none" stroke="{c}" stroke-width="2"/>',
    "info":    '<circle cx="12" cy="12" r="9" fill="none" stroke="{c}" stroke-width="2"/><path d="M12 11v6" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/><circle cx="12" cy="7.5" r="1.2" fill="{c}"/>',
    "map":     '<path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/><path d="M9 4v14M15 6v14" fill="none" stroke="{c}" stroke-width="2"/>',
    "external":'<path d="M14 4h6v6M20 4l-9 9" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/><path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "crown":   '<path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z" fill="{c}"/>',
    "shield":  '<path d="M12 3l8 3v6c0 4.5-3.4 8.3-8 9-4.6-.7-8-4.5-8-9V6z" fill="{c}"/>',
    "bolt":    '<path d="M13 2L4 14h7l-1 8 9-12h-7z" fill="{c}"/>',
    "voice":   '<path d="M6 10v4M10 6v12M14 8v8M18 10v4" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round"/>',
    "keyboard":'<rect x="2" y="6" width="20" height="12" rx="2" fill="none" stroke="{c}" stroke-width="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
    "minus":   '<path d="M5 12h14" fill="none" stroke="{c}" stroke-width="2.2" stroke-linecap="round"/>',
    "check":   '<path d="M5 12l5 5L20 7" fill="none" stroke="{c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>',
    "eye_off": '<path d="M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.2A10 10 0 0 1 12 5c5 0 9 4 10 7-.4 1.1-1.2 2.4-2.3 3.5M6.6 6.6C4.4 8 3 10 2 12c1 3 5 7 10 7 1.8 0 3.4-.5 4.8-1.3" fill="none" stroke="{c}" stroke-width="2" stroke-linecap="round"/>',
}

def svg(name: str, color: str) -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">{_SVG[name].format(c=color)}</svg>'

_cache: Dict[Tuple[str, str, int, float], QPixmap] = {}

def pixmap(name: str, color: str, size: int = 16) -> QPixmap:
    """Cached, DPR-aware render. Falls back to a 1.0 ratio when no screen exists (unit tests)."""
    app = QGuiApplication.instance(); dpr = float(app.devicePixelRatio()) if app else 1.0
    key = (name, color, size, dpr)
    if key in _cache: return _cache[key]
    px = int(round(size * dpr)); pm = QPixmap(px, px); pm.fill(Qt.transparent)
    r = QSvgRenderer(QByteArray(svg(name, color).encode())); p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    r.render(p, QRectF(0, 0, px, px)); p.end(); pm.setDevicePixelRatio(dpr)
    _cache[key] = pm; return pm

def icon(name: str, color: str, size: int = 16) -> QIcon:
    return QIcon(pixmap(name, color, size))

class IconLabel(QWidget):
    """A QLabel with an SVG icon before (or after) the text. `object_name` goes on the TEXT label so existing QSS keeps working."""
    def __init__(self, name: str, color: str, text: str = "", size: int = 14, object_name: str = "", after: bool = False, word_wrap: bool = False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        self.ico = QLabel(); self.ico.setFixedSize(size, size); self.ico.setAlignment(Qt.AlignCenter); self.ico.setScaledContents(False)
        self.lbl = QLabel(text); self.lbl.setWordWrap(word_wrap)
        if object_name: self.lbl.setObjectName(object_name)
        order = (self.lbl, self.ico) if after else (self.ico, self.lbl)
        for w in order: lay.addWidget(w)
        if after: lay.insertStretch(1, 0)
        else: lay.addStretch(1)
        if word_wrap: lay.setAlignment(self.ico, Qt.AlignTop)
        self._size = size; self.set_icon(name, color)
    def set_icon(self, name: str, color: str) -> None:
        self.ico.setPixmap(pixmap(name, color, self._size))
    def setText(self, text: str) -> None: self.lbl.setText(text)
    def text(self) -> str: return self.lbl.text()
    def setFont(self, f) -> None: self.lbl.setFont(f)
    def font(self): return self.lbl.font()

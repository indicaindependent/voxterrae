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

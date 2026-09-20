"""Members panel (0.1.2): rank badges as SVG (owner / admin / op / half-op / voice), sorted by rank then name,
a live count, a filter box once the room is big, and a right-click menu (mention, message, whois, copy)."""
from __future__ import annotations
from typing import Dict, List, Optional
from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal, QPoint
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QAction, QGuiApplication
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMenu, QStyledItemDelegate, QStyle, QVBoxLayout, QWidget, QHBoxLayout
from .icons import pixmap
from .theme import Palette, nick_color

RANKS = {"~": ("crown", "owner"), "&": ("shield", "admin"), "@": ("shield", "op"), "%": ("bolt", "half-op"), "+": ("voice", "voice")}
ORDER = "~&@%+"

def split_prefix(entry: str):
    """'@ nick' | '@nick' | 'nick' -> (prefix, nick)"""
    e = entry.strip()
    if e and e[0] in ORDER: return e[0], e[1:].strip()
    return "", e

class _Delegate(QStyledItemDelegate):
    def __init__(self, p: Palette, parent, me: str = ""):
        super().__init__(parent); self.p = p; self.me = me; self.f = QFont(); self.f.setPixelSize(14)
    def sizeHint(self, option, index) -> QSize: return QSize(option.rect.width(), 28)
    def paint(self, painter: QPainter, option, index):
        p = self.p; r = option.rect; prefix, nick = split_prefix(index.data(Qt.DisplayRole) or ""); painter.save(); painter.setRenderHint(QPainter.Antialiasing)
        if option.state & (QStyle.State_Selected | QStyle.State_MouseOver):
            painter.setPen(Qt.NoPen); painter.setBrush(QColor(p.panel3 if option.state & QStyle.State_Selected else p.panel2)); painter.drawRoundedRect(QRectF(r.adjusted(2, 1, -2, -1)), 6, 6)
        x = r.left() + 8
        if prefix in RANKS:
            name, _ = RANKS[prefix]; col = p.amber if prefix in "~&" else (p.phosphor if prefix == "@" else p.cyan)
            painter.drawPixmap(x, r.center().y() - 6, pixmap(name, col, 12))
        x += 20; painter.setFont(self.f)
        painter.setPen(QColor(p.phosphor if nick == self.me else (p.cyan if nick.lower().startswith("axiom") else nick_color(p, nick))))
        painter.drawText(QRect(x, r.top(), r.right() - x - 6, r.height()), Qt.AlignLeft | Qt.AlignVCenter, QFontMetrics(self.f).elidedText(nick, Qt.ElideRight, r.right() - x - 6))
        painter.restore()

class MemberList(QWidget):
    mention = Signal(str); message = Signal(str); whois = Signal(str)
    def __init__(self, p: Palette, parent=None):
        super().__init__(parent); self.p = p; self._all: List[str] = []; self.me = ""
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        head = QHBoxLayout(); head.setContentsMargins(0, 0, 0, 0); self.title = QLabel("MEMBERS"); self.title.setObjectName("sectionHead"); head.addWidget(self.title); head.addStretch(); lay.addLayout(head)
        self.filter = QLineEdit(); self.filter.setObjectName("filter"); self.filter.setPlaceholderText("filter members"); self.filter.setClearButtonEnabled(True); self.filter.textChanged.connect(self._refill); self.filter.hide(); lay.addWidget(self.filter)
        self.list = QListWidget(); self.list.setObjectName("members"); self.list.setFrameShape(QFrame.NoFrame); self.list.setMouseTracking(True); self.delegate = _Delegate(p, self.list); self.list.setItemDelegate(self.delegate)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu); self.list.customContextMenuRequested.connect(self._menu); self.list.itemDoubleClicked.connect(lambda it: self.mention.emit(split_prefix(it.text())[1]))
        lay.addWidget(self.list, 1)
        self.empty = QLabel("nobody here yet"); self.empty.setObjectName("hint"); self.empty.setAlignment(Qt.AlignCenter); lay.addWidget(self.empty); self.empty.hide()
    def set_me(self, nick: str): self.me = nick; self.delegate.me = nick; self.list.viewport().update()
    def set_members(self, names: List[str]):
        self._all = sorted(names, key=lambda n: (ORDER.find(split_prefix(n)[0]) if split_prefix(n)[0] and split_prefix(n)[0] in ORDER else 9, split_prefix(n)[1].lower()))
        self.filter.setVisible(len(self._all) > 20); self._refill()
    def nicks(self) -> List[str]: return [split_prefix(n)[1] for n in self._all]
    def _refill(self):
        q = self.filter.text().strip().lower(); self.list.clear()
        shown = [n for n in self._all if q in split_prefix(n)[1].lower()]
        for n in shown: self.list.addItem(QListWidgetItem(n))
        ops = sum(1 for n in self._all if split_prefix(n)[0] and split_prefix(n)[0] in "~&@")
        self.title.setText(f"MEMBERS · {len(self._all)}" + (f" · {ops} ops" if ops else "") if self._all else "MEMBERS")
        self.empty.setVisible(not self._all); self.list.setVisible(bool(self._all))
    def _menu(self, pos: QPoint):
        it = self.list.itemAt(pos)
        if not it: return
        prefix, nick = split_prefix(it.text()); m = QMenu(self)
        a = QAction(f"Mention {nick}", m); a.triggered.connect(lambda: self.mention.emit(nick)); m.addAction(a)
        b = QAction("Message", m); b.triggered.connect(lambda: self.message.emit(nick)); m.addAction(b)
        w = QAction("Whois", m); w.triggered.connect(lambda: self.whois.emit(nick)); m.addAction(w)
        m.addSeparator(); c = QAction("Copy nick", m); c.triggered.connect(lambda: QGuiApplication.clipboard().setText(nick)); m.addAction(c)
        if prefix in RANKS: m.addSeparator(); r = QAction(RANKS[prefix][1], m); r.setEnabled(False); m.addAction(r)
        m.exec(self.list.viewport().mapToGlobal(pos))

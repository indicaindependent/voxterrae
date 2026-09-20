"""Room rail (0.1.2): networks as collapsible groups, rooms with kind icons (hash / at / server), unread and
mention pills, an active indicator and a right-click menu. Item data(UserRole) is the room key "netkey/#chan";
header rows carry None there so existing tests keep working."""
from __future__ import annotations
from typing import Dict, List, Optional, Set
from PySide6.QtCore import QRect, QRectF, QSize, Qt, Signal, QPoint
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QAction
from PySide6.QtWidgets import QFrame, QListWidget, QListWidgetItem, QMenu, QStyledItemDelegate, QStyle
from .icons import pixmap
from .theme import Palette

ROLE_KEY = Qt.UserRole; ROLE_INFO = Qt.UserRole + 1

def room_display(key: str) -> str:
    name = key.split("/", 1)[1] if "/" in key else key
    return "network" if name == "*server*" else name

def room_kind(key: str) -> str:
    name = key.split("/", 1)[1] if "/" in key else key
    if name == "*server*": return "server"
    return "hash" if name.startswith(("#", "&")) else "at"

class _Delegate(QStyledItemDelegate):
    def __init__(self, p: Palette, parent):
        super().__init__(parent); self.p = p; self.f_head = QFont("Cascadia Mono"); self.f_head.setStyleHint(QFont.Monospace); self.f_head.setPixelSize(11); self.f_head.setBold(True); self.f_head.setLetterSpacing(QFont.AbsoluteSpacing, 1.5)
        self.f_room = QFont(); self.f_room.setPixelSize(14); self.f_room_b = QFont(self.f_room); self.f_room_b.setBold(True); self.f_pill = QFont(); self.f_pill.setPixelSize(11); self.f_pill.setBold(True)
    def sizeHint(self, option, index) -> QSize:
        info = index.data(ROLE_INFO) or {}
        return QSize(option.rect.width(), 30 if info.get("header") else 32)
    def paint(self, painter: QPainter, option, index):
        p = self.p; r = option.rect; info = index.data(ROLE_INFO) or {}; painter.save(); painter.setRenderHint(QPainter.Antialiasing)
        if info.get("header"):
            state = info.get("state", ""); ok = state == "connected"; col = p.phosphor if ok else (p.amber if state.startswith(("connecting", "retry", "reconnect")) else p.muted)
            painter.drawPixmap(r.left() + 6, r.center().y() - 6, pixmap("chevron_down" if not info.get("collapsed") else "chevron", p.dim, 12))
            painter.drawPixmap(r.left() + 24, r.center().y() - 5, pixmap("dot" if ok else "ring", col, 10))
            painter.setFont(self.f_head); painter.setPen(QColor(p.muted)); painter.drawText(QRect(r.left() + 40, r.top(), r.width() - 40, r.height()), Qt.AlignLeft | Qt.AlignVCenter, info.get("label", ""))
            st = "" if ok else state
            if st:
                fm = QFontMetrics(self.f_head); painter.setPen(QColor(col)); painter.drawText(QRect(r.left() + 40, r.top(), r.width() - 48, r.height()), Qt.AlignRight | Qt.AlignVCenter, fm.elidedText(st, Qt.ElideRight, r.width() - 40 - fm.horizontalAdvance(info.get("label", "")) - 24))
            painter.restore(); return
        selected = bool(option.state & QStyle.State_Selected); hovered = bool(option.state & QStyle.State_MouseOver)
        if selected or hovered:
            painter.setPen(Qt.NoPen); painter.setBrush(QColor(p.panel3 if selected else p.panel2)); painter.drawRoundedRect(QRectF(r.adjusted(6, 1, -6, -1)), 6, 6)
        if selected: painter.setBrush(QColor(p.phosphor)); painter.drawRoundedRect(QRectF(r.left() + 6, r.top() + 8, 3, r.height() - 16), 1.5, 1.5)
        unread = info.get("unread", 0); mention = info.get("mention", 0); kind = info.get("kind", "hash")
        icol = p.phosphor if selected else (p.text if unread else p.muted)
        painter.drawPixmap(r.left() + 18, r.center().y() - 7, pixmap(kind, icol, 14))
        painter.setFont(self.f_room_b if unread and not selected else self.f_room); painter.setPen(QColor(p.phosphor if selected else (p.text if unread else p.muted)))
        right = r.right() - 10
        if unread:
            label = str(min(unread, 99)) + ("+" if unread > 99 else ""); fm = QFontMetrics(self.f_pill); pw = max(20, fm.horizontalAdvance(label) + 12)
            pill = QRectF(right - pw, r.center().y() - 9, pw, 18); painter.setPen(Qt.NoPen); painter.setBrush(QColor(p.phosphor if mention else p.panel3)); painter.drawRoundedRect(pill, 9, 9)
            painter.setFont(self.f_pill); painter.setPen(QColor(p.bg if mention else p.text)); painter.drawText(pill, Qt.AlignCenter, label); right -= pw + 8
            painter.setFont(self.f_room_b); painter.setPen(QColor(p.phosphor if selected else p.text))
        fm = QFontMetrics(painter.font()); painter.drawText(QRect(r.left() + 40, r.top(), right - r.left() - 40, r.height()), Qt.AlignLeft | Qt.AlignVCenter, fm.elidedText(info.get("name", ""), Qt.ElideRight, right - r.left() - 40))
        painter.restore()

class RoomList(QListWidget):
    """Rooms grouped by network. Item data = room key "netkey/#chan"; header items are unselectable."""
    part_requested = Signal(str); mark_read_requested = Signal(str); close_requested = Signal(str)
    def __init__(self, p: Palette):
        super().__init__(); self.p = p; self.setObjectName("roomList"); self.setFrameShape(QFrame.NoFrame); self.setMouseTracking(True)
        self._unread: Dict[str, int] = {}; self._mention: Dict[str, int] = {}; self.collapsed: Set[str] = set(); self._groups: List[tuple] = []; self._active = ""
        self.setItemDelegate(_Delegate(p, self)); self.setSpacing(0); self.setUniformItemSizes(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu); self.customContextMenuRequested.connect(self._menu); self.itemClicked.connect(self._clicked)
    def set_groups(self, groups: List[tuple], active: str):
        """groups = [(net_label, net_state, [room_key, ...]), ...]"""
        self._groups = groups; self._active = active
        self.blockSignals(True)   # QListWidget.clear() moves "current" onto a random surviving row while items are removed; that fired show_room() on an unrelated room and wiped its unread badge
        self.clear()
        for label, state, keys in groups:
            netkey = keys[0].split("/", 1)[0] if keys else label.lower(); col = netkey in self.collapsed
            h = QListWidgetItem(f"{label}   {state}"); h.setFlags(Qt.NoItemFlags); h.setData(ROLE_KEY, None); h.setData(ROLE_INFO, {"header": True, "label": label, "state": state, "netkey": netkey, "collapsed": col}); self.addItem(h)
            if col: continue
            for k in keys:
                it = QListWidgetItem(self._label(k)); it.setData(ROLE_KEY, k); it.setData(ROLE_INFO, self._info(k)); self.addItem(it)
                if k == active: self.setCurrentItem(it)
        self.blockSignals(False)
    def _info(self, k: str) -> dict:
        return {"name": room_display(k), "kind": room_kind(k), "unread": self._unread.get(k, 0), "mention": self._mention.get(k, 0)}
    def _label(self, k: str) -> str:
        n = self._unread.get(k, 0); return f"   {room_display(k)}" + (f"   ·{n}" if n else "")
    def bump(self, key: str, n: int, mention: Optional[int] = None):
        self._unread[key] = n
        if mention is not None: self._mention[key] = mention
        if n == 0: self._mention[key] = 0
        for i in range(self.count()):
            if self.item(i).data(ROLE_KEY) == key: self.item(i).setText(self._label(key)); self.item(i).setData(ROLE_INFO, self._info(key))
    def total_mentions(self) -> int: return sum(self._mention.values())
    def keys(self) -> List[str]: return [k for _, _, ks in self._groups for k in ks]
    def _clicked(self, item: QListWidgetItem):
        info = item.data(ROLE_INFO) or {}
        if info.get("header"):
            nk = info["netkey"]; self.collapsed.symmetric_difference_update({nk}); self.set_groups(self._groups, self._active)
    def mousePressEvent(self, e):
        it = self.itemAt(e.position().toPoint() if hasattr(e, "position") else e.pos())
        if it is not None and (it.data(ROLE_INFO) or {}).get("header") and e.button() == Qt.LeftButton: self._clicked(it); return
        super().mousePressEvent(e)
    def _menu(self, pos: QPoint):
        it = self.itemAt(pos); key = it.data(ROLE_KEY) if it else None
        if not key: return
        m = QMenu(self); kind = room_kind(key)
        a = QAction("Mark as read", m); a.triggered.connect(lambda: self.mark_read_requested.emit(key)); m.addAction(a)
        if kind == "hash": b = QAction("Leave room", m); b.triggered.connect(lambda: self.part_requested.emit(key)); m.addAction(b)
        elif kind == "at": b = QAction("Close conversation", m); b.triggered.connect(lambda: self.close_requested.emit(key)); m.addAction(b)
        m.addSeparator(); c = QAction("Copy name", m); c.triggered.connect(lambda: __import__("PySide6.QtGui", fromlist=["QGuiApplication"]).QGuiApplication.clipboard().setText(room_display(key))); m.addAction(c)
        m.exec(self.viewport().mapToGlobal(pos))
    def next_key(self, step: int) -> Optional[str]:
        keys = [k for k in self.keys()]
        if not keys or self._active not in keys: return keys[0] if keys else None
        return keys[(keys.index(self._active) + step) % len(keys)]
    def next_unread(self) -> Optional[str]:
        keys = self.keys()
        if not keys: return None
        start = keys.index(self._active) if self._active in keys else -1
        for i in range(1, len(keys) + 1):
            k = keys[(start + i) % len(keys)]
            if self._unread.get(k): return k
        return None

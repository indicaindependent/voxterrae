"""VoxTerrae main window: rooms | timeline + composer | WarHeatMap rail. Widgets + QSS (v1)."""
from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QSettings, QTimer, QRect
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QFont, QIcon, QGuiApplication, QAction
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMainWindow,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget, QSplitter, QStackedWidget, QMenu, QSystemTrayIcon, QApplication)
from .theme import Palette, qss, THEMES
from .timeline import TimelineModel, TimelineDelegate, Item
from .. import __version__ as APP_VERSION

class Welcome(QWidget):
    """First screen: one button. No server/port/nick wall."""
    enter = Signal(str)
    def __init__(self, p: Palette):
        super().__init__(); self.p = p
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignCenter); lay.setSpacing(16)
        mark = QLabel("▣ VOXTERRAE"); mark.setObjectName("wordmark"); mark.setAlignment(Qt.AlignCenter)
        f = mark.font(); f.setPixelSize(34); mark.setFont(f)
        sub = QLabel("the door from the map to the room"); sub.setObjectName("sectionHead"); sub.setAlignment(Qt.AlignCenter)
        self.handle = QLineEdit(); self.handle.setObjectName("composer"); self.handle.setPlaceholderText("pick a handle (optional)"); self.handle.setFixedWidth(340); self.handle.setAlignment(Qt.AlignCenter)
        btn = QPushButton("ENTER #WARHEATMAP"); btn.setObjectName("primary"); btn.setFixedWidth(340); btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.enter.emit(self.handle.text().strip()))
        note = QLabel("live rooms on irc.warheatmap.app · no account needed · TLS"); note.setObjectName("status"); note.setAlignment(Qt.AlignCenter)
        for w in (mark, sub, self.handle, btn, note): lay.addWidget(w, 0, Qt.AlignCenter)

class RoomList(QListWidget):
    """Rooms grouped by network. Item data = room key "netkey/#chan"; header items are unselectable."""
    def __init__(self):
        super().__init__(); self.setObjectName("roomList"); self.setFrameShape(QFrame.NoFrame); self._unread: Dict[str, int] = {}
    def set_groups(self, groups: List[tuple], active: str):
        """groups = [(net_label, net_state, [room_key, ...]), ...]"""
        self.clear()
        for label, state, keys in groups:
            h = QListWidgetItem(f"{label}   {state}"); h.setFlags(Qt.NoItemFlags); f = h.font(); f.setPixelSize(11); f.setBold(True); h.setFont(f); h.setData(Qt.UserRole, None); self.addItem(h)
            for k in keys:
                it = QListWidgetItem(self._label(k)); it.setData(Qt.UserRole, k); self.addItem(it)
                if k == active: self.setCurrentItem(it)
    def _label(self, k: str) -> str:
        n = self._unread.get(k, 0); name = k.split("/", 1)[1] if "/" in k else k
        return f"   {name}" + (f"   ·{n}" if n else "")
    def bump(self, key: str, n: int):
        self._unread[key] = n
        for i in range(self.count()):
            if self.item(i).data(Qt.UserRole) == key: self.item(i).setText(self._label(key))

class MapRail(QFrame):
    """Right rail: live ticker (card-only until the site feed is confirmed) + WarDesk card + members."""
    def __init__(self, p: Palette):
        super().__init__(); self.setObjectName("mapRail"); self.p = p
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)
        h = QLabel("LIVE MAP"); h.setObjectName("sectionHead"); lay.addWidget(h)
        self.map = QLabel(); self.map.setFixedHeight(110); self.map.setPixmap(self._fake_map(236, 110)); lay.addWidget(self.map)
        self.ticker = QVBoxLayout(); self.ticker.setSpacing(4); lay.addLayout(self.ticker)
        lay.addSpacing(8); c = QLabel("WARDESK · LATEST"); c.setObjectName("cardTitle"); lay.addWidget(c)
        card = QFrame(); card.setObjectName("card"); cl = QVBoxLayout(card); cl.setContentsMargins(10, 10, 10, 10)
        self.card_title = QLabel("Ukraine WarDesk · 8 posts · 7-min drip"); self.card_title.setWordWrap(True)
        self.card_meta = QLabel("fired 02:04 ET · 5.40★"); self.card_meta.setObjectName("status")
        cl.addWidget(self.card_title); cl.addWidget(self.card_meta); lay.addWidget(card)
        lay.addSpacing(8); m = QLabel("MEMBERS"); m.setObjectName("sectionHead"); lay.addWidget(m)
        self.members = QListWidget(); self.members.setFrameShape(QFrame.NoFrame); lay.addWidget(self.members, 1)
    def set_events(self, evs: List[tuple]):
        while self.ticker.count():
            w = self.ticker.takeAt(0).widget()
            if w: w.deleteLater()
        for theatre, text in evs:
            l = QLabel(("🟥 " if theatre == "red" else "🟦 ") + text); l.setObjectName("eventRed" if theatre == "red" else "eventBlue"); l.setWordWrap(True); self.ticker.addWidget(l)
    def set_members(self, names: List[str]):
        self.members.clear()
        for n in names: self.members.addItem(n)
    def _fake_map(self, w, h) -> QPixmap:
        pm = QPixmap(w, h); pm.fill(QColor(self.p.panel2)); q = QPainter(pm); q.setRenderHint(QPainter.Antialiasing)
        q.setPen(QPen(QColor(self.p.grid), 1))
        for x in range(0, w, 20): q.drawLine(x, 0, x, h)
        for y in range(0, h, 20): q.drawLine(0, y, w, y)
        for (cx, cy, col, r) in ((150, 48, self.p.red, 9), (128, 34, self.p.blue, 7), (140, 70, self.p.red, 6), (60, 40, self.p.amber, 4)):
            for rr, a in ((r * 2.4, 40), (r * 1.6, 90), (r, 255)):
                c = QColor(col); c.setAlpha(a); q.setBrush(c); q.setPen(Qt.NoPen); q.drawEllipse(int(cx - rr), int(cy - rr), int(rr * 2), int(rr * 2))
        q.end(); return pm

QUICK_REACTIONS = ["👍", "🔥", "👀", "💯", "😂", "🙏"]

def make_icon(p: Palette, badge: int = 0) -> QIcon:
    pm = QPixmap(64, 64); pm.fill(Qt.transparent); q = QPainter(pm); q.setRenderHint(QPainter.Antialiasing)
    q.setBrush(QColor(p.bg)); q.setPen(QPen(QColor(p.phosphor), 4)); q.drawRoundedRect(4, 4, 56, 56, 12, 12)
    q.setPen(Qt.NoPen); q.setBrush(QColor(p.phosphor)); q.drawRect(18, 18, 28, 28)
    if badge:
        q.setBrush(QColor(p.red)); q.drawEllipse(36, 0, 28, 28); q.setPen(QColor("#ffffff")); f = QFont(); f.setPixelSize(16); f.setBold(True); q.setFont(f)
        q.drawText(QRect(36, 0, 28, 28), Qt.AlignCenter, str(min(badge, 9)) + ("+" if badge > 9 else ""))
    q.end(); return QIcon(pm)

class MainWindow(QMainWindow):
    send_text = Signal(str, str)              # room key, text
    send_reply = Signal(str, str, str)        # room key, parent msgid, text
    send_react = Signal(str, str, str)        # room key, msgid, emoji
    typing_changed = Signal(str, bool)        # room key, active
    room_changed = Signal(str)
    update_result = Signal(dict)   # H3: emitted from the update-check thread, handled on the UI thread                # room key (for read markers / members refresh)
    def __init__(self, theme: str = "darkops"):
        super().__init__(); self.p = THEMES[theme]; self.setWindowTitle(self._base_title()); self.resize(1280, 760)
        self.setStyleSheet(qss(self.p))
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.welcome = Welcome(self.p); self.stack.addWidget(self.welcome)
        self.chat = QWidget(); self.stack.addWidget(self.chat); self._build_chat()
        self.welcome.enter.connect(lambda h: self.stack.setCurrentWidget(self.chat))
        self.models: Dict[str, TimelineModel] = {}; self.active = "home/#warheatmap"; self.net_labels: Dict[str, str] = {}
        self.reply_to: Optional[Item] = None; self.unread_total = 0; self.update_state = {"status": "unchecked"}; self.update_result.connect(self.on_update_result)
        self.settings = QSettings("VoxTerrae", "VoxTerrae")
        if (g := self.settings.value("geometry")) is not None: self.restoreGeometry(g)
        self.setWindowIcon(make_icon(self.p))
        self.tray = QSystemTrayIcon(make_icon(self.p), self) if QSystemTrayIcon.isSystemTrayAvailable() else None
        if self.tray:
            m = QMenu(); a = QAction("Show VoxTerrae", m); a.triggered.connect(self._raise); m.addAction(a); qa = QAction("Quit", m); qa.triggered.connect(QApplication.instance().quit); m.addAction(qa)
            self.tray.setContextMenu(m); self.tray.activated.connect(lambda r: self._raise()); self.tray.show()
        self._typing_timer = QTimer(self); self._typing_timer.setSingleShot(True); self._typing_timer.timeout.connect(lambda: self.typing_changed.emit(self.active, False))
        self._typing_sent = False
    def _build_chat(self):
        root = QHBoxLayout(self.chat); root.setContentsMargins(10, 10, 10, 10); root.setSpacing(10)
        # left: rooms
        left = QFrame(); left.setObjectName("rooms"); left.setFixedWidth(220); ll = QVBoxLayout(left); ll.setContentsMargins(12, 12, 12, 12)
        mark = QLabel("▣ VOXTERRAE"); mark.setObjectName("wordmark"); ll.addWidget(mark)
        rh = QLabel("ROOMS"); rh.setObjectName("sectionHead"); ll.addWidget(rh)
        self.rooms = RoomList(); ll.addWidget(self.rooms, 1)
        self.rooms.currentItemChanged.connect(lambda cur, prev: cur and cur.data(Qt.UserRole) and self.show_room(cur.data(Qt.UserRole)))
        self.me = QLabel("● connecting…"); self.me.setObjectName("status"); ll.addWidget(self.me)
        root.addWidget(left)
        # centre: timeline
        mid = QFrame(); mid.setObjectName("timeline"); ml = QVBoxLayout(mid); ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(0)
        head = QWidget(); hl = QHBoxLayout(head); hl.setContentsMargins(14, 10, 14, 10)
        self.title = QLabel("#warheatmap"); self.title.setObjectName("roomTitle"); self.meta = QLabel(""); self.meta.setObjectName("roomMeta")
        hl.addWidget(self.title); hl.addSpacing(10); hl.addWidget(self.meta); hl.addStretch(); ml.addWidget(head)
        self.view = QListView(); self.view.setObjectName("timelineView"); self.view.setFrameShape(QFrame.NoFrame)
        self.view.setItemDelegate(TimelineDelegate(self.p, self.view)); self.view.setSelectionMode(QListView.NoSelection); self.view.setUniformItemSizes(False)
        self.view.setWordWrap(True); self.view.setResizeMode(QListView.Adjust); ml.addWidget(self.view, 1)
        self.typing = QLabel(""); self.typing.setObjectName("typing"); self.typing.setContentsMargins(14, 0, 14, 4); ml.addWidget(self.typing)
        self.reply_strip = QWidget(); rs = QHBoxLayout(self.reply_strip); rs.setContentsMargins(14, 0, 14, 0)
        self.reply_label = QLabel(""); self.reply_label.setObjectName("typing"); rs.addWidget(self.reply_label, 1)
        cancel = QPushButton("✕"); cancel.setFixedSize(24, 22); cancel.setToolTip("cancel reply (Esc)"); cancel.clicked.connect(self.clear_reply); rs.addWidget(cancel)
        self.reply_strip.hide(); ml.addWidget(self.reply_strip)
        comp = QWidget(); cl = QHBoxLayout(comp); cl.setContentsMargins(12, 6, 12, 12)
        self.composer = QLineEdit(); self.composer.setObjectName("composer"); self.composer.setPlaceholderText("message #warheatmap …  (Enter to send · /help)")
        self.composer.returnPressed.connect(self._send); self.composer.textEdited.connect(self._on_typing); cl.addWidget(self.composer); ml.addWidget(comp)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu); self.view.customContextMenuRequested.connect(self._message_menu)
        self.view.clicked.connect(self._on_view_click)
        root.addWidget(mid, 1)
        # right: map rail
        self.rail = MapRail(self.p); self.rail.setFixedWidth(260); root.addWidget(self.rail)
    # ---- API used by the bridge / demo ----
    def set_groups(self, groups: List[tuple]):
        for label, state, keys in groups:
            for k in keys:
                self.models.setdefault(k, TimelineModel()); self.net_labels[k] = label
        self.rooms.set_groups(groups, self.active); self.show_room(self.active)
    def show_room(self, key: str):
        changed = key != self.active   # set_groups() re-shows the active room on every roster change; that must not clear the badge
        self.active = key; name = key.split("/", 1)[1] if "/" in key else key
        self.title.setText(name); self.view.setModel(self.models.setdefault(key, TimelineModel())); self.view.scrollToBottom()
        net = self.net_labels.get(key, ""); self.composer.setPlaceholderText(f"message {name} on {net} …  (Enter to send · /help)"); self.rooms.bump(key, 0)
        self.clear_reply(); self.room_changed.emit(key)
        if changed and self.unread_total:  # switching to a room clears the mention badge; the per-room counts stay honest on the rail
            self.unread_total = 0; self.setWindowTitle(self._base_title())
            if self.tray: self.tray.setIcon(make_icon(self.p))
    def add(self, room: str, it: Item):
        m = self.models.setdefault(room, TimelineModel()); m.append(it)
        if room == self.active: self.view.scrollToBottom()
        elif it.kind == "msg": self.rooms.bump(room, self.rooms._unread.get(room, 0) + 1)
    def _send(self):
        t = self.composer.text().strip()
        if not t: return
        if self.reply_to and self.reply_to.msgid and not t.startswith("/"):
            self.send_reply.emit(self.active, self.reply_to.msgid, t); self.clear_reply()
        else:
            self.send_text.emit(self.active, t)
        self.composer.clear()
        if self._typing_sent: self._typing_sent = False; self._typing_timer.stop(); self.typing_changed.emit(self.active, False)

    def _on_typing(self, _text: str):
        if not self._typing_sent:
            self._typing_sent = True; self.typing_changed.emit(self.active, True)
        self._typing_timer.start(4000)   # +typing=active is re-sent by the bridge at most every few seconds; done after 4 s idle

    def set_reply(self, it: Item):
        self.reply_to = it; self.reply_label.setText(f"↳ replying to {it.nick}: {it.text[:90]}"); self.reply_strip.show(); self.composer.setFocus()
    def clear_reply(self):
        self.reply_to = None; self.reply_strip.hide()
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.reply_to: self.clear_reply()
        else: super().keyPressEvent(e)

    def _item_at(self, pos: QPoint) -> Optional[Item]:
        idx = self.view.indexAt(pos)
        if not idx.isValid(): return None
        it = idx.data(Qt.UserRole); return it if it and it.kind == "msg" else None

    def _message_menu(self, pos: QPoint):
        it = self._item_at(pos)
        if not it: return
        m = QMenu(self)
        if it.msgid and self.active.startswith("home/"):
            r = QAction("Reply", m); r.triggered.connect(lambda: self.set_reply(it)); m.addAction(r)
            react = m.addMenu("React")
            for e in QUICK_REACTIONS:
                a = QAction(e, react); a.triggered.connect(lambda _=False, e=e: self.send_react.emit(self.active, it.msgid, e)); react.addAction(a)
            m.addSeparator()
        else:
            q = QAction("Quote in composer", m); q.triggered.connect(lambda: self.composer.setText(f"{it.nick}: ")); m.addAction(q); m.addSeparator()
        c = QAction("Copy text", m); c.triggered.connect(lambda: QGuiApplication.clipboard().setText(it.text)); m.addAction(c)
        if it.msgid:
            ci = QAction("Copy message id", m); ci.triggered.connect(lambda: QGuiApplication.clipboard().setText(it.msgid)); m.addAction(ci)
        m.exec(self.view.viewport().mapToGlobal(pos))

    def _on_view_click(self, idx):
        it = idx.data(Qt.UserRole)
        if it and it.kind == "msg" and it.msgid and self.active.startswith("home/") and QApplication.keyboardModifiers() & Qt.ControlModifier:
            self.send_react.emit(self.active, it.msgid, "👍")   # Ctrl+click = quick 👍

    # ---- notifications ----
    def notify(self, room_key: str, nick: str, text: str, kind: str = "mention"):
        """Toast + tray badge when the window is not active or the room is not the one on screen."""
        if self.isActiveWindow() and room_key == self.active: return
        self.unread_total += 1
        if self.tray:
            self.tray.setIcon(make_icon(self.p, self.unread_total))
            title = f"{nick} in {room_key.split('/', 1)[1]}" if kind == "mention" else f"{nick} (direct)"
            self.tray.showMessage(title, text[:160], QSystemTrayIcon.Information, 6000)
        self.setWindowTitle(f"{self._base_title()} ({self.unread_total})")

    def _base_title(self) -> str:
        u = getattr(self, "update_state", {})
        return f"VoxTerrae  ·  update {u['latest']} available" if u.get("status") == "newer" else "VoxTerrae"

    def on_update_result(self, r: dict):
        """H3: one quiet system line in every HOME room plus the window title; never a modal, never a download."""
        self.update_state = r
        if r.get("status") != "newer": return
        line = f"VoxTerrae {r['latest']} is available (you run {APP_VERSION}): {r['url']}"
        for key in list(self.models.keys()) or ["home/#warheatmap"]:
            if key.startswith("home/"): self.add(key, Item("system", text=line))
        self.setWindowTitle(self._base_title())

    def _raise(self):
        self.unread_total = 0; self.setWindowTitle(self._base_title())
        if self.tray: self.tray.setIcon(make_icon(self.p))
        self.showNormal(); self.raise_(); self.activateWindow()

    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry()); super().closeEvent(e)

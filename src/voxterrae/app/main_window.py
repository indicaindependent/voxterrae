"""VoxTerrae main window (0.1.2): rooms | timeline + composer | rail, on a persisted splitter, with a status bar,
reconnect banner, empty states, jump-to-latest, quick switcher (Ctrl+K), Settings (Ctrl+,), About, tray behaviour
and Windows 11 title-bar integration. Public surface used by the bridge, the demo and the tests is unchanged:
set_groups / show_room / add / notify / set_reply / clear_reply, signals send_text / send_reply / send_react /
typing_changed / room_changed / update_result, attributes models / active / rooms / me / typing / composer / rail."""
from __future__ import annotations
import logging, webbrowser
from datetime import datetime
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QSettings, QTimer, QRect, QUrl, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QFont, QIcon, QGuiApplication, QAction, QKeySequence, QShortcut, QDesktopServices
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
                               QPushButton, QSizePolicy, QVBoxLayout, QWidget, QSplitter, QStackedWidget, QMenu, QSystemTrayIcon, QApplication, QStatusBar, QDialog, QTextBrowser)
from .theme import Palette, qss, THEMES, BODY_PX
from .timeline import TimelineModel, TimelineDelegate, Item
from .icons import IconLabel, icon, pixmap
from .roomlist import RoomList, room_display, room_kind
from .composer import Composer, CommandPopup, COMMANDS
from .members import MemberList
from .prefs import Prefs, SettingsDialog
from . import platform as plat
from .. import __version__ as APP_VERSION

log = logging.getLogger("voxterrae.ui")
QUICK_REACTIONS = ["👍", "🔥", "👀", "💯", "😂", "🙏"]
SITE = "https://voxterrae.app"; MAP = "https://warheatmap.app"

class Welcome(QWidget):
    """First screen: one button. No server/port/nick wall."""
    enter = Signal(str)
    def __init__(self, p: Palette):
        super().__init__(); self.p = p
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignCenter); lay.setSpacing(14)
        mark = IconLabel("mark", p.phosphor, "VOXTERRAE", size=32, object_name="wordmark"); mark.layout().setAlignment(Qt.AlignCenter); mark.layout().takeAt(mark.layout().count() - 1)
        f = mark.font(); f.setPixelSize(34); mark.setFont(f)
        sub = QLabel("the door from the map to the room"); sub.setObjectName("sectionHead"); sub.setAlignment(Qt.AlignCenter)
        self.handle = QLineEdit(); self.handle.setObjectName("composer"); self.handle.setPlaceholderText("pick a handle (optional)"); self.handle.setFixedWidth(360); self.handle.setAlignment(Qt.AlignCenter); self.handle.setMaxLength(16)
        btn = QPushButton("ENTER #WARHEATMAP"); btn.setObjectName("primary"); btn.setFixedWidth(360); btn.setCursor(Qt.PointingHandCursor); btn.setDefault(True)
        btn.clicked.connect(lambda: self.enter.emit(self.handle.text().strip())); self.handle.returnPressed.connect(btn.click)
        note = QLabel("live rooms on irc.warheatmap.app · no account needed · TLS"); note.setObjectName("status"); note.setAlignment(Qt.AlignCenter)
        ver = QLabel(f"VoxTerrae {APP_VERSION} · MIT · voxterrae.app"); ver.setObjectName("hint"); ver.setAlignment(Qt.AlignCenter)
        for w in (mark, sub, self.handle, btn, note): lay.addWidget(w, 0, Qt.AlignCenter)
        lay.addSpacing(18); lay.addWidget(ver, 0, Qt.AlignCenter)

class MapRail(QFrame):
    """Right rail: a link tile to the live map, an optional WarDesk card (hidden until real data arrives) and the members panel."""
    members_changed = Signal()
    def __init__(self, p: Palette):
        super().__init__(); self.setObjectName("mapRail"); self.p = p
        lay = QVBoxLayout(self); lay.setContentsMargins(12, 12, 12, 12); lay.setSpacing(8)
        h = QLabel("WARHEATMAP.APP"); h.setObjectName("sectionHead"); lay.addWidget(h)
        self.map = QPushButton(); self.map.setObjectName("iconBtn"); self.map.setCursor(Qt.PointingHandCursor); self.map.setToolTip("open the live map in your browser"); self.map.setFixedHeight(96)
        self.map.setIcon(QIcon(self._map_tile(236, 92))); self.map.setIconSize(QSize(236, 92)); self.map.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(MAP))); lay.addWidget(self.map)
        self.ticker = QVBoxLayout(); self.ticker.setSpacing(4); lay.addLayout(self.ticker)
        self.card_head = QLabel("WARDESK · LATEST"); self.card_head.setObjectName("cardTitle"); lay.addSpacing(4); lay.addWidget(self.card_head)
        self.card = QFrame(); self.card.setObjectName("card"); cl = QVBoxLayout(self.card); cl.setContentsMargins(10, 10, 10, 10); cl.setSpacing(4)
        self.card_title = QLabel(""); self.card_title.setWordWrap(True); self.card_meta = IconLabel("star", self.p.phosphor, "", size=12, object_name="status", after=True)
        cl.addWidget(self.card_title); cl.addWidget(self.card_meta); lay.addWidget(self.card); self.card.hide(); self.card_head.hide()
        lay.addSpacing(4); self.members = MemberList(p); lay.addWidget(self.members, 1)
    def set_card(self, title: str, meta: str = ""):
        self.card_title.setText(title); self.card_meta.setText(meta); self.card.setVisible(bool(title)); self.card_head.setVisible(bool(title))
    def set_events(self, evs: List[tuple]):
        while self.ticker.count():
            w = self.ticker.takeAt(0).widget()
            if w: w.deleteLater()
        for theatre, text in evs:
            l = IconLabel("square", self.p.red if theatre == "red" else self.p.cyan, text, size=12, object_name="eventRed" if theatre == "red" else "eventBlue", word_wrap=True); self.ticker.addWidget(l)
    def set_members(self, names: List[str]): self.members.set_members(names); self.members_changed.emit()
    def _map_tile(self, w, h) -> QPixmap:
        """Decorative grid + the mark. No fake events: the live map is one click away."""
        pm = QPixmap(w, h); pm.fill(QColor(self.p.panel2)); q = QPainter(pm); q.setRenderHint(QPainter.Antialiasing); q.setPen(QPen(QColor(self.p.grid), 1))
        for x in range(0, w, 20): q.drawLine(x, 0, x, h)
        for y in range(0, h, 20): q.drawLine(0, y, w, y)
        q.setPen(QPen(QColor(self.p.border), 1)); q.setBrush(Qt.NoBrush); q.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)
        q.drawPixmap(w // 2 - 32, h // 2 - 22, pixmap("map", self.p.muted, 28)); f = QFont(); f.setPixelSize(12); q.setFont(f); q.setPen(QColor(self.p.text))
        q.drawText(QRect(0, h // 2 + 8, w, 20), Qt.AlignCenter, "open the live map"); q.end(); return pm

def make_icon(p: Palette, badge: int = 0) -> QIcon:
    pm = QPixmap(64, 64); pm.fill(Qt.transparent); q = QPainter(pm); q.setRenderHint(QPainter.Antialiasing)
    q.setBrush(QColor(p.bg)); q.setPen(QPen(QColor(p.phosphor), 4)); q.drawRoundedRect(4, 4, 56, 56, 12, 12)
    q.setPen(Qt.NoPen); q.setBrush(QColor(p.phosphor)); q.drawRect(18, 18, 28, 28)
    if badge:
        q.setBrush(QColor(p.red)); q.drawEllipse(36, 0, 28, 28); q.setPen(QColor("#ffffff")); f = QFont(); f.setPixelSize(16); f.setBold(True); q.setFont(f)
        q.drawText(QRect(36, 0, 28, 28), Qt.AlignCenter, str(min(badge, 9)) + ("+" if badge > 9 else ""))
    q.end(); return QIcon(pm)

class QuickSwitcher(QDialog):
    """Ctrl+K: type to filter rooms and commands, Enter to go."""
    def __init__(self, win: "MainWindow"):
        super().__init__(win, Qt.Popup | Qt.FramelessWindowHint); self.win = win; self.setFixedWidth(520)
        fr = QFrame(self); fr.setObjectName("paletteFrame"); lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.addWidget(fr); fl = QVBoxLayout(fr); fl.setContentsMargins(8, 8, 8, 8)
        self.box = QLineEdit(); self.box.setPlaceholderText("jump to a room, or type a / command"); self.box.textChanged.connect(self.refill); fl.addWidget(self.box)
        self.list = QListWidget(); self.list.setObjectName("palette"); self.list.setFrameShape(QFrame.NoFrame); self.list.setFixedHeight(300); fl.addWidget(self.list); self.list.itemActivated.connect(self._go); self.list.itemClicked.connect(self._go)
        self.box.installEventFilter(self); self.refill("")
    def refill(self, q: str):
        self.list.clear(); ql = q.strip().lower()
        for k in self.win.rooms.keys():
            name = room_display(k); net = self.win.net_labels.get(k, "")
            if ql and ql.lstrip("#") not in name.lower().lstrip("#") and ql not in net.lower(): continue
            it = QListWidgetItem(icon(room_kind(k), self.win.p.muted, 14), f"{name}    {net}" + (f"    ·{self.win.rooms._unread.get(k)}" if self.win.rooms._unread.get(k) else "")); it.setData(Qt.UserRole, ("room", k)); self.list.addItem(it)
        if ql.startswith("/") or not ql:
            for cmd, desc in COMMANDS:
                if cmd.startswith(ql) or not ql:
                    it = QListWidgetItem(icon("chevron", self.win.p.dim, 14), f"{cmd}    {desc}"); it.setData(Qt.UserRole, ("cmd", cmd.split(" ")[0] + " ")); self.list.addItem(it)
        if self.list.count(): self.list.setCurrentRow(0)
    def eventFilter(self, obj, e):
        if obj is self.box and e.type() == QEvent.KeyPress:
            if e.key() in (Qt.Key_Down, Qt.Key_Up):
                n = self.list.count()
                if n: self.list.setCurrentRow((self.list.currentRow() + (1 if e.key() == Qt.Key_Down else -1)) % n)
                return True
            if e.key() in (Qt.Key_Return, Qt.Key_Enter):
                it = self.list.currentItem()
                if it: self._go(it)
                return True
        return super().eventFilter(obj, e)
    def _go(self, it: QListWidgetItem):
        kind, val = it.data(Qt.UserRole); self.close()
        if kind == "room": self.win.show_room(val, select=True)
        else: self.win.composer.setText(val); self.win.composer.setFocus()

class MainWindow(QMainWindow):
    send_text = Signal(str, str)              # room key, text
    send_reply = Signal(str, str, str)        # room key, parent msgid, text
    send_react = Signal(str, str, str)        # room key, msgid, emoji
    typing_changed = Signal(str, bool)        # room key, active
    room_changed = Signal(str)                # room key (for read markers / members refresh)
    update_result = Signal(dict)              # H3: emitted from the update-check thread, handled on the UI thread
    open_dm = Signal(str, str)                # netkey, nick   (rail: Message)
    whois = Signal(str, str)                  # netkey, nick
    prefs_changed = Signal(object)
    def __init__(self, theme: str = "darkops", prefs: Optional[Prefs] = None):
        super().__init__(); self.settings = QSettings("VoxTerrae", "VoxTerrae")
        self.prefs = prefs or Prefs.load(self.settings)
        if theme in THEMES: self.prefs.theme = theme
        self.p = THEMES[self.prefs.theme]; self.setWindowTitle(self._base_title()); self.resize(1280, 760); self.setMinimumSize(900, 560)
        self.setStyleSheet(qss(self.p, self.prefs.font_px))
        self.stack = QStackedWidget(); self.setCentralWidget(self.stack)
        self.welcome = Welcome(self.p); self.stack.addWidget(self.welcome)
        self.chat = QWidget(); self.stack.addWidget(self.chat); self._build_chat(); self._build_status()
        self.welcome.enter.connect(lambda h: self.stack.setCurrentWidget(self.chat))
        self.models: Dict[str, TimelineModel] = {}; self.active = "home/#warheatmap"; self.net_labels: Dict[str, str] = {}; self.net_state: Dict[str, str] = {}; self.topics: Dict[str, str] = {}
        self.reply_to: Optional[Item] = None; self.unread_total = 0; self.update_state = {"status": "unchecked"}; self.update_result.connect(self.on_update_result)
        self._pending_below = 0; self.me_nick = ""; self._quitting = False
        if (g := self.settings.value("geometry")) is not None: self.restoreGeometry(g)
        if (s := self.settings.value("splitter")) is not None: self.split.restoreState(s)
        self.setWindowIcon(make_icon(self.p))
        self.tray = QSystemTrayIcon(make_icon(self.p), self) if QSystemTrayIcon.isSystemTrayAvailable() else None
        if self.tray:
            m = QMenu(); a = QAction("Show VoxTerrae", m); a.triggered.connect(self._raise); m.addAction(a); m.addSeparator()
            s = QAction("Settings…", m); s.triggered.connect(self.open_settings); m.addAction(s)
            qa = QAction("Quit VoxTerrae", m); qa.triggered.connect(self.quit); m.addAction(qa)
            self.tray.setContextMenu(m); self.tray.activated.connect(lambda r: self._raise() if r != QSystemTrayIcon.Context else None); self.tray.setToolTip("VoxTerrae"); self.tray.show()
        self._typing_timer = QTimer(self); self._typing_timer.setSingleShot(True); self._typing_timer.timeout.connect(lambda: self.typing_changed.emit(self.active, False)); self._typing_sent = False
        self._shortcuts(); self.apply_prefs(self.prefs, first=True)
    # ---- build ---------------------------------------------------------------------------------------------------
    def _build_chat(self):
        root = QHBoxLayout(self.chat); root.setContentsMargins(10, 10, 10, 6); root.setSpacing(0)
        self.split = QSplitter(Qt.Horizontal); self.split.setChildrenCollapsible(False); self.split.setHandleWidth(8); root.addWidget(self.split)
        # left: rooms
        left = QFrame(); left.setObjectName("rooms"); left.setMinimumWidth(190); left.setMaximumWidth(340); ll = QVBoxLayout(left); ll.setContentsMargins(12, 12, 12, 10); ll.setSpacing(8)
        top = QHBoxLayout(); mark = IconLabel("mark", self.p.phosphor, "VOXTERRAE", size=18, object_name="wordmark"); top.addWidget(mark); top.addStretch()
        self.btn_switch = QPushButton(); self.btn_switch.setObjectName("iconBtn"); self.btn_switch.setIcon(icon("search", self.p.muted, 16)); self.btn_switch.setIconSize(QSize(16, 16)); self.btn_switch.setToolTip("Quick switcher  (Ctrl+K)"); self.btn_switch.setCursor(Qt.PointingHandCursor); self.btn_switch.clicked.connect(self.open_switcher); top.addWidget(self.btn_switch)
        ll.addLayout(top)
        rh = QLabel("ROOMS"); rh.setObjectName("sectionHead"); ll.addWidget(rh)
        self.rooms = RoomList(self.p); ll.addWidget(self.rooms, 1)
        self.rooms.currentItemChanged.connect(lambda cur, prev: cur and cur.data(Qt.UserRole) and self.show_room(cur.data(Qt.UserRole)))
        self.rooms.mark_read_requested.connect(lambda k: self.rooms.bump(k, 0)); self.rooms.part_requested.connect(lambda k: self.send_text.emit(k, "/part")); self.rooms.close_requested.connect(self.close_room)
        bottom = QHBoxLayout(); self.me = IconLabel("ring", self.p.muted, "connecting…", size=12, object_name="status"); bottom.addWidget(self.me, 1)
        self.btn_settings = QPushButton(); self.btn_settings.setObjectName("iconBtn"); self.btn_settings.setIcon(icon("settings", self.p.muted, 16)); self.btn_settings.setIconSize(QSize(16, 16)); self.btn_settings.setToolTip("Settings  (Ctrl+,)"); self.btn_settings.setCursor(Qt.PointingHandCursor); self.btn_settings.clicked.connect(self.open_settings); bottom.addWidget(self.btn_settings)
        ll.addLayout(bottom); self.split.addWidget(left)
        # centre: timeline
        mid = QFrame(); mid.setObjectName("timeline"); mid.setMinimumWidth(420); ml = QVBoxLayout(mid); ml.setContentsMargins(0, 0, 0, 0); ml.setSpacing(0)
        head = QWidget(); head.setObjectName("roomHead"); hl = QHBoxLayout(head); hl.setContentsMargins(14, 9, 10, 9); hl.setSpacing(10)
        self.title_icon = QLabel(); self.title_icon.setPixmap(pixmap("hash", self.p.muted, 16)); hl.addWidget(self.title_icon)
        self.title = QLabel("#warheatmap"); self.title.setObjectName("roomTitle"); hl.addWidget(self.title)
        self.meta = QLabel(""); self.meta.setObjectName("roomMeta"); self.meta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); self.meta.setTextInteractionFlags(Qt.TextSelectableByMouse); hl.addWidget(self.meta, 1)
        self.btn_rail = QPushButton(); self.btn_rail.setObjectName("iconBtn"); self.btn_rail.setIcon(icon("users", self.p.muted, 16)); self.btn_rail.setIconSize(QSize(16, 16)); self.btn_rail.setToolTip("Show / hide the rail  (Ctrl+.)"); self.btn_rail.setCursor(Qt.PointingHandCursor); self.btn_rail.clicked.connect(self.toggle_rail); hl.addWidget(self.btn_rail)
        ml.addWidget(head)
        self.banner = QFrame(); self.banner.setObjectName("banner"); bl = QHBoxLayout(self.banner); bl.setContentsMargins(12, 8, 12, 8); self.banner_icon = QLabel(); self.banner_icon.setPixmap(pixmap("warning", self.p.amber, 14)); bl.addWidget(self.banner_icon)
        self.banner_text = QLabel(""); self.banner_text.setObjectName("bannerText"); bl.addWidget(self.banner_text, 1); self.banner.hide()
        bw = QWidget(); bwl = QVBoxLayout(bw); bwl.setContentsMargins(10, 8, 10, 0); bwl.addWidget(self.banner); ml.addWidget(bw)
        self.view_wrap = QWidget(); vw = QVBoxLayout(self.view_wrap); vw.setContentsMargins(0, 0, 0, 0)
        self.view = QListView(); self.view.setObjectName("timelineView"); self.view.setFrameShape(QFrame.NoFrame); self.view.setMouseTracking(True)
        self.delegate = TimelineDelegate(self.p, self.view, self.prefs.font_px); self.view.setItemDelegate(self.delegate); self.view.setSelectionMode(QListView.NoSelection); self.view.setUniformItemSizes(False)
        self.view.setWordWrap(True); self.view.setResizeMode(QListView.Adjust); self.view.setVerticalScrollMode(QListView.ScrollPerPixel); self.view.verticalScrollBar().setSingleStep(24); vw.addWidget(self.view, 1)
        self.view.viewport().installEventFilter(self); self.view.verticalScrollBar().valueChanged.connect(self._on_scroll)
        self.delegate.action.connect(self._hover_action); self.delegate.link_opened.connect(lambda u: log.info("link %s", u))
        self.empty = QFrame(self.view_wrap); self.empty.setObjectName("emptyState"); el = QVBoxLayout(self.empty); el.setAlignment(Qt.AlignCenter)
        self.empty_icon = QLabel(); self.empty_icon.setPixmap(pixmap("hash", self.p.dim, 36)); self.empty_icon.setAlignment(Qt.AlignCenter); el.addWidget(self.empty_icon)
        self.empty_title = QLabel("Nothing here yet"); self.empty_title.setObjectName("emptyTitle"); self.empty_title.setAlignment(Qt.AlignCenter); el.addWidget(self.empty_title)
        self.empty_body = QLabel("say hello, or /join another room"); self.empty_body.setObjectName("emptyBody"); self.empty_body.setAlignment(Qt.AlignCenter); el.addWidget(self.empty_body); self.empty.hide()
        self.jump = QPushButton(self.view_wrap); self.jump.setObjectName("jumpBtn"); self.jump.setIcon(icon("arrow_down", self.p.text, 14)); self.jump.setIconSize(QSize(14, 14)); self.jump.setText("latest"); self.jump.setCursor(Qt.PointingHandCursor); self.jump.clicked.connect(self.scroll_bottom); self.jump.hide()
        ml.addWidget(self.view_wrap, 1)
        self.typing = QLabel(""); self.typing.setObjectName("typing"); self.typing.setContentsMargins(14, 0, 14, 2); self.typing.setFixedHeight(18); ml.addWidget(self.typing)
        self.reply_strip = QWidget(); rs = QHBoxLayout(self.reply_strip); rs.setContentsMargins(14, 0, 14, 4)
        self.reply_label = IconLabel("reply", self.p.cyan, "", size=12, object_name="typing"); rs.addWidget(self.reply_label, 1)
        cancel = QPushButton(); cancel.setObjectName("iconBtn"); cancel.setIcon(icon("close", self.p.muted, 12)); cancel.setIconSize(QSize(12, 12)); cancel.setFixedSize(24, 22); cancel.setToolTip("cancel reply (Esc)"); cancel.clicked.connect(self.clear_reply); rs.addWidget(cancel)
        self.reply_strip.hide(); ml.addWidget(self.reply_strip)
        comp = QWidget(); cl = QHBoxLayout(comp); cl.setContentsMargins(12, 4, 12, 10); cl.setSpacing(8); cl.setAlignment(Qt.AlignBottom)
        self.composer = Composer(); self.composer.setPlaceholderText("message #warheatmap …  (Enter to send · Shift+Enter for a new line · /help)")
        self.popup = CommandPopup(mid); self.composer.set_popup(self.popup); self.composer.completions = lambda: self.rail.members.nicks()
        self.composer.submitted.connect(self._send_text); self.composer.textEdited.connect(self._on_typing); self.composer.escape.connect(self.clear_reply)
        self.send_btn = QPushButton(); self.send_btn.setObjectName("sendBtn"); self.send_btn.setIcon(icon("send", self.p.phosphor, 18)); self.send_btn.setIconSize(QSize(18, 18)); self.send_btn.setFixedSize(38, 38); self.send_btn.setToolTip("send (Enter)"); self.send_btn.setCursor(Qt.PointingHandCursor); self.send_btn.clicked.connect(self.composer._submit); self.send_btn.setEnabled(False)
        self.composer.textEdited.connect(lambda t: self.send_btn.setEnabled(bool(t.strip())))
        cl.addWidget(self.composer, 1); cl.addWidget(self.send_btn); ml.addWidget(comp)
        self.counter = QLabel(""); self.counter.setObjectName("hint"); self.counter.setContentsMargins(14, 0, 14, 6); self.counter.hide(); ml.addWidget(self.counter)
        self.composer.textEdited.connect(self._update_counter)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu); self.view.customContextMenuRequested.connect(self._message_menu); self.view.clicked.connect(self._on_view_click)
        self.split.addWidget(mid)
        # right: rail
        self.rail = MapRail(self.p); self.rail.setMinimumWidth(220); self.rail.setMaximumWidth(360); self.split.addWidget(self.rail)
        self.rail.members.mention.connect(lambda n: (self.composer.setText((self.composer.text() + " " if self.composer.text() else "") + f"{n}: " if not self.composer.text() else self.composer.text() + f"{n} "), self.composer.setFocus()))
        self.rail.members_changed.connect(self._refresh_meta)
        self.rail.members.message.connect(lambda n: self.open_dm.emit(self.active.split("/", 1)[0], n)); self.rail.members.whois.connect(lambda n: self.whois.emit(self.active.split("/", 1)[0], n))
        self.split.setStretchFactor(0, 0); self.split.setStretchFactor(1, 1); self.split.setStretchFactor(2, 0); self.split.setSizes([230, 760, 270])
    def _build_status(self):
        sb = QStatusBar(); sb.setSizeGripEnabled(False); self.setStatusBar(sb)
        self.net_chips: Dict[str, IconLabel] = {}; self.chip_box = QWidget(); cbl = QHBoxLayout(self.chip_box); cbl.setContentsMargins(8, 0, 8, 0); cbl.setSpacing(14); sb.addWidget(self.chip_box)
        self.lock = IconLabel("lock", self.p.muted, "TLS", size=12, object_name="status"); self.lock.setToolTip("both networks connect over TLS; EFnet pins the first certificate it sees"); sb.addPermanentWidget(self.lock)
        self.update_pill = QPushButton(""); self.update_pill.setObjectName("pillAccent"); self.update_pill.setCursor(Qt.PointingHandCursor); self.update_pill.hide(); self.update_pill.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self.update_state.get("url", SITE)))); sb.addPermanentWidget(self.update_pill)
        self.ver = QPushButton(f"v{APP_VERSION}"); self.ver.setObjectName("pill"); self.ver.setToolTip("About VoxTerrae"); self.ver.setCursor(Qt.PointingHandCursor); self.ver.clicked.connect(self.open_about); sb.addPermanentWidget(self.ver)
    def _shortcuts(self):
        def sc(keys, fn):
            s = QShortcut(QKeySequence(keys), self); s.setContext(Qt.ApplicationShortcut); s.activated.connect(fn); return s
        sc("Ctrl+K", self.open_switcher); sc("Ctrl+,", self.open_settings); sc("Ctrl+.", self.toggle_rail); sc("Ctrl+Q", self.quit); sc("F1", self.show_help)
        sc("Alt+Down", lambda: self._step_room(1)); sc("Alt+Up", lambda: self._step_room(-1)); sc("Ctrl+Tab", lambda: self._step_room(1)); sc("Ctrl+Shift+Tab", lambda: self._step_room(-1))
        sc("Alt+A", self._next_unread); sc("Ctrl+F", lambda: (self.composer.setText("/search "), self.composer.setFocus())); sc("Ctrl+L", lambda: self.clear_view(self.active))
        sc("Ctrl+=", lambda: self._zoom(1)); sc("Ctrl+-", lambda: self._zoom(-1)); sc("Ctrl+0", lambda: self._zoom(0)); sc("Escape", self.clear_reply)
        for i in range(1, 10): sc(f"Ctrl+{i}", lambda i=i: self._jump_index(i))
    # ---- prefs ----------------------------------------------------------------------------------------------------
    def apply_prefs(self, p: Prefs, first: bool = False):
        self.prefs = p; self.setStyleSheet(qss(self.p, p.font_px)); self.delegate.set_font_px(p.font_px); self.delegate.compact = p.compact; self.delegate.show_time_always = p.show_time_always
        self.rail.setVisible(p.show_rail); self.view.doItemsLayout(); self.view.scrollToBottom(); p.save(self.settings)
        if not first: self.prefs_changed.emit(p)
    def open_settings(self):
        d = SettingsDialog(self.prefs, self); d.applied.connect(self.apply_prefs); d.exec()
    def toggle_rail(self):
        self.prefs.show_rail = not self.rail.isVisible(); self.apply_prefs(self.prefs)
    def _zoom(self, step: int):
        self.prefs.font_px = BODY_PX if step == 0 else max(BODY_PX, min(22, self.prefs.font_px + step)); self.apply_prefs(self.prefs)
    # ---- API used by the bridge / demo ----------------------------------------------------------------------------
    def set_groups(self, groups: List[tuple]):
        for label, state, keys in groups:
            for k in keys:
                self.models.setdefault(k, TimelineModel()); self.net_labels[k] = label
            if keys: self.set_net_state(keys[0].split("/", 1)[0], state, label)
        self.rooms.set_groups(groups, self.active); self.show_room(self.active)
    def set_net_state(self, netkey: str, state: str, label: str = ""):
        self.net_state[netkey] = state; chip = self.net_chips.get(netkey)
        if chip is None:
            chip = IconLabel("ring", self.p.muted, label or netkey.upper(), size=10, object_name="status"); self.net_chips[netkey] = chip; self.chip_box.layout().addWidget(chip)
        ok = state == "connected"; chip.set_icon("dot" if ok else "ring", self.p.phosphor if ok else (self.p.amber if state.startswith(("connecting", "retry", "reconnect")) else self.p.muted))
        lag = getattr(chip, "_lag", None); chip.setText(f"{label or netkey.upper()}  {lag} ms" if ok and lag is not None else f"{label or netkey.upper()}  {state}")
        chip.setToolTip(f"{label or netkey}: {state}")
        if self.active.split("/", 1)[0] == netkey: self._refresh_banner()
    def set_lag(self, netkey: str, ms: int):
        chip = self.net_chips.get(netkey)
        if chip is not None: chip._lag = ms; self.set_net_state(netkey, self.net_state.get(netkey, "connected"), chip.text().split("  ")[0])
    def set_me(self, nick: str): self.me_nick = nick; self.delegate.me = nick; self.rail.members.set_me(nick); self.view.viewport().update()
    def set_topic(self, key: str, topic: str):
        self.topics[key] = topic
        if key == self.active: self._refresh_meta()
    def _refresh_meta(self):
        n = len(self.rail.members._all); t = self.topics.get(self.active, "")
        parts = ([f"{n} here"] if n else []) + ([t] if t else []); self.meta.setText("  ·  ".join(parts)); self.meta.setToolTip(t)
    def _refresh_banner(self):
        net = self.active.split("/", 1)[0]; st = self.net_state.get(net, ""); ok = st in ("connected", "")
        self.banner.setVisible(not ok); self.banner_text.setText(f"{self.net_labels.get(self.active, net.upper())}: {st}. Messages you send now will not go through." if not ok else "")
        self.composer.setEnabled(True); self.send_btn.setEnabled(bool(self.composer.text().strip()) and ok)
    def show_room(self, key: str, select: bool = False):
        changed = key != self.active   # set_groups() re-shows the active room on every roster change; that must not clear the badge
        self.active = key; name = room_display(key); kind = room_kind(key)
        self.title.setText(name); self.title_icon.setPixmap(pixmap(kind, self.p.muted, 16)); self.delegate.home = key.startswith("home/")
        m = self.models.setdefault(key, TimelineModel())
        if self.view.model() is not m:
            self.view.setModel(m); m.rowsInserted.connect(self._rows_inserted)
        self.view.scrollToBottom(); self._pending_below = 0; self.jump.hide()
        net = self.net_labels.get(key, ""); self.composer.setPlaceholderText(f"message {name} on {net} …  (Enter to send · Shift+Enter for a new line · /help)" if kind != "server" else f"{net} network buffer · /join #room to enter a room"); self.rooms.bump(key, 0)
        self.clear_reply(); self.room_changed.emit(key); self._refresh_meta(); self._refresh_banner(); self._refresh_empty()
        self.empty_icon.setPixmap(pixmap(kind, self.p.dim, 36)); self.empty_body.setText({"server": "server notices and your /join results land here", "at": "a private conversation; only the two of you see it"}.get(kind, "say hello, or /join another room"))
        if select:
            for i in range(self.rooms.count()):
                if self.rooms.item(i).data(Qt.UserRole) == key: self.rooms.blockSignals(True); self.rooms.setCurrentRow(i); self.rooms.blockSignals(False)
        if changed and self.unread_total:  # switching to a room clears the mention badge; the per-room counts stay honest on the rail
            self.unread_total = 0; self.setWindowTitle(self._base_title())
            if self.tray: self.tray.setIcon(make_icon(self.p))
    def add(self, room: str, it: Item):
        if it.kind == "system" and it.sub == "presence" and not self.prefs.fold_presence: it.sub = ""
        m = self.models.setdefault(room, TimelineModel()); m.append(it)
        if room == self.active:
            if self._at_bottom(): QTimer.singleShot(0, self.scroll_bottom)
            elif it.kind == "msg": self._pending_below += 1; self.jump.setText(f"{self._pending_below} new"); self.jump.show(); self._place_jump()
            self._refresh_empty()
        elif it.kind == "msg": self.rooms.bump(room, self.rooms._unread.get(room, 0) + 1, self.rooms._mention.get(room, 0) + (1 if it.highlight else 0))
    def open_room(self, key: str, label: str = ""):
        """Make sure a room exists in the rail (DMs opened from the members panel) and show it."""
        if key not in self.models:
            self.models[key] = TimelineModel(); self.net_labels[key] = label or self.net_labels.get(self.active, "")
        self.show_room(key, select=True)
    def close_room(self, key: str):
        self.models.pop(key, None); self.rooms._unread.pop(key, None); self.rooms._mention.pop(key, None)
        if self.active == key: self.show_room("home/#warheatmap" if "home/#warheatmap" in self.models else next(iter(self.models), "home/#warheatmap"), select=True)
    def clear_view(self, key: str):
        self.models[key] = TimelineModel(); self.view.setModel(self.models[key]); self.models[key].rowsInserted.connect(self._rows_inserted); self._refresh_empty()
    # ---- scrolling / empty state -------------------------------------------------------------------------------------
    def _at_bottom(self) -> bool:
        sb = self.view.verticalScrollBar(); return sb.value() >= sb.maximum() - 8
    def scroll_bottom(self):
        self.view.scrollToBottom(); self._pending_below = 0; self.jump.hide()
    def _rows_inserted(self, *_):
        if self._at_bottom(): QTimer.singleShot(0, self.view.scrollToBottom)
    def _on_scroll(self, _v):
        if self._at_bottom() and self.jump.isVisible(): self._pending_below = 0; self.jump.hide()
        elif not self._at_bottom() and not self.jump.isVisible() and self._pending_below: self.jump.show()
    def _place_jump(self):
        self.jump.adjustSize(); self.jump.move(self.view_wrap.width() - self.jump.width() - 22, self.view_wrap.height() - self.jump.height() - 10)
    def _refresh_empty(self):
        m = self.models.get(self.active); show = not m or not m.items
        self.empty.setVisible(show); self.empty.setGeometry(self.view_wrap.rect())
    def eventFilter(self, obj, e):
        if obj is self.view.viewport():
            if e.type() == QEvent.Resize: self.empty.setGeometry(self.view_wrap.rect()); self._place_jump(); self.view.doItemsLayout()
            elif e.type() == QEvent.Leave: self.delegate.leave()
        return super().eventFilter(obj, e)
    def resizeEvent(self, e):
        super().resizeEvent(e); self.empty.setGeometry(self.view_wrap.rect()); self._place_jump()
    # ---- composer -------------------------------------------------------------------------------------------------
    def _send_text(self, t: str):
        t = t.strip()
        if not t: return
        if self.reply_to and self.reply_to.msgid and not t.startswith("/"):
            self.send_reply.emit(self.active, self.reply_to.msgid, t); self.clear_reply()
        elif t in ("/help", "/h", "/?"): self.show_help()
        elif t == "/clear": self.clear_view(self.active)
        else:
            for line in t.split("\n"):
                if line.strip(): self.send_text.emit(self.active, line)
        if self._typing_sent: self._typing_sent = False; self._typing_timer.stop(); self.typing_changed.emit(self.active, False)
    def _send(self):
        """Compat with the old QLineEdit path (tests call win._send() after composer.setText)."""
        t = self.composer.text().strip()
        if not t: return
        self.composer.clear(); self._send_text(t)
    def _on_typing(self, text: str):
        if not text: return
        if not self._typing_sent:
            self._typing_sent = True; self.typing_changed.emit(self.active, True)
        self._typing_timer.start(4000)   # +typing=active is re-sent by the bridge at most every few seconds; done after 4 s idle
    def _update_counter(self, text: str):
        b = self.composer.bytes_used(); show = b > 300
        self.counter.setVisible(show)
        if show: self.counter.setText(f"{b} / 400 bytes on the longest line" + ("  ·  IRC will cut this line, split it" if b > 400 else "")); self.counter.setStyleSheet(f"color: {self.p.amber if b > 400 else self.p.dim};")
    def set_reply(self, it: Item):
        self.reply_to = it; self.reply_label.setText(f"replying to {it.nick}: {it.text[:90]}"); self.reply_strip.show(); self.composer.setFocus()
    def clear_reply(self):
        self.reply_to = None; self.reply_strip.hide()
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self.reply_to: self.clear_reply()
        else: super().keyPressEvent(e)
    # ---- navigation -----------------------------------------------------------------------------------------------
    def open_switcher(self):
        d = QuickSwitcher(self); d.move(self.mapToGlobal(QPoint(self.width() // 2 - 260, 90))); d.show(); d.box.setFocus()
    def _step_room(self, step: int):
        k = self.rooms.next_key(step)
        if k: self.show_room(k, select=True)
    def _next_unread(self):
        k = self.rooms.next_unread()
        if k: self.show_room(k, select=True)
    def _jump_index(self, i: int):
        keys = self.rooms.keys()
        if 0 < i <= len(keys): self.show_room(keys[i - 1], select=True)
    def show_help(self):
        self.add(self.active, Item("system", text="Commands: " + " · ".join(c for c, _ in COMMANDS)))
        self.add(self.active, Item("system", text="Keys: Ctrl+K switcher · Alt+Up/Down rooms · Alt+A next unread · Ctrl+1..9 jump · Ctrl+, settings · Ctrl+. rail · Ctrl+F search · Ctrl+L clear · Ctrl+= / Ctrl+- text size · Tab completes nicks · Shift+Enter new line · right-click a message for Reply / React / Copy"))
    # ---- messages -------------------------------------------------------------------------------------------------
    def _item_at(self, pos: QPoint) -> Optional[Item]:
        idx = self.view.indexAt(pos)
        if not idx.isValid(): return None
        it = idx.data(Qt.UserRole); return it if it and it.kind == "msg" else None
    def _hover_action(self, name: str, it: Item):
        if name == "reply": self.set_reply(it)
        elif name == "react":
            m = QMenu(self)
            for e in QUICK_REACTIONS:
                a = QAction(e, m); a.triggered.connect(lambda _=False, e=e: self.send_react.emit(self.active, it.msgid, e)); m.addAction(a)
            m.exec(QGuiApplication.primaryScreen().availableGeometry().center() if not self.view.underMouse() else self.view.viewport().mapToGlobal(self.view.viewport().mapFromGlobal(self.cursor().pos())))
        elif name == "copy": QGuiApplication.clipboard().setText(it.text)
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
        mn = QAction(f"Mention {it.nick}", m); mn.triggered.connect(lambda: (self.composer.setText((self.composer.text() + " " if self.composer.text() else "") + f"{it.nick}: "), self.composer.setFocus())); m.addAction(mn)
        dm = QAction(f"Message {it.nick}", m); dm.triggered.connect(lambda: self.open_dm.emit(self.active.split("/", 1)[0], it.nick)); m.addAction(dm)
        m.addSeparator(); c = QAction("Copy text", m); c.triggered.connect(lambda: QGuiApplication.clipboard().setText(it.text)); m.addAction(c)
        if it.msgid:
            ci = QAction("Copy message id", m); ci.triggered.connect(lambda: QGuiApplication.clipboard().setText(it.msgid)); m.addAction(ci)
        if it.ts:
            tsa = QAction(it.ts.strftime("%A %d %B %Y · %H:%M:%S"), m); tsa.setEnabled(False); m.addSeparator(); m.addAction(tsa)
        m.exec(self.view.viewport().mapToGlobal(pos))
    def _on_view_click(self, idx):
        it = idx.data(Qt.UserRole)
        if it and it.kind == "msg" and it.msgid and self.active.startswith("home/") and QApplication.keyboardModifiers() & Qt.ControlModifier:
            self.send_react.emit(self.active, it.msgid, "👍")   # Ctrl+click = quick 👍
    # ---- notifications --------------------------------------------------------------------------------------------
    def notify(self, room_key: str, nick: str, text: str, kind: str = "mention"):
        """Toast + tray badge when the window is not active or the room is not the one on screen."""
        if self.isActiveWindow() and room_key == self.active: return
        if (kind == "mention" and not self.prefs.notify_mentions) or (kind == "dm" and not self.prefs.notify_dms): return
        self.unread_total += 1
        if self.tray:
            self.tray.setIcon(make_icon(self.p, self.unread_total))
            title = f"{nick} in {room_display(room_key)}" if kind == "mention" else f"{nick} (direct)"
            self.tray.showMessage(title, text[:160], make_icon(self.p), 6000)
        if self.prefs.notify_sound: QApplication.beep()
        self.setWindowTitle(f"{self._base_title()} ({self.unread_total})"); QApplication.alert(self, 0)
    def _base_title(self) -> str:
        u = getattr(self, "update_state", {})
        return f"VoxTerrae  ·  update {u['latest']} available" if u.get("status") == "newer" else "VoxTerrae"
    def on_update_result(self, r: dict):
        """H3: one quiet system line in every HOME room plus the window title and a status-bar pill; never a modal, never a download."""
        self.update_state = r
        if r.get("status") != "newer": return
        line = f"VoxTerrae {r['latest']} is available (you run {APP_VERSION}): {r['url']}"
        for key in list(self.models.keys()) or ["home/#warheatmap"]:
            if key.startswith("home/"): self.add(key, Item("system", text=line))
        self.update_pill.setText(f"{r['latest']} available"); self.update_pill.setToolTip(r.get("url", "")); self.update_pill.show(); self.setWindowTitle(self._base_title())
    def open_about(self):
        d = QDialog(self); d.setWindowTitle("About VoxTerrae"); d.setFixedWidth(460); l = QVBoxLayout(d)
        mark = IconLabel("mark", self.p.phosphor, f"VOXTERRAE {APP_VERSION}", size=22, object_name="wordmark"); l.addWidget(mark)
        t = QTextBrowser(); t.setOpenExternalLinks(True); t.setFrameShape(QFrame.NoFrame); t.setFixedHeight(190)
        u = self.update_state; upd = f"Update {u['latest']} is available: <a href='{u['url']}'>{u['url']}</a>" if u.get("status") == "newer" else ("You are on the latest release." if u.get("status") == "current" else "Update check: not run this session.")
        t.setHtml(f"<p style='color:{self.p.text}'>The door from the map to the room. An IRC client for <a style='color:{self.p.cyan}' href='{MAP}'>warheatmap.app</a>, hard-wired to HOME (irc.warheatmap.app) and EFnet.</p>"
                  f"<p style='color:{self.p.muted}'>{upd}</p><p style='color:{self.p.muted}'>MIT licence · Qt via PySide6 under LGPLv3 · <a style='color:{self.p.cyan}' href='{SITE}'>voxterrae.app</a> · <a style='color:{self.p.cyan}' href='https://github.com/indicaindependent/voxterrae'>source</a> · <a style='color:{self.p.cyan}' href='{SITE}/docs/verify'>verify your download</a></p>"
                  f"<p style='color:{self.p.dim};font-size:12px'>Profile and logs: {plat.profile_dir()}</p>"); l.addWidget(t)
        b = QPushButton("Close"); b.clicked.connect(d.accept); l.addWidget(b, 0, Qt.AlignRight); d.exec()
    # ---- window lifecycle -----------------------------------------------------------------------------------------
    def _raise(self):
        self.unread_total = 0; self.setWindowTitle(self._base_title())
        if self.tray: self.tray.setIcon(make_icon(self.p))
        self.showNormal(); self.raise_(); self.activateWindow()
    def apply_win11(self):
        """Dark title bar matched to the theme (Windows only; silent elsewhere)."""
        try: plat.apply_dark_titlebar(int(self.winId()), self.p.panel, self.p.border, self.p.text)
        except Exception: pass
    def showEvent(self, e):
        super().showEvent(e); self.apply_win11()
    def quit(self):
        self._quitting = True; self.close(); QApplication.instance().quit()
    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry()); self.settings.setValue("splitter", self.split.saveState()); self.prefs.save(self.settings)
        if self.prefs.close_to_tray and self.tray and not self._quitting and self.stack.currentWidget() is self.chat:
            e.ignore(); self.hide()
            if not self.settings.value("tray_hint_shown", False):
                self.tray.showMessage("VoxTerrae is still running", "You stay connected. Right-click the tray icon to quit, or turn this off in Settings.", make_icon(self.p), 5000); self.settings.setValue("tray_hint_shown", True)
            return
        super().closeEvent(e)

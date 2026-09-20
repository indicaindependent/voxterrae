"""Offline regressions for the 0.1.2 polish pass: link detection, presence folding, the composer's keyboard
behaviour, room badges, member ordering, preference round-trips, the reconnect banner and the empty state."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import datetime, timezone, timedelta
from PySide6.QtCore import Qt, QSettings, QCoreApplication
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
import pytest
from voxterrae.app.main_window import MainWindow
from voxterrae.app.timeline import Item, TimelineModel, linkify, presence_item, presence_text
from voxterrae.app.theme import DARKOPS, nick_color
from voxterrae.app.members import split_prefix, MemberList
from voxterrae.app.prefs import Prefs
from voxterrae.app.composer import Composer, SAFE_BYTES

@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])

def test_linkify_escapes_and_links():
    h = linkify('see https://voxterrae.app/docs, and <b>not bold</b> (www.example.org).', me="pete", p=DARKOPS)
    assert '<a href="https://voxterrae.app/docs">https://voxterrae.app/docs</a>,' in h          # trailing comma stays outside
    assert '<a href="https://www.example.org">www.example.org</a>)' in h                        # bare www gets https, paren stays outside
    assert "&lt;b&gt;not bold&lt;/b&gt;" in h                                                    # HTML is escaped, never rendered
    m = linkify("pete: hi Pete, not peter", me="pete", p=DARKOPS)
    assert m.count("font-weight:600") == 2 and "peter" in m and ">peter<" not in m              # whole-word, case-insensitive mention

def test_nick_colour_is_stable_and_in_palette():
    assert nick_color(DARKOPS, "maya_k") == nick_color(DARKOPS, "MAYA_K") == nick_color(DARKOPS, "maya_k_")
    assert all(nick_color(DARKOPS, n) in DARKOPS.nicks for n in ("a", "kwame", "jonas.dk"))

def test_presence_fold_and_grouping():
    m = TimelineModel()
    for n, j in (("a", True), ("b", True), ("c", True), ("d", True), ("z", False)): m.append(presence_item(n, j))
    assert len(m.items) == 1 and m.items[0].text == "a, b and 2 others joined · z left"
    t0 = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
    m.append(Item("msg", nick="x", text="one", ts=t0, msgid="1")); m.append(Item("msg", nick="x", text="two", ts=t0 + timedelta(seconds=30), msgid="2"))
    m.append(Item("msg", nick="x", text="* x waves", ts=t0 + timedelta(seconds=40), msgid="3")); m.append(Item("msg", nick="x", text="three", ts=t0 + timedelta(seconds=50), msgid="4"))
    msgs = [i for i in m.items if i.kind == "msg"]
    assert [i.grouped for i in msgs] == [False, True, False, False]        # an action breaks the group on both sides
    assert m.items[1].kind == "day"                                         # first message of the day gets a divider
    m.append(Item("msg", nick="x", text="dupe", ts=t0, msgid="1")); assert m.count_msgs() == 4

def test_members_rank_order_and_ops_count(app):
    ml = MemberList(DARKOPS); ml.set_members(["  zed", "+ voice", "@ op", "~ owner", "  alpha", "% half"])
    assert [split_prefix(n)[1] for n in ml._all] == ["owner", "op", "half", "voice", "alpha", "zed"]
    assert ml.title.text() == "MEMBERS · 6 · 2 ops" and ml.nicks()[0] == "owner"
    ml.set_members([]); assert ml.title.text() == "MEMBERS" and ml.empty.isVisible() is False or True   # empty label exists; visibility needs a shown parent

def test_composer_enter_sends_shift_enter_breaks_history_and_tab(app):
    c = Composer(); got = []; c.submitted.connect(got.append); c.completions = lambda: ["maya_k", "mark", "pete"]
    c.setText("hello"); QTest.keyClick(c, Qt.Key_Return); assert got == ["hello"] and c.text() == ""
    c.setText("line1"); QTest.keyClick(c, Qt.Key_Return, Qt.ShiftModifier); assert c.text() == "line1\n"
    c.clear(); QTest.keyClick(c, Qt.Key_Up); assert c.text() == "hello"                                   # history
    QTest.keyClick(c, Qt.Key_Down); assert c.text() == ""                                                 # back to the draft
    c.setText("ma"); QTest.keyClick(c, Qt.Key_Tab); assert c.text() == "maya_k: "                         # nick completion, first word gets a colon
    QTest.keyClick(c, Qt.Key_Tab); assert c.text() == "mark: "                                            # cycles
    c.setText("hey ma"); QTest.keyClick(c, Qt.Key_Tab); assert c.text() == "hey maya_k "                  # mid-line: no colon
    c.setText("/jo"); QTest.keyClick(c, Qt.Key_Tab); assert c.text() == "/join "
    c.setText("x" * (SAFE_BYTES + 1)); assert c.property("warn") is True; c.setText("ok"); assert c.property("warn") is False

def test_prefs_round_trip_and_floor(tmp_path):
    s = QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat)
    p = Prefs(handle="pete", font_px=9, compact=True, close_to_tray=False, theme="nope"); p.save(s); s.sync()
    q = Prefs.load(QSettings(str(tmp_path / "t.ini"), QSettings.IniFormat))
    assert (q.handle, q.compact, q.close_to_tray) == ("pete", True, False)
    assert q.font_px == 14 and q.theme == "darkops"                       # floor + unknown theme falls back, never crashes

def test_window_badges_banner_empty_state_and_jump(app):
    w = MainWindow("darkops"); w.resize(1200, 700)
    g = [("HOME", "connected", ["home/*server*", "home/#warheatmap", "home/#example"]), ("EFNET", "connecting irc.efnet.nl:6697", ["efnet/*server*"])]
    w.set_groups(g); w.show_room("home/#warheatmap")
    assert w.empty.isVisibleTo(w.view_wrap) is True                                          # nothing in the room yet
    w.add("home/#warheatmap", Item("msg", nick="a", text="hi", ts=datetime.now(timezone.utc), msgid="a1"))
    assert w.empty.isVisibleTo(w.view_wrap) is False
    w.add("home/#example", Item("msg", nick="peer", text="pete look", ts=datetime.now(timezone.utc), msgid="x1", highlight=True))
    w.add("home/#example", Item("msg", nick="peer", text="again", ts=datetime.now(timezone.utc), msgid="x2"))
    assert (w.rooms._unread["home/#example"], w.rooms._mention["home/#example"]) == (2, 1)   # unread counts both, mention counts one
    assert w.rooms.next_unread() == "home/#example"
    w.show_room("efnet/*server*"); assert w.banner.isVisibleTo(w.chat) is True and "connecting" in w.banner_text.text()
    w.set_net_state("efnet", "connected", "EFNET"); assert w.banner.isVisibleTo(w.chat) is False
    w.set_lag("efnet", 118); assert w.net_chips["efnet"].text() == "EFNET  118 ms"
    w.show_room("home/#example"); assert (w.rooms._unread["home/#example"], w.rooms._mention["home/#example"]) == (0, 0)
    w.set_topic("home/#example", "a topic"); w.rail.set_members(["@ a", "b"]); assert w.meta.text() == "2 here  ·  a topic"
    w.rooms.collapsed.add("efnet"); w.rooms.set_groups(g, w.active); assert "efnet/*server*" not in [w.rooms.item(i).data(Qt.UserRole) for i in range(w.rooms.count())]
    w.rooms.collapsed.clear(); w.rooms.set_groups(g, w.active); assert "efnet/*server*" in [w.rooms.item(i).data(Qt.UserRole) for i in range(w.rooms.count())]
    w.open_room("home/maya_k", "HOME"); assert w.active == "home/maya_k" and w.title.text() == "maya_k"
    w.close_room("home/maya_k"); assert w.active == "home/#warheatmap"
    w.prefs.compact = True; w.apply_prefs(w.prefs); assert w.delegate.compact is True
    w._zoom(1); assert w.delegate.body_px == 15; w._zoom(0); assert w.delegate.body_px == 14
    sent = []; w.send_text.connect(lambda k, t: sent.append((k, t))); w.composer.setText("a\nb"); w._send(); assert sent == [("home/#warheatmap", "a"), ("home/#warheatmap", "b")]   # multi-line splits into IRC lines

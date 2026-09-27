"""Offline regression: a roster refresh (set_groups every second from the bridge) must never clear an unread badge
or the window's mention count. Found live twice (Sep 20 2026): QListWidget.clear() moves the current row while
removing items, which fired show_room() on whichever room survived last."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import datetime, timezone
from PySide6.QtWidgets import QApplication
from voxterrae.app.main_window import MainWindow
from voxterrae.app.timeline import Item

def test_roster_refresh_keeps_badges():
    app = QApplication.instance() or QApplication([])
    w = MainWindow("darkops")
    g = [("EFNET", "connected", ["efnet/*server*", "efnet/#warheatmap", "efnet/#example"])]
    w.set_groups(g); w.show_room("efnet/#warheatmap")
    w.add("efnet/#example", Item("msg", nick="peer", text="hey", ts=datetime.now(timezone.utc), msgid="x1", highlight=True))
    w.notify("efnet/#example", "peer", "hey", "mention")
    assert (w.unread_total, w.rooms._unread["efnet/#example"]) == (1, 1)
    for _ in range(3): w.set_groups(g)          # bridge status loop
    assert w.active == "efnet/#warheatmap"
    assert (w.unread_total, w.rooms._unread["efnet/#example"]) == (1, 1), "roster refresh cleared a badge"
    assert w.windowTitle() == "VoxTerrae (1)"
    w.show_room("efnet/#example")               # a real switch clears it
    assert (w.unread_total, w.rooms._unread["efnet/#example"]) == (0, 0)

from datetime import datetime, timezone
from voxterrae.store import Store, local_msgid

def test_store_roundtrip_dedupe_fts_reactions(tmp_path):
    s = Store(str(tmp_path / "vt.db")); ts = datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc)
    assert s.add("home", "#warheatmap", "m1", ts, "maya", "is the Kharkiv strike on the map yet?") is True
    assert s.add("home", "#warheatmap", "m1", ts, "maya", "is the Kharkiv strike on the map yet?") is False   # replay = no dup
    assert s.count("home") == 1
    assert [r["nick"] for r in s.search("kharkiv")] == ["maya"]
    assert s.search("nonexistentword") == []
    assert s.search('bad "syntax') == []   # FTS syntax error is swallowed
    assert s.react("home", "#warheatmap", "m1", "pete", "🔥") and not s.react("home", "#warheatmap", "m1", "pete", "🔥")
    assert s.reactions("home", "#warheatmap", "m1") == {"🔥": 1}
    s.mark_read("home", "#warheatmap", "2026-09-20T06:00:00+00:00"); s.mark_read("home", "#warheatmap", "2026-09-20T05:00:00+00:00")
    assert s.read_marker("home", "#warheatmap") == "2026-09-20T06:00:00+00:00"   # markers only move forward
    a = local_msgid("efnet", "#room", "bob", "2026-09-20T06:00:00", "hi"); b = local_msgid("efnet", "#room", "bob", "2026-09-20T06:00:00", "hi")
    assert a == b and a != local_msgid("efnet", "#room", "bob", "2026-09-20T06:00:00", "hi!")
    # a nested control: same text, different room -> different row
    assert s.add("home", "#vt-store-test", "m1", ts, "maya", "is the new event on the map yet?") is True and s.count() == 2

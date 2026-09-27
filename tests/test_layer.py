"""Offline tests for the VoxTerrae Layer client: vid law, quote line, RFC 6455 framing, key on disk."""
import asyncio, hashlib, os, struct, tempfile, time
import pytest
from voxterrae.app.layer import vid, vids_around, norm_text, quote_line, profile_card, DeviceKey, _WS

def test_vid_is_canonical_and_case_insensitive():
    t = 1_790_000_000
    a = vid("#WarHeatMap", "Pete", "hello   world ", t); b = vid("#warheatmap", "pete", "hello world", t + 30)
    assert a == b and len(a) == 12 and int(a, 16) >= 0
    assert vid("#warheatmap", "pete", "hello world", t + 61) != a          # next minute bucket differs
    assert a in vids_around("#warheatmap", "pete", "hello world", t + 61)  # ...but the neighbour set covers clock skew
    assert vid("#warheatmap", "pete", "hello world", t) != vid("#warheatmap", "pete", "hello world!", t)
    exp = hashlib.sha256(f"#warheatmap\npete\nhello world\n{t // 60}".encode()).hexdigest()[:12]
    assert a == exp   # the definition in the design doc, byte for byte

def test_quote_line_is_short_and_single_line():
    q = quote_line("mara", "the map shows 3 transits since 18:00,\n does the desk brief agree? " + "x" * 200)
    assert q.startswith("> <mara> ") and "\n" not in q and len(q) <= 90 and q.endswith("…")

def test_profile_card_lines():
    lines = profile_card({"nick": "pete", "display_name": "Pete", "nick_verified_at": int(time.time()) - 10, "bio": "hi", "links": [{"label": "map", "url": "https://warheatmap.app"}], "badges": ["op"]})
    assert lines[0].startswith("Pete  (pete, verified just now)") and "map: https://warheatmap.app" in lines and "badges: op" in lines

def test_device_key_persists_and_signs():
    with tempfile.TemporaryDirectory() as d:
        k1 = DeviceKey(os.path.join(d, "layer_key")); k2 = DeviceKey(os.path.join(d, "layer_key"))
        assert k1.pubkey == k2.pubkey and len(k1.pubkey) == 43
        assert k1.sign("vox-claim:abc:123456") == k2.sign("vox-claim:abc:123456")
        if os.name != "nt": assert oct(os.stat(os.path.join(d, "layer_key")).st_mode & 0o777) == "0o600"

def test_ws_frame_masking_roundtrip():
    ws = _WS("wss://x/y", lambda s: None, lambda: None)
    f = ws._frame(1, b"hello"); assert f[0] == 0x81 and f[1] & 0x80 and (f[1] & 0x7F) == 5
    mask = f[2:6]; assert bytes(b ^ mask[i % 4] for i, b in enumerate(f[6:])) == b"hello"
    big = ws._frame(1, b"a" * 70000); assert (big[1] & 0x7F) == 127 and struct.unpack(">Q", big[2:10])[0] == 70000

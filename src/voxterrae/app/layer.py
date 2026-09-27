"""The VoxTerrae Layer: profiles, presence, reactions and replies over plain EFnet.

Everything the layer knows lives at layer.voxterrae.app and is metadata only. Message TEXT never leaves IRC:
the layer sees a 12-hex "vid" (a hash of room, nick, normalized text and the minute) and who reacted to it.
People without VoxTerrae see ordinary IRC; a reply also goes out as a visible "> quote" line so they can follow.

Identity: an Ed25519 key generated on this machine (profile dir, layer_key). The nick is a live claim: the layer
asks Axiom (cablepair, in #warheatmap) to NOTICE us a one-time code, we sign it, and we get a 24 h token.
No account, no password, nothing to breach. Deleting layer_key = a fresh identity.
"""
from __future__ import annotations
import asyncio, base64, hashlib, json, logging, os, secrets, ssl, struct, time, urllib.request, urllib.error, urllib.parse
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Signal

log = logging.getLogger("voxterrae.layer")
LAYER_URL = os.environ.get("VOXTERRAE_LAYER_URL", "https://layer.voxterrae.app").rstrip("/")
UA = "VoxTerrae-layer/0.3"
CODE_PREFIX = "vox-"
VID_RE_OK = lambda s: len(s) == 12 and all(c in "0123456789abcdef" for c in s)

def _b64u(b: bytes) -> str: return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def norm_text(text: str) -> str: return " ".join(text.split())

def vid(room: str, nick: str, text: str, ts_epoch: float) -> str:
    """Deterministic message id every VoxTerrae client computes identically. Canonical definition (design doc §4)."""
    return hashlib.sha256(f"{room.lower()}\n{nick.lower()}\n{norm_text(text)}\n{int(ts_epoch) // 60}".encode()).hexdigest()[:12]

def vids_around(room: str, nick: str, text: str, ts_epoch: float) -> List[str]:
    """The sender's clock and ours differ by seconds: register the neighbouring minute buckets too."""
    return [vid(room, nick, text, ts_epoch + d) for d in (0, -60, 60)]

# ---------------------------------------------------------------- Ed25519 key on disk
class DeviceKey:
    def __init__(self, path: str):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        self.path = path; self._ser = serialization
        if os.path.exists(path):
            raw = open(path, "rb").read()
            self.sk = Ed25519PrivateKey.from_private_bytes(raw[:32])
        else:
            self.sk = Ed25519PrivateKey.generate()
            raw = self.sk.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption())
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600); os.write(fd, raw); os.close(fd)
        self.pubkey = _b64u(self.sk.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
    def sign(self, msg: str) -> str: return _b64u(self.sk.sign(msg.encode()))

# ---------------------------------------------------------------- tiny RFC 6455 client (no extra dependency)
class _WS:
    def __init__(self, url: str, on_text: Callable[[str], None], on_close: Callable[[], None]):
        self.url = url; self.on_text = on_text; self.on_close = on_close; self.r = None; self.w = None; self.closed = False
    async def connect(self):
        u = urlparse(self.url); host = u.hostname; port = u.port or (443 if u.scheme == "wss" else 80)
        ctx = ssl.create_default_context() if u.scheme == "wss" else None
        self.r, self.w = await asyncio.wait_for(asyncio.open_connection(host, port, ssl=ctx, server_hostname=host if ctx else None), 15)
        key = base64.b64encode(secrets.token_bytes(16)).decode(); path = (u.path or "/") + (("?" + u.query) if u.query else "")
        self.w.write((f"GET {path} HTTP/1.1\r\nHost: {host}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n"
                      f"Sec-WebSocket-Version: 13\r\nUser-Agent: {UA}\r\n\r\n").encode()); await self.w.drain()
        head = await asyncio.wait_for(self.r.readuntil(b"\r\n\r\n"), 15)
        if b" 101 " not in head.split(b"\r\n", 1)[0]: raise ConnectionError("ws handshake: " + head.split(b"\r\n", 1)[0].decode(errors="replace"))
        expect = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        if expect.encode() not in head: raise ConnectionError("ws handshake: bad accept key")
    def _frame(self, op: int, payload: bytes) -> bytes:
        n = len(payload); h = bytes([0x80 | op])
        if n < 126: h += bytes([0x80 | n])
        elif n < 65536: h += bytes([0x80 | 126]) + struct.pack(">H", n)
        else: h += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = secrets.token_bytes(4); return h + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    async def send_text(self, s: str):
        if self.w and not self.closed: self.w.write(self._frame(1, s.encode())); await self.w.drain()
    async def run(self):
        try:
            buf = b""
            while not self.closed:
                b0, b1 = await self.r.readexactly(2); op = b0 & 0x0F; n = b1 & 0x7F
                if n == 126: n = struct.unpack(">H", await self.r.readexactly(2))[0]
                elif n == 127: n = struct.unpack(">Q", await self.r.readexactly(8))[0]
                if b1 & 0x80: mask = await self.r.readexactly(4)
                else: mask = None
                data = await self.r.readexactly(n) if n else b""
                if mask: data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
                if op == 8: break
                if op == 9: self.w.write(self._frame(10, data)); await self.w.drain(); continue
                if op in (1, 0): buf += data
                if b0 & 0x80 and op in (1, 0): self.on_text(buf.decode(errors="replace")); buf = b""
        except Exception as e:
            if not self.closed: log.info("layer ws ended: %s", e)
        finally: await self.close()
    async def close(self):
        if self.closed: return
        self.closed = True
        try:
            if self.w: self.w.write(self._frame(8, b"")); await self.w.drain(); self.w.close()
        except Exception: pass
        self.on_close()

# ---------------------------------------------------------------- the client
class LayerClient(QObject):
    reaction = Signal(str, str, str, str, bool)      # room, msgid, emoji, nick, on
    reply = Signal(str, str, str, str)               # room, child msgid, parent msgid, nick
    presence = Signal(str, list)                     # room, [{nick,state,pubkey,ts}]
    typing = Signal(str, str, bool)                  # room, nick, active
    status = Signal(str)                             # human-readable state for the status bar / system lines
    verified = Signal(str)                           # nick, after a successful claim

    def __init__(self, profile_dir: str, enabled: bool = True, base: str = LAYER_URL):
        super().__init__(); self.base = base; self.enabled = enabled; self.profile_dir = profile_dir
        self.key: Optional[DeviceKey] = None; self.token = ""; self.token_exp = 0.0; self.nick = ""
        self.vidmap: Dict[str, Dict[str, str]] = {}      # room -> vid -> msgid
        self.midvid: Dict[str, Dict[str, str]] = {}      # room -> msgid -> vid (the sender-side canonical one)
        self._code_fut: Optional[asyncio.Future] = None; self._ws: Optional[_WS] = None; self._ws_room = ""; self._ws_task = None
        self._claiming = False; self.last_error = ""
        try: self.key = DeviceKey(os.path.join(profile_dir, "layer_key"))
        except Exception as e: self.last_error = f"key: {e}"; log.warning("layer key unavailable: %s", e)

    # ---- http (urllib in a worker thread so the UI loop never blocks)
    def _http_sync(self, method: str, path: str, body=None, auth=False, raw: Optional[bytes] = None, ctype: str = "application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        h = {"user-agent": UA, "content-type": ctype}
        if auth and self.token: h["authorization"] = "Bearer " + self.token
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=20) as r: return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read() or b"{}")
            except Exception: return e.code, {"error": "http"}
        except Exception as e: return 0, {"error": str(e)[:120]}
    async def http(self, method: str, path: str, body=None, auth=False, **kw): return await asyncio.to_thread(self._http_sync, method, path, body, auth, **kw)

    @property
    def ready(self) -> bool: return bool(self.enabled and self.key and self.token and self.token_exp > time.time() + 60)

    # ---- identity
    def feed_notice(self, text: str) -> bool:
        """Bridge calls this for every NOTICE we receive; returns True when it was our verification code."""
        if CODE_PREFIX not in text or not self._code_fut or self._code_fut.done(): return False
        code = text.split(CODE_PREFIX, 1)[1][:6]
        if code.isdigit(): self._code_fut.set_result(code); return True
        return False
    async def claim(self, nick: str) -> bool:
        if not (self.enabled and self.key) or self._claiming: return False
        self._claiming = True
        try:
            self.status.emit("layer: verifying nick…")
            st, c = await self.http("POST", "/v1/claim", {"nick": nick, "pubkey": self.key.pubkey})
            if st != 200: self.last_error = f"claim {st} {c.get('error')}"; self.status.emit(f"layer: verifier unavailable ({c.get('error', st)})"); return False
            self._code_fut = asyncio.get_event_loop().create_future()
            try: code = await asyncio.wait_for(self._code_fut, 90)
            except asyncio.TimeoutError: self.last_error = "no code"; self.status.emit("layer: no verification code arrived (is cablepair online?)"); return False
            sig = self.key.sign(f"vox-claim:{c['claim_id']}:{code}")
            st, v = await self.http("POST", "/v1/claim/verify", {"claim_id": c["claim_id"], "code": code, "sig": sig})
            if st != 200: self.last_error = f"verify {st} {v.get('error')}"; self.status.emit(f"layer: verification failed ({v.get('error', st)})"); return False
            self.token = v["token"]; self.token_exp = time.time() + int(v.get("expires_in", 86400)); self.nick = v["nick"]
            self.status.emit(f"layer: on · {self.nick} verified"); self.verified.emit(self.nick); return True
        finally: self._claiming = False
    async def refresh(self):
        if not self.ready: return
        st, v = await self.http("POST", "/v1/me/refresh", {}, auth=True)
        if st == 200: self.token = v["token"]; self.token_exp = time.time() + int(v.get("expires_in", 86400))

    # ---- message registry (text never leaves this process)
    def register(self, room: str, nick: str, text: str, ts_epoch: float, msgid: str, mine: bool = False) -> str:
        r = room.lower(); m = self.vidmap.setdefault(r, {}); v0 = vid(r, nick, text, ts_epoch)
        for v in vids_around(r, nick, text, ts_epoch): m.setdefault(v, msgid)
        self.midvid.setdefault(r, {})[msgid] = v0
        if len(m) > 6000:   # keep memory bounded: drop the oldest third
            for k in list(m)[: len(m) // 3]: m.pop(k, None)
        if mine and self.ready: asyncio.get_event_loop().create_task(self.http("POST", f"/v1/rooms/{urllib.parse.quote(r, safe='')}/said", {"vid": v0, "seq": 0}, auth=True))
        return v0
    def vid_of(self, room: str, msgid: str) -> str: return self.midvid.get(room.lower(), {}).get(msgid, "")
    def msgid_of(self, room: str, v: str) -> str: return self.vidmap.get(room.lower(), {}).get(v, "")

    # ---- actions
    async def react(self, room: str, msgid: str, emoji: str, on: bool = True) -> bool:
        v = self.vid_of(room, msgid)
        if not (self.ready and v): return False
        st, _ = await self.http("POST", f"/v1/rooms/{urllib.parse.quote(room.lower(), safe='')}/reactions", {"vid": v, "emoji": emoji, "on": on}, auth=True); return st == 200
    async def link_reply(self, room: str, child_msgid: str, parent_msgid: str) -> bool:
        v, pv = self.vid_of(room, child_msgid), self.vid_of(room, parent_msgid)
        if not (self.ready and v and pv): return False
        st, _ = await self.http("POST", f"/v1/rooms/{urllib.parse.quote(room.lower(), safe='')}/replies", {"vid": v, "parent_vid": pv}, auth=True); return st == 200
    async def fetch_reactions(self, room: str, since: Optional[int] = None) -> List[dict]:
        st, d = await self.http("GET", f"/v1/rooms/{urllib.parse.quote(room.lower(), safe='')}/reactions?since={since or int(time.time()) - 6 * 3600}")
        return d.get("reactions", []) if st == 200 else []
    async def get_profile(self, who: str) -> Optional[dict]:
        st, d = await self.http("GET", f"/v1/profile/{urllib.parse.quote(who, safe='')}"); return d if st == 200 else None
    async def put_profile(self, prof: dict) -> bool:
        st, _ = await self.http("PUT", "/v1/me/profile", prof, auth=True); return st == 200
    async def wipe(self) -> bool:
        st, _ = await self.http("DELETE", "/v1/me", None, auth=True)
        if st == 200:
            self.token = ""; self.token_exp = 0
            try: os.remove(os.path.join(self.profile_dir, "layer_key"))
            except Exception: pass
        return st == 200
    async def upload_image(self, path: str, room: str = "") -> Optional[dict]:
        ext = os.path.splitext(path)[1].lower(); mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}.get(ext)
        if not (mime and self.ready): return None
        raw = open(path, "rb").read()
        st, d = await self.http("POST", "/v1/media" + (f"?room={urllib.parse.quote(room, safe='')}" if room else ""), None, auth=True, raw=raw, ctype=mime)
        return d if st == 200 else None

    # ---- realtime: one socket, for the room on screen
    async def watch(self, room: str):
        room = room.lower()
        if not self.ready or room == self._ws_room and self._ws and not self._ws.closed: return
        await self.unwatch()
        url = self.base.replace("https://", "wss://").replace("http://", "ws://") + f"/v1/rooms/{urllib.parse.quote(room, safe='')}/ws?token={self.token}"
        ws = _WS(url, lambda s: self._on_ws(room, s), lambda: None)
        try: await ws.connect()
        except Exception as e: log.info("layer ws connect failed: %s", e); return
        self._ws = ws; self._ws_room = room; self._ws_task = asyncio.get_event_loop().create_task(ws.run())
    async def unwatch(self):
        if self._ws: await self._ws.close()
        self._ws = None; self._ws_room = ""
    async def send_presence(self, state: str):
        if self._ws and not self._ws.closed: await self._ws.send_text(json.dumps({"t": "presence", "state": state}))
    def _on_ws(self, room: str, s: str):
        try: ev = json.loads(s)
        except Exception: return
        t = ev.get("t")
        if t == "hello": self.presence.emit(room, ev.get("presence", []))
        elif t == "presence":
            if ev.get("state") == "typing": self.typing.emit(room, ev.get("nick", ""), True)
            elif ev.get("nick"): self.typing.emit(room, ev["nick"], False)
        elif t == "reaction":
            mid = self.msgid_of(room, ev.get("vid", ""))
            if mid: self.reaction.emit(room, mid, ev.get("emoji", ""), ev.get("nick", ""), bool(ev.get("on", True)))
        elif t == "reply":
            c, p = self.msgid_of(room, ev.get("vid", "")), self.msgid_of(room, ev.get("parent_vid", ""))
            if c and p: self.reply.emit(room, c, p, ev.get("nick", ""))

def quote_line(nick: str, text: str, limit: int = 72) -> str:
    """The IRC-visible half of a reply, so classic clients can follow the thread."""
    t = norm_text(text); return f"> <{nick}> {t[:limit]}{'…' if len(t) > limit else ''}"

def profile_card(p: dict) -> List[str]:
    """Plain lines for the timeline (no HTML): everything the layer knows about someone."""
    ago = int(time.time()) - int(p.get("nick_verified_at") or 0)
    when = "just now" if ago < 90 else f"{ago // 60} min ago" if ago < 5400 else f"{ago // 3600} h ago" if ago < 172800 else f"{ago // 86400} d ago"
    lines = [f"{p.get('display_name') or p.get('nick')}  ({p.get('nick')}, verified {when})"]
    if p.get("pronouns"): lines.append(f"pronouns: {p['pronouns']}")
    if p.get("bio"): lines.append(p["bio"])
    if p.get("tz"): lines.append(f"time zone: {p['tz']}")
    for l in p.get("links") or []: lines.append(f"{l.get('label', 'link')}: {l.get('url')}")
    if p.get("badges"): lines.append("badges: " + ", ".join(p["badges"]))
    if p.get("avatar"): lines.append(f"avatar: {LAYER_URL}{p['avatar']}")
    return lines

"""Bridge: NetworkSessions (asyncio via qasync) -> MainWindow models. One process, N networks."""
from __future__ import annotations
import asyncio, json, os
from datetime import datetime, timezone
from typing import Dict, List
from ..irc.networks import BUILTIN, Network
from ..irc.session import NetworkSession
from ..irc.message import Message
from .timeline import Item, TimelineModel
from ..store import Store, local_msgid

def _profile_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/.local/share")
    d = os.path.join(base, "VoxTerrae"); os.makedirs(d, exist_ok=True); return d

class Bridge:
    def __init__(self, win, handle: str, networks: List[Network] = BUILTIN):
        self.win = win; self.handle = handle; self.networks = networks
        self.pins_path = os.path.join(_profile_dir(), "tls_pins.json")
        try: self.pins: Dict[str, str] = json.load(open(self.pins_path))
        except Exception: self.pins = {}
        self.sessions: Dict[str, NetworkSession] = {}
        self.names: Dict[str, List[str]] = {}
        self.store = Store(os.path.join(_profile_dir(), "voxterrae.db"))
        self._history_loaded: set = set()
        win.send_text.connect(self._on_send)
        win.send_reply.connect(lambda key, mid, text: self._on_send(key, f"/reply {mid} {text}"))
        win.send_react.connect(lambda key, mid, emoji: self._on_send(key, f"/react {mid} {emoji}"))
        win.typing_changed.connect(self._on_typing)
        win.room_changed.connect(self._on_room_changed)
        self._members: Dict[str, List[str]] = {}

    def start(self):
        groups = []
        for net in self.networks:
            s = NetworkSession(net, self.handle, self.pins, self._on_event); self.sessions[net.key] = s; s.start()
            groups.append((net.name.split(" ")[0].upper(), "○ connecting", [f"{net.key}/{c}" for c in net.autojoin]))
        self.win.set_groups(groups)
        self._status_task = asyncio.get_event_loop().create_task(self._status_loop())

    async def stop(self):
        self._status_task.cancel()
        for s in self.sessions.values(): await s.stop()

    async def _status_loop(self):
        while True:
            await asyncio.sleep(1.0)
            groups = []
            for net in self.networks:
                s = self.sessions[net.key]; dot = "●" if s.state == "connected" else "○"
                groups.append((net.name.split(" ")[0].upper(), f"{dot} {s.state}", [f"{net.key}/{c}" for c in net.autojoin]))
            self.win.rooms.set_groups(groups, self.win.active)
            hs = self.sessions.get("home"); self.win.me.setText(f"● {self.handle} · " + (hs.state if hs else "?"))
            if self.pins: json.dump(self.pins, open(self.pins_path, "w"))

    def _ts(self, m: Message) -> datetime:
        t = m.server_time
        if t:
            try: return datetime.fromisoformat(t.replace("Z", "+00:00")).astimezone()
            except Exception: pass
        return datetime.now().astimezone()

    def _on_event(self, sess: NetworkSession, m: Message):
        k = sess.net.key; me = sess.client.nick if sess.client else self.handle
        if m.command in ("PRIVMSG", "NOTICE") and m.params:
            target = m.params[0]
            if target.startswith(("#", "&")): room = target
            elif m.command == "NOTICE" or not m.nick or "!" not in (m.source or ""): room = "*server*"   # server/pseudo-user notices (e.g. EFnet drone scanners) go to the network buffer, not a DM
            else: room = m.nick
            key = f"{k}/{room}"; text = m.params[-1]
            if text.startswith("\x01ACTION ") and text.endswith("\x01"): text = f"* {m.nick} {text[8:-1]}"
            nick = m.nick or sess.server_used or "server"; ts = self._ts(m)
            mid = m.msgid or local_msgid(k, room, nick, ts.astimezone(timezone.utc).isoformat(), text)
            reply_to = m.tags.get("+draft/reply") or m.tags.get("+reply")
            if room != "*server*" and not self.store.add(k, room, mid, ts, nick, text, reply_to=reply_to, tags=json.dumps(m.tags) if m.tags else None):
                return  # already stored (history replay / reconnect): never show twice
            rn, rt = "", ""
            if reply_to:
                parent = self.store.get(k, room, reply_to)
                if parent: rn, rt = parent["nick"], parent["text"]
            hl = (me.lower() in text.lower() and nick != me)
            self.win.add(key, Item("msg", nick=nick, text=text, ts=ts, msgid=mid, is_me=(nick == me),
                                   is_bot=nick.lower().startswith("axiom"), highlight=hl,
                                   reply_to_nick=rn, reply_to_text=rt, reactions=self.store.reactions(k, room, mid)))
            if nick != me and (hl or (room not in ("*server*",) and not room.startswith(("#", "&")))):
                self.win.notify(key, nick, text, "mention" if hl else "dm")
            if key == self.win.active and sess.client and sess.client.has("draft/read-marker", "read-marker") and m.server_time:
                self.store.mark_read(k, room, ts.astimezone(timezone.utc).isoformat()); asyncio.get_event_loop().create_task(sess.client.mark_read(room, m.server_time))
        elif m.command == "TAGMSG" and "+draft/react" in m.tags and "+draft/reply" in m.tags:
            key = f"{k}/{m.params[0]}"
            if self.store.react(k, m.params[0], m.tags["+draft/reply"], m.nick or "?", m.tags["+draft/react"]):
                self.win.models.setdefault(key, TimelineModel()).react(m.tags["+draft/reply"], m.tags["+draft/react"])
        elif m.command == "TAGMSG" and "+typing" in m.tags:
            if f"{k}/{m.params[0]}" == self.win.active and m.nick != me:
                self.win.typing.setText(f"{m.nick} is typing…" if m.tags["+typing"] == "active" else "")
        elif m.command == "353":
            key = f"{k}/{m.params[-2]}"; self.names.setdefault(key, []).extend(m.params[-1].split())
        elif m.command == "366":
            key = f"{k}/{m.params[1]}"; names = self.names.pop(key, [])
            self._members[key] = sorted(names, key=lambda n: ("~&@%+".find(n[0]) if n[0] in "~&@%+" else 9, n.lower()))
            if key == self.win.active: self.win.rail.set_members(self._members[key])
            self.win.add(key, Item("system", text=f"{len(names)} here on {sess.net.name}"))
        elif m.command == "332":
            self.win.add(f"{k}/{m.params[1]}", Item("system", text=f"topic: {m.params[-1]}"))
        elif m.command == "JOIN" and m.nick == me:
            room = m.params[0]; key = f"{k}/{room}"
            if key not in self._history_loaded:
                self._history_loaded.add(key); self._replay_store(k, room, key)
                if sess.client and sess.client.has("draft/chathistory", "chathistory"):
                    asyncio.get_event_loop().create_task(self._fetch_history(sess, room, key))
            self.win.add(key, Item("system", text=f"joined {room} via {sess.server_used}"))
        elif m.command == "VT_CTCP":
            self.win.add(f"{k}/*server*", Item("system", text=f"CTCP {m.params[1]} from {m.params[0]} (answered)"))
        elif m.command == "001":
            self.win.add(f"{k}/{sess.net.home_channel}", Item("system", text=f"connected to {sess.net.name} ({sess.server_used}) · caps: {', '.join(sorted(sess.client.caps_enabled)) or 'none'}"))

    def _replay_store(self, k: str, room: str, key: str):
        rows = self.store.recent(k, room, 200); marker = self.store.read_marker(k, room); placed_marker = False
        for r in rows:
            ts = datetime.fromisoformat(r["ts"]).astimezone()
            if marker and not placed_marker and r["ts"] > marker:
                self.win.add(key, Item("read")); placed_marker = True
            rn = rt = ""
            if r["reply_to"]:
                p = self.store.get(k, room, r["reply_to"])
                if p: rn, rt = p["nick"], p["text"]
            self.win.add(key, Item("msg", nick=r["nick"], text=r["text"], ts=ts, msgid=r["msgid"], is_me=(r["nick"] == self.handle),
                                   is_bot=r["nick"].lower().startswith("axiom"), reply_to_nick=rn, reply_to_text=rt, reactions=self.store.reactions(k, room, r["msgid"])))
        if rows: self.win.add(key, Item("system", text=f"{len(rows)} messages from your local history"))

    async def _fetch_history(self, sess: NetworkSession, room: str, key: str):
        """Server history newer than the newest stored line (or the latest 100 on first join). Arrives via the
        normal event path, so the store's INSERT OR IGNORE is the single dedupe point for replay + live."""
        c = sess.client; newest = self.store.newest_ts(sess.net.key, room)
        try:
            if newest: rows = await c.chathistory("AFTER", room, "timestamp=" + newest.replace("+00:00", "Z"), limit=200)
            else: rows = await c.chathistory("LATEST", room, "*", limit=100)
        except Exception as e:
            self.win.add(key, Item("system", text=f"history fetch failed: {e}")); return
        for m in rows:  # same path as live lines: the store's INSERT OR IGNORE is the one dedupe point
            self._on_event(sess, m)
        if rows: self.win.add(key, Item("system", text=f"{len(rows)} lines from server history" + (" since your last visit" if newest else "")))

    def _on_typing(self, key: str, active: bool):
        net, _, room = key.partition("/"); s = self.sessions.get(net)
        if s and s.client and s.state == "connected" and s.net.ircv3 and room.startswith(("#", "&")):
            asyncio.get_event_loop().create_task(s.client.typing(room, "active" if active else "done"))

    def _on_room_changed(self, key: str):
        self.win.rail.set_members(self._members.get(key, [])); self.win.typing.setText("")
        net, _, room = key.partition("/"); s = self.sessions.get(net)
        if s and s.client and s.state == "connected" and s.net.ircv3 and s.client.has("draft/read-marker", "read-marker") and room.startswith("#"):
            newest = self.store.newest_ts(net, room)
            if newest:
                self.store.mark_read(net, room, newest)
                asyncio.get_event_loop().create_task(s.client.mark_read(room, newest.replace("+00:00", "Z")))

    def _on_send(self, key: str, text: str):
        net, _, room = key.partition("/"); s = self.sessions.get(net)
        if not s or not s.client or s.state != "connected": self.win.add(key, Item("system", text="not connected")); return
        async def go():
            if text.startswith("/"):
                cmd, _, rest = text[1:].partition(" ")
                if cmd in ("join", "j"): await s.client.join(rest.strip()); return
                if cmd == "me": await s.client.privmsg(room, f"\x01ACTION {rest}\x01"); return
                if cmd == "raw": await s.client.send_raw(rest); return
                if cmd in ("search", "s"):
                    hits = self.store.search(rest.strip(), network=net)
                    self.win.add(key, Item("system", text=f"search '{rest.strip()}' on {s.net.name}: {len(hits)} hit(s)"))
                    for r in hits[:20]:
                        self.win.add(key, Item("system", text=f"{r['ts'][:16]} {r['room']} <{r['nick']}> {r['text'][:140]}"))
                    return
                if cmd == "ask":  # Axiom door: HOME rooms carry Axiom's !ask (rate-limited 1/min/channel)
                    if net != "home": self.win.add(key, Item("system", text="/ask works on HOME rooms only (Axiom lives there)")); return
                    await s.client.privmsg(room, f"!ask {rest.strip()}"); return
                if cmd == "react" and s.client.has("message-tags") and s.client.cfg.client_tags:  # /react <msgid> <emoji>
                    mid, _, emoji = rest.strip().partition(" ")
                    await s.client.react(room, mid, emoji or "👍"); self.store.react(net, room, mid, s.client.nick, emoji or "👍")
                    self.win.models[key].react(mid, emoji or "👍"); return
                if cmd == "reply":  # /reply <msgid> text
                    mid, _, body = rest.strip().partition(" ")
                    await s.client.privmsg(room, body, reply_to=mid); return
                self.win.add(key, Item("system", text=f"unknown command /{cmd} (try /search /ask /react /reply /join /me)")); return
            mid = await s.client.privmsg(room, text)
            if not s.client.has("echo-message"):  # classic network: show + store our own line locally
                now = datetime.now().astimezone(); lid = local_msgid(net, room, s.client.nick, now.astimezone(timezone.utc).isoformat(), text)
                self.store.add(net, room, lid, now, s.client.nick, text)
                self.win.add(key, Item("msg", nick=s.client.nick, text=text, ts=now, msgid=lid, is_me=True))
        asyncio.get_event_loop().create_task(go())

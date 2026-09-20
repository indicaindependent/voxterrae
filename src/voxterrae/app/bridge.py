"""Bridge: NetworkSessions (asyncio via qasync) -> MainWindow models. One process, N networks."""
from __future__ import annotations
import asyncio, json, os
from datetime import datetime, timezone
from typing import Dict, List
from ..irc.networks import BUILTIN, Network
from ..irc.session import NetworkSession
from ..irc.message import Message
from .timeline import Item, TimelineModel, presence_item
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
        self._history_loaded: set = set(); self._replaying = False; self._announced: Dict[str, str] = {}   # net.key -> server we last announced
        win.send_text.connect(self._on_send)
        win.send_reply.connect(lambda key, mid, text: self._on_send(key, f"/reply {mid} {text}"))
        win.send_react.connect(lambda key, mid, emoji: self._on_send(key, f"/react {mid} {emoji}"))
        win.typing_changed.connect(self._on_typing)
        win.room_changed.connect(self._on_room_changed)
        if hasattr(win, "open_dm"): win.open_dm.connect(self.open_dm)
        if hasattr(win, "whois"): win.whois.connect(lambda net, nick: self._on_send(f"{net}/{self.win.active.split('/', 1)[1]}" if self.win.active.startswith(net + "/") else f"{net}/*server*", f"/whois {nick}"))
        if hasattr(win.rooms, "close_requested"): win.rooms.close_requested.connect(self._close_dm)
        self._members: Dict[str, List[str]] = {}
        self.dms: Dict[str, List[str]] = {}         # net.key -> open private conversations (rail rows)
        self.joined: Dict[str, List[str]] = {}      # net.key -> rooms we are actually in (JOIN/PART/KICK), drives the rail

    def _rooms_for(self, net) -> List[str]:
        """Rail entries for a network: its buffer, the rooms it will auto-join, then everything we joined ourselves."""
        rooms = list(dict.fromkeys(list(net.autojoin) + self.joined.get(net.key, [])))
        return [f"{net.key}/*server*"] + [f"{net.key}/{c}" for c in rooms if c != "*server*"] + [f"{net.key}/{n}" for n in self.dms.get(net.key, [])]

    def open_dm(self, net: str, nick: str):
        if not nick or nick.startswith(("#", "&")) or nick == "*server*": return
        if nick not in self.dms.setdefault(net, []): self.dms[net].append(nick)
        label = next((n.name.split(" ")[0].upper() for n in self.networks if n.key == net), net.upper())
        self.win.open_room(f"{net}/{nick}", label)

    def _close_dm(self, key: str):
        net, _, nick = key.partition("/")
        if nick in self.dms.get(net, []): self.dms[net].remove(nick)

    def _label(self, net) -> str: return net.name.split(" ")[0].upper()

    def _rename_member(self, k: str, old: str, new: str):
        for key, names in self._members.items():
            if not key.startswith(k + "/"): continue
            for i, n in enumerate(names):
                pre, nick = (n[0], n[1:].strip()) if n and n[0] in "~&@%+" else ("", n.strip())
                if nick == old: names[i] = pre + new
            if key == self.win.active: self.win.rail.set_members(names)

    def _member_event(self, k: str, room: str, nick: str, joined: bool):
        key = f"{k}/{room}"; names = self._members.setdefault(key, [])
        bare = [(n[1:].strip() if n and n[0] in "~&@%+" else n.strip()) for n in names]
        if joined and nick not in bare: names.append(nick)
        if not joined and nick in bare: names.pop(bare.index(nick))
        if key == self.win.active: self.win.rail.set_members(names); self.win._refresh_meta()
        self.win.add(key, presence_item(nick, joined))

    def start(self):
        groups = []
        for net in self.networks:
            s = NetworkSession(net, self.handle, self.pins, self._on_event); self.sessions[net.key] = s; s.start()
            groups.append((net.name.split(" ")[0].upper(), "connecting", self._rooms_for(net)))
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
                s = self.sessions[net.key]
                groups.append((self._label(net), s.state, self._rooms_for(net)))
                if s.state == "connected" and s.client and self._announced.get(net.key) != s.server_used:
                    # 001 is consumed inside connect() before the session attaches our handler, so announce from here
                    self._announced[net.key] = s.server_used
                    if net.key == "home": self.win.set_me(s.client.nick)
                    self.win.add(f"{net.key}/*server*", Item("system", text=f"connected to {net.name} ({s.server_used}) as {s.client.nick} · caps: {', '.join(sorted(s.client.caps_enabled)) or 'none'}"))
                    if not net.autojoin: self.win.add(f"{net.key}/*server*", Item("system", text="nothing is joined for you here: type /join #channel to enter a room"))
                if hasattr(self.win, "set_net_state"):
                    self.win.set_net_state(net.key, s.state, self._label(net))
                    lag = getattr(s.client, "lag_ms", None) if s.client else None
                    if lag is not None and s.state == "connected": self.win.set_lag(net.key, lag)
            self.win.rooms.set_groups(groups, self.win.active)
            hs = self.sessions.get("home"); st = hs.state if hs else "?"
            self.win.me.setText(f"{self.handle} · {st}"); self.win.me.set_icon("dot" if st == "connected" else "ring", self.win.p.phosphor if st == "connected" else self.win.p.muted)
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
            if room != "*server*" and not room.startswith(("#", "&")) and room not in self.dms.setdefault(k, []): self.dms[k].append(room)
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
            key = f"{k}/{m.params[-2]}"   # userhost-in-names gives "@nick!user@host": keep the prefix, drop the hostmask
            self.names.setdefault(key, []).extend(n.split("!", 1)[0] for n in m.params[-1].split() if n)
        elif m.command == "366":
            key = f"{k}/{m.params[1]}"; names = self.names.pop(key, [])
            self._members[key] = sorted(dict.fromkeys(names), key=lambda n: ("~&@%+".find(n[0]) if n[0] in "~&@%+" else 9, n.lower()))
            if key == self.win.active: self.win.rail.set_members(self._members[key]); self.win._refresh_meta()
            self.win.add(key, Item("system", text=f"{len(names)} here on {sess.net.name}"))
        elif m.command == "332":
            self.win.set_topic(f"{k}/{m.params[1]}", m.params[-1]); self.win.add(f"{k}/{m.params[1]}", Item("system", sub="topic", text=f"topic: {m.params[-1]}"))
        elif m.command in ("JOIN", "PART", "KICK", "QUIT") and self._replaying:
            pass   # history playback: presence changes from the past would corrupt the live member list and the fold
        elif m.command == "JOIN" and m.nick and m.nick != me:
            self._member_event(k, m.params[0], m.nick, True)
        elif m.command in ("PART", "KICK") and m.nick and (m.params[1] if m.command == "KICK" and len(m.params) > 1 else m.nick) != me:
            who = m.params[1] if m.command == "KICK" and len(m.params) > 1 else m.nick
            self._member_event(k, m.params[0], who, False)
        elif m.command == "QUIT" and m.nick and m.nick != me:
            for key in [key for key in list(self._members) if key.startswith(k + "/")]:
                names = self._members[key]; bare = [(n[1:].strip() if n and n[0] in "~&@%+" else n.strip()) for n in names]
                if m.nick in bare: self._member_event(k, key.split("/", 1)[1], m.nick, False)
        elif m.command == "NICK" and m.nick and m.params:
            new = m.params[0]
            if m.nick == me: self.win.set_me(new); self.win.add(f"{k}/*server*", Item("system", text=f"you are now known as {new}"))
            self._rename_member(k, m.nick, new)
            for key in [key for key in self._members if key.startswith(k + "/")]:
                if any((n[1:].strip() if n and n[0] in "~&@%+" else n.strip()) == new for n in self._members[key]): self.win.add(key, Item("system", sub="presence", text=f"{m.nick} is now {new}", meta={"renamed": [f"{m.nick} is now {new}"]}))
        elif m.command == "TOPIC" and m.params:
            self.win.set_topic(f"{k}/{m.params[0]}", m.params[-1]); self.win.add(f"{k}/{m.params[0]}", Item("system", sub="topic", text=f"{m.nick or 'server'} set the topic: {m.params[-1]}"))
        elif m.command in ("311", "312", "313", "317", "318", "319", "330", "338", "378", "379", "671"):
            txt = {"311": "{1} is {2}@{3} ({5})", "312": "{1} is on {2} ({3})", "313": "{1} is an operator", "317": "{1} idle {2}s", "318": "end of whois for {1}", "319": "{1} is in {2}", "330": "{1} is logged in as {2}", "338": "{1} actually {2}", "378": "{1} connecting from {2}", "379": "{1} modes {2}", "671": "{1} is using a secure connection"}.get(m.command, "{1} {2}")
            try: line = txt.format(*m.params)
            except Exception: line = " ".join(m.params[1:])
            self.win.add(self.win.active if self.win.active.startswith(k + "/") else f"{k}/*server*", Item("system", text=line))
        elif m.command == "433":
            self.win.add(f"{k}/*server*", Item("system", sub="error", text=f"nick {m.params[1] if len(m.params) > 1 else ''} is already in use; use /nick to pick another"))
        elif m.command in ("401", "402", "403", "404", "405", "421", "442", "471", "473", "474", "475", "477", "482"):
            self.win.add(self.win.active if self.win.active.startswith(k + "/") else f"{k}/*server*", Item("system", sub="error", text=" ".join(m.params[1:])))
        elif m.command in ("PART", "KICK") and (m.params[1] if m.command == "KICK" and len(m.params) > 1 else m.nick) == me:
            room = m.params[0]
            if room in self.joined.get(k, []): self.joined[k].remove(room)
            self.win.add(f"{k}/{room}", Item("system", text=("kicked from " if m.command == "KICK" else "left ") + room))
        elif m.command == "JOIN" and m.nick == me:
            room = m.params[0]; key = f"{k}/{room}"
            if self._replaying: return
            if room not in self.joined.setdefault(k, []): self.joined[k].append(room)
            if key not in self._history_loaded:
                self._history_loaded.add(key); self._replay_store(k, room, key)
                if sess.client and sess.client.has("draft/chathistory", "chathistory"):
                    asyncio.get_event_loop().create_task(self._fetch_history(sess, room, key))
            self.win.add(key, Item("system", text=f"joined {room} via {sess.server_used}"))
        elif m.command == "VT_CTCP":
            self.win.add(f"{k}/*server*", Item("system", text=f"CTCP {m.params[1]} from {m.params[0]} (answered)"))
        elif m.command == "001":
            pass   # registration completes inside connect(); the status loop announces the connection (see _status_loop)

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
        self._replaying = True
        try:
            for m in rows:  # same path as live lines: the store's INSERT OR IGNORE is the one dedupe point
                self._on_event(sess, m)
        finally: self._replaying = False
        n_msgs = sum(1 for m in rows if m.command in ("PRIVMSG", "NOTICE"))
        if n_msgs: self.win.add(key, Item("system", text=f"{n_msgs} messages from server history" + (" since your last visit" if newest else "")))

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
        if not s or not s.client or s.state != "connected": self.win.add(key, Item("system", sub="error", text="not connected: this line was not sent")); return
        async def go():
            if text.startswith("/"):
                cmd, _, rest = text[1:].partition(" ")
                if cmd in ("join", "j"): await s.client.join(rest.strip()); return
                if cmd in ("part", "leave"):
                    target = rest.strip() or room
                    if not target.startswith(("#", "&")): self._close_dm(key); self.win.close_room(key); return
                    await s.client.send_raw(f"PART {target}"); return
                if cmd in ("msg", "query", "q"):
                    to, _, body = rest.strip().partition(" ")
                    if not to: self.win.add(key, Item("system", sub="error", text="usage: /msg nick text")); return
                    self.open_dm(net, to)
                    if body:
                        mid = await s.client.privmsg(to, body)
                        if not s.client.has("echo-message"):
                            now = datetime.now().astimezone(); lid = local_msgid(net, to, s.client.nick, now.astimezone(timezone.utc).isoformat(), body)
                            self.store.add(net, to, lid, now, s.client.nick, body); self.win.add(f"{net}/{to}", Item("msg", nick=s.client.nick, text=body, ts=now, msgid=lid, is_me=True))
                    return
                if cmd == "whois": await s.client.send_raw(f"WHOIS {rest.strip()}"); return
                if cmd == "nick": await s.client.send_raw(f"NICK {rest.strip()}"); return
                if cmd == "topic":
                    if rest.strip(): await s.client.send_raw(f"TOPIC {room} :{rest.strip()}")
                    else: await s.client.send_raw(f"TOPIC {room}")
                    return
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
                self.win.add(key, Item("system", sub="error", text=f"unknown command /{cmd} (try /help)")); return
            mid = await s.client.privmsg(room, text)
            if not s.client.has("echo-message"):  # classic network: show + store our own line locally
                now = datetime.now().astimezone(); lid = local_msgid(net, room, s.client.nick, now.astimezone(timezone.utc).isoformat(), text)
                self.store.add(net, room, lid, now, s.client.nick, text)
                self.win.add(key, Item("msg", nick=s.client.nick, text=text, ts=now, msgid=lid, is_me=True))
        asyncio.get_event_loop().create_task(go())

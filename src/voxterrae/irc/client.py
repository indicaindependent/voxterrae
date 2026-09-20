"""Async IRCv3 client core for VoxTerrae (M0).

Responsibilities: TLS connect, CAP LS 302 negotiation, SASL PLAIN, registration, PING/PONG,
batch assembly (incl. chathistory + multiline), labeled-response correlation, msgid dedupe,
CHATHISTORY requests, JOIN/PRIVMSG/TAGMSG helpers, and a simple event stream.

Design rules (from the v1 architecture doc):
- feature-gate every draft/* capability on the server's CAP list, never on hostname;
- negotiate both the draft/ and ratified spelling of caps that are mid-ratification;
- never hardcode an IP: hostname + TLS (STS honoured when advertised);
- the store keys on msgid, so this layer exposes msgid on every message and never invents one.
"""
from __future__ import annotations
import asyncio, base64, logging, ssl, time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from .message import Message, parse

log = logging.getLogger("voxterrae.irc")

# caps we know how to use, in the order we like them. (draft, ratified) pairs are both requested.
WANTED_CAPS: List[str] = [
    "message-tags", "server-time", "batch", "labeled-response", "echo-message", "cap-notify",
    "account-notify", "away-notify", "chghost", "extended-join", "invite-notify", "setname",
    "account-tag", "multi-prefix", "userhost-in-names", "sasl", "standard-replies",
    "draft/chathistory", "chathistory",
    "draft/read-marker", "read-marker",
    "draft/multiline", "multiline",
    "draft/event-playback", "event-playback",
    "draft/account-registration",
    "draft/message-redaction", "message-redaction",
]

Handler = Callable[[Message], Awaitable[None] | None]


@dataclass
class ClientConfig:
    host: str
    port: int = 6697
    tls: bool = True
    nick: str = "voxterrae"
    user: str = "voxterrae"
    realname: str = "VoxTerrae"
    sasl_user: Optional[str] = None
    sasl_pass: Optional[str] = None
    tls_verify: str = "strict"            # "strict" (CA-verified, HOME) | "tofu" (self-signed pinned by SHA-256, EFnet)
    pinned_fingerprint: Optional[str] = None  # sha256 hex of the leaf cert when tls_verify == "tofu"
    client_tags: bool = True              # send +typing/+draft/react etc. (False on EFnet even if a server advertised tags)
    connect_timeout: float = 15.0
    ping_interval: float = 60.0
    ping_timeout: float = 120.0
    client_tags_ok_without_server: bool = False  # TAGMSG needs message-tags; keep False


@dataclass
class Batch:
    ref: str
    kind: str
    params: List[str]
    messages: List[Message] = field(default_factory=list)
    parent: Optional[str] = None


class IrcClient:
    def __init__(self, cfg: ClientConfig):
        self.cfg = cfg
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.caps_available: Dict[str, str] = {}
        self.caps_enabled: Set[str] = set()
        self.isupport: Dict[str, str] = {}
        self.nick = cfg.nick
        self.lag_ms: Optional[int] = None   # round trip of our own PING, set on PONG
        self.registered = asyncio.Event()
        self.closed = asyncio.Event()
        self.seen_msgids: Set[str] = set()
        self.batches: Dict[str, Batch] = {}
        self._handlers: List[Handler] = []
        self._label_waiters: Dict[str, asyncio.Future] = {}
        self._batch_labels: Dict[str, str] = {}  # batch ref -> label (label rides the "+" BATCH line)
        self._label_n = 0
        self._cap_ls_done = asyncio.Event()
        self._sasl_done: Optional[asyncio.Future] = None
        self._last_rx = time.monotonic()
        self._tasks: List[asyncio.Task] = []
        self.events: "asyncio.Queue[Message]" = asyncio.Queue()

    # ---- capability helpers --------------------------------------------------------------
    def has(self, *names: str) -> bool:
        """True if ANY of the given cap spellings is enabled (draft/ or ratified)."""
        return any(n in self.caps_enabled for n in names)

    def cap_value(self, *names: str) -> Optional[str]:
        for n in names:
            if n in self.caps_available:
                return self.caps_available[n]
        return None

    # ---- lifecycle -----------------------------------------------------------------------
    async def connect(self) -> None:
        ctx = None
        if self.cfg.tls:
            ctx = ssl.create_default_context()
            if self.cfg.tls_verify == "tofu":
                # EFnet servers mostly run self-signed certs. We still encrypt, and we PIN the leaf certificate:
                # first connection records its SHA-256; any later mismatch is refused (see below).
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
        self.reader, self.writer = await asyncio.wait_for(
            asyncio.open_connection(self.cfg.host, self.cfg.port, ssl=ctx, server_hostname=self.cfg.host if ctx else None),
            timeout=self.cfg.connect_timeout,
        )
        self.cert_fingerprint: Optional[str] = None
        if ctx is not None:
            sslobj = self.writer.get_extra_info("ssl_object")
            der = sslobj.getpeercert(binary_form=True) if sslobj else None
            if der:
                import hashlib
                self.cert_fingerprint = hashlib.sha256(der).hexdigest()
            if self.cfg.tls_verify == "tofu" and self.cfg.pinned_fingerprint and self.cert_fingerprint != self.cfg.pinned_fingerprint:
                self.writer.close()
                raise ssl.SSLError(f"pinned certificate mismatch for {self.cfg.host}: got {self.cert_fingerprint}")
        self._tasks.append(asyncio.create_task(self._read_loop(), name="irc-read"))
        self._tasks.append(asyncio.create_task(self._ping_loop(), name="irc-ping"))
        await self.send_raw("CAP LS 302")
        if self.cfg.sasl_pass:
            # nothing else yet; NICK/USER after we know caps so sasl can complete before 001
            pass
        await self.send_raw(f"NICK {self.cfg.nick}")
        await self.send_raw(f"USER {self.cfg.user} 0 * :{self.cfg.realname}")
        await asyncio.wait_for(self._cap_ls_done.wait(), timeout=self.cfg.connect_timeout)
        req = [c for c in getattr(self, "_wanted", WANTED_CAPS) if c in self.caps_available]
        if self.cfg.sasl_pass is None:
            req = [c for c in req if c != "sasl"]
        if req:
            # CAP REQ lines must stay well under 512 bytes
            chunk: List[str] = []
            for c in req:
                if len(" ".join(chunk + [c])) > 400:
                    await self.send_raw("CAP REQ :" + " ".join(chunk)); chunk = []
                chunk.append(c)
            if chunk:
                await self.send_raw("CAP REQ :" + " ".join(chunk))
        if self.cfg.sasl_pass is not None and "sasl" in self.caps_available:
            loop = asyncio.get_running_loop()
            self._sasl_done = loop.create_future()
            await self._await_cap_ack("sasl")
            await self.send_raw("AUTHENTICATE PLAIN")
            await asyncio.wait_for(self._sasl_done, timeout=self.cfg.connect_timeout)
        await self.send_raw("CAP END")
        await asyncio.wait_for(self.registered.wait(), timeout=self.cfg.connect_timeout)

    async def _await_cap_ack(self, cap: str, timeout: float = 10.0) -> None:
        end = time.monotonic() + timeout
        while cap not in self.caps_enabled and time.monotonic() < end:
            await asyncio.sleep(0.05)
        if cap not in self.caps_enabled:
            raise RuntimeError(f"cap {cap} not acknowledged")

    async def quit(self, reason: str = "VoxTerrae") -> None:
        try:
            await self.send_raw(f"QUIT :{reason}")
            await asyncio.sleep(0.3)
        except (ConnectionError, OSError):
            pass  # the server may drop the socket before our drain completes; that is a successful quit
        finally:
            await self.close()

    async def close(self) -> None:
        for t in self._tasks:
            t.cancel()
        if self.writer:
            try:
                self.writer.close(); await self.writer.wait_closed()
            except Exception:
                pass
        self.closed.set()

    # ---- I/O ---------------------------------------------------------------------------------
    async def send_raw(self, line: str) -> None:
        if "\r" in line or "\n" in line:
            raise ValueError("CR/LF in line")
        data = (line + "\r\n").encode("utf-8")
        limit = 8191 if "message-tags" in self.caps_enabled else 512
        if len(data) > limit:  # classic servers cut at 512 bytes; the composer splits long text upstream
            raise ValueError(f"line too long ({len(data)} > {limit})")
        log.debug(">> %s", line if not line.startswith("AUTHENTICATE ") else "AUTHENTICATE ***")
        assert self.writer is not None
        self.writer.write(data)
        await self.writer.drain()

    async def send(self, msg: Message) -> None:
        await self.send_raw(msg.serialize())

    async def send_labeled(self, msg: Message, timeout: float = 15.0) -> List[Message]:
        """Send with labeled-response; returns the response messages (a batch's contents or the single reply)."""
        if not self.has("labeled-response"):
            await self.send(msg); return []
        self._label_n += 1
        label = f"vt{self._label_n}"
        msg.tags["label"] = label
        fut = asyncio.get_running_loop().create_future()
        self._label_waiters[label] = fut
        await self.send(msg)
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._label_waiters.pop(label, None)

    async def _read_loop(self) -> None:
        assert self.reader is not None
        try:
            while True:
                raw = await self.reader.readline()
                if not raw:
                    break
                self._last_rx = time.monotonic()
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    continue
                try:
                    msg = parse(line)
                except ValueError as e:
                    log.warning("unparsable line: %s", e); continue
                log.debug("<< %s", line)
                await self._dispatch(msg)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # pragma: no cover
            log.exception("read loop died: %s", e)
        finally:
            self.closed.set()

    async def _ping_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.cfg.ping_interval)
                if time.monotonic() - self._last_rx > self.cfg.ping_timeout:
                    log.warning("server silent %.0fs, closing", time.monotonic() - self._last_rx)
                    await self.close(); return
                if self.registered.is_set():
                    await self.send_raw(f"PING :vt{int(time.monotonic() * 1000)}")   # PONG echoes it back -> lag_ms
        except asyncio.CancelledError:
            raise

    # ---- protocol handling ---------------------------------------------------------------
    async def _dispatch(self, msg: Message) -> None:
        c = msg.command
        if c == "PING":
            await self.send_raw("PONG :" + (msg.params[-1] if msg.params else "")); return
        if c == "PONG" and msg.params and msg.params[-1].startswith("vt") and msg.params[-1][2:].isdigit():
            self.lag_ms = max(0, int(time.monotonic() * 1000) - int(msg.params[-1][2:]))
        if c == "CAP":
            await self._on_cap(msg); return
        if c == "AUTHENTICATE":
            await self._on_authenticate(msg); return
        if c in ("903", "904", "905", "906", "907", "908"):
            if self._sasl_done and not self._sasl_done.done():
                if c == "903": self._sasl_done.set_result(True)
                else: self._sasl_done.set_exception(RuntimeError(f"SASL failed {c}: {' '.join(msg.params[1:])}"))
            return
        if c == "001":
            self.nick = msg.params[0] if msg.params else self.nick
        if c == "005":
            for tok in msg.params[1:-1]:
                k, _, v = tok.partition("=")
                self.isupport[k] = v
        if c in ("376", "422"):
            self.registered.set()
        if c == "NICK" and msg.nick == self.nick and msg.params:
            self.nick = msg.params[0]
        if c == "BATCH":
            await self._on_batch(msg); return
        if c == "PRIVMSG" and len(msg.params) == 2 and msg.params[1].startswith("\x01") and not msg.params[1].startswith("\x01ACTION"):
            await self._on_ctcp(msg); return  # CTCP request: answer, never show as a DM (EFnet drone monitors VERSION every new client)
        # messages inside a batch are collected, then delivered when the batch closes
        b = msg.batch
        if b and b in self.batches:
            self.batches[b].messages.append(msg)
            return
        # labeled-response: single reply (no batch)
        label = msg.tags.get("label")
        if label and label in self._label_waiters and not self._label_waiters[label].done():
            self._label_waiters[label].set_result([msg])
            if c == "ACK":  # empty labeled ack
                return
        await self._deliver(msg)

    async def _deliver(self, msg: Message) -> None:
        mid = msg.msgid
        if mid:
            if mid in self.seen_msgids and msg.command in ("PRIVMSG", "NOTICE", "TAGMSG"):
                log.debug("dedupe msgid %s", mid); return
            self.seen_msgids.add(mid)
        await self.events.put(msg)
        for h in self._handlers:
            r = h(msg)
            if asyncio.iscoroutine(r):
                await r

    def on(self, handler: Handler) -> None:
        self._handlers.append(handler)

    async def _on_cap(self, msg: Message) -> None:
        sub = msg.params[1].upper() if len(msg.params) > 1 else ""
        if sub == "LS":
            more = len(msg.params) > 3 and msg.params[2] == "*"
            caps = msg.params[-1].split()
            for cap in caps:
                k, _, v = cap.partition("=")
                self.caps_available[k] = v
            if not more:
                self._cap_ls_done.set()
        elif sub == "ACK":
            for cap in msg.params[-1].split():
                if cap.startswith("-"): self.caps_enabled.discard(cap[1:])
                else: self.caps_enabled.add(cap)
        elif sub == "NAK":
            log.warning("CAP NAK %s", msg.params[-1])
        elif sub == "NEW":
            for cap in msg.params[-1].split():
                k, _, v = cap.partition("="); self.caps_available[k] = v
            want = [c.partition("=")[0] for c in msg.params[-1].split() if c.partition("=")[0] in WANTED_CAPS]
            if want: await self.send_raw("CAP REQ :" + " ".join(want))
        elif sub == "DEL":
            for cap in msg.params[-1].split():
                self.caps_available.pop(cap, None); self.caps_enabled.discard(cap)

    CTCP_VERSION = "VoxTerrae 0.0.1 (Python/PySide6) https://voxterrae.app"
    async def _on_ctcp(self, msg: Message) -> None:
        body = msg.params[1].strip("\x01"); cmd, _, arg = body.partition(" "); who = msg.nick
        if not who: return
        reply = None
        if cmd.upper() == "VERSION": reply = f"VERSION {self.CTCP_VERSION}"
        elif cmd.upper() == "PING": reply = f"PING {arg}" if arg else "PING"
        elif cmd.upper() == "CLIENTINFO": reply = "CLIENTINFO ACTION CLIENTINFO PING VERSION"
        if reply:
            await self.send(Message("NOTICE", [who, "\x01" + reply + "\x01"]))
        await self.events.put(Message("VT_CTCP", [who, body], tags=dict(msg.tags), source=msg.source))
        for h in self._handlers:
            r = h(Message("VT_CTCP", [who, body], tags=dict(msg.tags), source=msg.source))
            if asyncio.iscoroutine(r): await r

    async def _on_authenticate(self, msg: Message) -> None:
        if msg.params and msg.params[0] == "+":
            u = self.cfg.sasl_user or self.cfg.nick
            blob = base64.b64encode(f"{u}\x00{u}\x00{self.cfg.sasl_pass}".encode()).decode()
            # 400-byte chunking per SASL spec
            for i in range(0, len(blob), 400):
                await self.send_raw("AUTHENTICATE " + blob[i:i+400])
            if len(blob) % 400 == 0:
                await self.send_raw("AUTHENTICATE +")

    async def _on_batch(self, msg: Message) -> None:
        ref = msg.params[0]
        if ref.startswith("+"):
            ref = ref[1:]
            kind = msg.params[1] if len(msg.params) > 1 else ""
            self.batches[ref] = Batch(ref=ref, kind=kind, params=msg.params[2:], parent=msg.batch)
            if msg.tags.get("label"):
                self._batch_labels[ref] = msg.tags["label"]
            return
        if ref.startswith("-"):
            ref = ref[1:]
            b = self.batches.pop(ref, None)
            if b is None:
                return
            if b.parent and b.parent in self.batches:  # nested: hand to parent
                self.batches[b.parent].messages.append(Message("BATCH", ["+" + b.ref, b.kind] + b.params))
                self.batches[b.parent].messages.extend(b.messages)
                self.batches[b.parent].messages.append(Message("BATCH", ["-" + b.ref]))
                return
            lbl = self._batch_labels.pop(ref, None)
            if lbl and lbl in self._label_waiters and not self._label_waiters[lbl].done():
                self._label_waiters[lbl].set_result([m for m in b.messages if m.command != "BATCH"])
                return  # a labeled reply batch is consumed by its requester, not the event stream
            if b.kind in ("draft/multiline", "multiline"):
                await self._deliver(self._join_multiline(b)); return
            for m in b.messages:
                if m.command == "BATCH":
                    continue
                m.tags.setdefault("vt/batch-kind", b.kind)
                await self._deliver(m)

    def _join_multiline(self, b: Batch) -> Message:
        target = b.params[0] if b.params else ""
        first = next((m for m in b.messages if m.command in ("PRIVMSG", "NOTICE")), None)
        text_parts: List[str] = []
        for m in b.messages:
            if m.command not in ("PRIVMSG", "NOTICE"):
                continue
            piece = m.params[-1]
            if "draft/multiline-concat" in m.tags or "multiline-concat" in m.tags:
                text_parts[-1] = (text_parts[-1] if text_parts else "") + piece
            else:
                text_parts.append(piece)
        out = Message(first.command if first else "PRIVMSG", [target, "\n".join(text_parts)],
                      tags=dict(first.tags) if first else {}, source=first.source if first else None)
        out.tags.pop("batch", None)
        out.tags["vt/multiline"] = ""
        return out

    # ---- actions -----------------------------------------------------------------------------
    async def join(self, channel: str, key: Optional[str] = None) -> None:
        await self.send_raw(f"JOIN {channel}" + (f" {key}" if key else ""))

    async def privmsg(self, target: str, text: str, reply_to: Optional[str] = None) -> Optional[str]:
        """Send text; multi-line text uses a multiline batch when the server supports it.
        Returns the echoed msgid when echo-message + labeled-response are on, else None."""
        tags: Dict[str, str] = {}
        if reply_to and self.has("message-tags") and self.cfg.client_tags:
            tags["+draft/reply"] = reply_to
        lines = text.split("\n")
        if len(lines) > 1 and self.has("draft/multiline", "multiline"):
            ref = f"ml{int(time.time()*1000)}"
            kind = "draft/multiline" if "draft/multiline" in self.caps_enabled else "multiline"
            await self.send(Message("BATCH", [f"+{ref}", kind, target], tags=tags))
            for ln in lines:
                await self.send(Message("PRIVMSG", [target, ln], tags={"batch": ref}))
            await self.send(Message("BATCH", [f"-{ref}"]))
            return None
        if len(lines) > 1:
            for ln in lines:
                await self.send(Message("PRIVMSG", [target, ln]))
            return None
        msg = Message("PRIVMSG", [target, text], tags=tags)
        if self.has("echo-message") and self.has("labeled-response"):
            resp = await self.send_labeled(msg)
            for m in resp:
                if m.command == "PRIVMSG" and m.msgid:
                    self.seen_msgids.add(m.msgid)  # our own echo counts as seen
                    return m.msgid
            return None
        await self.send(msg)
        return None

    async def react(self, target: str, msgid: str, emoji: str) -> None:
        if not self.has("message-tags") or not self.cfg.client_tags:
            return  # silently unsupported (EFnet)
        await self.send(Message("TAGMSG", [target], tags={"+draft/reply": msgid, "+draft/react": emoji}))

    async def typing(self, target: str, state: str = "active") -> None:
        if self.has("message-tags") and self.cfg.client_tags:
            await self.send(Message("TAGMSG", [target], tags={"+typing": state}))

    async def mark_read(self, target: str, timestamp: str) -> None:
        if self.has("draft/read-marker", "read-marker"):
            await self.send_raw(f"MARKREAD {target} timestamp={timestamp}")

    async def chathistory(self, subcmd: str, target: str, *args: str, limit: int = 100, timeout: float = 20.0) -> List[Message]:
        """CHATHISTORY LATEST|BEFORE|AFTER|AROUND|BETWEEN. Returns the delivered messages (batch contents)."""
        if not self.has("draft/chathistory", "chathistory"):
            return []
        line = " ".join(["CHATHISTORY", subcmd.upper(), target, *args, str(limit)])
        msg = parse(line)
        if not self.has("labeled-response"):
            await self.send(msg)  # results arrive on the event stream instead
            return []
        res = await self.send_labeled(msg, timeout=timeout)
        out = [m for m in res if m.command in ("PRIVMSG", "NOTICE", "TAGMSG", "JOIN", "PART", "QUIT", "MODE", "TOPIC", "NICK", "KICK")]
        for m in out:
            if m.msgid:
                self.seen_msgids.add(m.msgid)
        return out

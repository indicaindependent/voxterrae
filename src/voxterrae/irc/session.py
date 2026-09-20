"""NetworkSession: one Network -> one live IrcClient, with server-pool failover and reconnect backoff."""
from __future__ import annotations
import asyncio, logging, ssl
from typing import Callable, Dict, Optional
from .client import IrcClient, ClientConfig, WANTED_CAPS
from .message import Message
from .networks import Network

log = logging.getLogger("voxterrae.session")
CLASSIC_CAPS = {"multi-prefix", "userhost-in-names", "away-notify", "account-notify", "chghost", "extended-join", "invite-notify", "server-time", "message-tags", "batch", "cap-notify", "sasl"}

class NetworkSession:
    def __init__(self, net: Network, handle: str, pins: Dict[str, str], on_event: Callable[["NetworkSession", Message], None], sasl_pass: Optional[str] = None):
        self.net = net; self.handle = handle; self.pins = pins; self.on_event = on_event; self.sasl_pass = sasl_pass
        self.client: Optional[IrcClient] = None; self.server_used: Optional[str] = None
        self.state = "idle"; self._task: Optional[asyncio.Task] = None; self.stopped = False

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name=f"session-{self.net.key}")

    async def stop(self) -> None:
        self.stopped = True
        if self.client: await self.client.quit("VoxTerrae")
        if self._task: self._task.cancel()

    async def _run(self) -> None:
        backoff = 3
        while not self.stopped:
            ok = await self._connect_pool()
            if not ok:
                self.state = f"retry in {backoff}s"; await asyncio.sleep(backoff); backoff = min(backoff * 2, 120); continue
            backoff = 3
            assert self.client
            await self.client.closed.wait()
            if not self.stopped:
                self.state = "disconnected"; log.warning("%s: disconnected, reconnecting", self.net.key)

    async def _connect_pool(self) -> bool:
        for srv in self.net.servers:
            key = f"{srv.host}:{srv.port}"
            cfg = ClientConfig(host=srv.host, port=srv.port, tls=srv.tls, tls_verify=srv.tls_verify,
                               pinned_fingerprint=self.pins.get(key), nick=self.handle + self.net.nick_suffix,
                               user="voxterrae", realname=f"VoxTerrae · {self.handle}",
                               sasl_user=self.handle if (self.net.sasl and self.sasl_pass) else None,
                               sasl_pass=self.sasl_pass if self.net.sasl else None, client_tags=self.net.ircv3)
            c = IrcClient(cfg)
            if not self.net.ircv3:  # classic network: ask only for widely-implemented caps
                c._wanted = [x for x in WANTED_CAPS if x in CLASSIC_CAPS]
            self.state = f"connecting {key}"
            try:
                await c.connect()
            except ssl.SSLError as e:
                log.warning("%s: %s TLS refused: %s", self.net.key, key, e); await c.close(); continue
            except Exception as e:
                log.warning("%s: %s failed: %s", self.net.key, key, e); await c.close(); continue
            if srv.tls_verify == "tofu" and c.cert_fingerprint and key not in self.pins:
                self.pins[key] = c.cert_fingerprint  # trust on first use; persisted by the caller
            self.client = c; self.server_used = key; self.state = "connected"
            c.on(lambda m, s=self: s.on_event(s, m))
            for ch in self.net.autojoin:
                await c.join(ch)
            return True
        return False

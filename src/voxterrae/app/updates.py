"""H3: in-app update check against the hub's static feed. One plain GET, no identifiers, never installs anything.
   The feed carries a sha256 per asset; the CLIENT never downloads a binary, it only points at the release page."""
from __future__ import annotations
import json, re, ssl, threading, urllib.request
from typing import Callable, Optional
from .. import __version__

FEED_URL = "https://voxterrae.app/api/latest.json"
_NUM = re.compile(r"\d+")

def version_tuple(v: str) -> tuple:
    """'0.1.0' -> (0,1,0,1); '0.1.0-rc1' -> (0,1,0,0) so a pre-release sorts below its final. Non-numeric tags ignored."""
    core, _, pre = v.strip().lstrip("v").partition("-")
    nums = tuple(int(x) for x in _NUM.findall(core))[:3]
    nums = nums + (0,) * (3 - len(nums))
    return nums + ((0,) if pre else (1,))

def is_newer(latest: str, current: str) -> bool:
    return version_tuple(latest) > version_tuple(current)

def fetch_feed(url: str = FEED_URL, timeout: float = 6.0) -> Optional[dict]:
    """Strict TLS (system CA), explicit User-Agent (Cloudflare 403s the default urllib UA), 6 s timeout. None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"VoxTerrae/{__version__} (update-check)", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            if r.status != 200: return None
            d = json.loads(r.read(200_000).decode("utf-8"))
        return d if isinstance(d, dict) and isinstance(d.get("version"), str) else None
    except Exception:
        return None

def check(current: str = __version__, url: str = FEED_URL, timeout: float = 6.0) -> dict:
    """Returns {'status': 'newer'|'current'|'unknown', 'latest': str|None, 'url': str|None}."""
    d = fetch_feed(url, timeout)
    if not d: return {"status": "unknown", "latest": None, "url": None}
    latest = d["version"]; page = d.get("url") or "https://voxterrae.app/download"
    return {"status": "newer" if is_newer(latest, current) else "current", "latest": latest, "url": page}

def check_async(callback: Callable[[dict], None], current: str = __version__, url: str = FEED_URL) -> threading.Thread:
    """Run check() off the UI thread; callback receives the result dict (caller marshals to the UI thread)."""
    t = threading.Thread(target=lambda: callback(check(current, url)), name="vt-update-check", daemon=True); t.start(); return t

"""IRC message parsing/serialising with IRCv3 message-tags (ircv3.net/specs/extensions/message-tags).

Zero dependencies. Lines are handled as str (UTF-8 decoded upstream, UTF8ONLY networks)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_UNESC = {"\\:": ";", "\\s": " ", "\\\\": "\\", "\\r": "\r", "\\n": "\n"}
_ESC = {";": "\\:", " ": "\\s", "\\": "\\\\", "\r": "\\r", "\n": "\\n"}


def unescape_tag_value(v: str) -> str:
    out: List[str] = []
    i = 0
    while i < len(v):
        c = v[i]
        if c == "\\":
            if i + 1 >= len(v):  # trailing lone backslash is dropped per spec
                break
            pair = v[i : i + 2]
            out.append(_UNESC.get(pair, v[i + 1]))  # invalid escape -> the char itself
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def escape_tag_value(v: str) -> str:
    return "".join(_ESC.get(c, c) for c in v)


@dataclass
class Message:
    command: str
    params: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)
    source: Optional[str] = None  # "nick!user@host" or "server"

    # -- convenience --------------------------------------------------------------------------
    @property
    def nick(self) -> Optional[str]:
        if not self.source:
            return None
        return self.source.split("!", 1)[0]

    @property
    def msgid(self) -> Optional[str]:
        return self.tags.get("msgid")

    @property
    def server_time(self) -> Optional[str]:
        return self.tags.get("time")

    @property
    def batch(self) -> Optional[str]:
        return self.tags.get("batch")

    def serialize(self) -> str:
        parts: List[str] = []
        if self.tags:
            parts.append("@" + ";".join(k if v == "" else f"{k}={escape_tag_value(v)}" for k, v in self.tags.items()))
        if self.source:
            parts.append(":" + self.source)
        parts.append(self.command)
        if self.params:
            *head, last = self.params
            for p in head:
                if p == "" or p.startswith(":") or " " in p:
                    raise ValueError(f"middle param not encodable: {p!r}")
                parts.append(p)
            if last == "" or last.startswith(":") or " " in last:
                parts.append(":" + last)
            else:
                parts.append(last)
        line = " ".join(parts)
        if "\r" in line or "\n" in line:
            raise ValueError("CR/LF inside message")
        return line


def parse(line: str) -> Message:
    """Parse one line WITHOUT the trailing CRLF. Raises ValueError on an empty command."""
    tags: Dict[str, str] = {}
    source: Optional[str] = None
    s = line
    if s.startswith("@"):
        raw, _, s = s[1:].partition(" ")
        for item in raw.split(";"):
            if not item:
                continue
            k, eq, v = item.partition("=")
            tags[k] = unescape_tag_value(v) if eq else ""
        s = s.lstrip(" ")
    if s.startswith(":"):
        source, _, s = s[1:].partition(" ")
        s = s.lstrip(" ")
    params: List[str] = []
    trailing: Optional[str] = None
    if " :" in s:
        s, _, trailing = s.partition(" :")
    elif s.startswith(":"):
        s, trailing = "", s[1:]
    toks = [t for t in s.split(" ") if t]
    if not toks:
        raise ValueError(f"no command in line: {line!r}")
    command = toks[0].upper()
    params = toks[1:]
    if trailing is not None:
        params.append(trailing)
    return Message(command=command, params=params, tags=tags, source=source)

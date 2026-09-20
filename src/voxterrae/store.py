"""Local store: SQLite (WAL) + FTS5. Messages are keyed by (network, room, msgid); msgid is the server's on IRCv3
networks and a deterministic local hash on classic networks (EFnet has no msgid). Read markers per room."""
from __future__ import annotations
import hashlib, os, sqlite3, threading, time
from datetime import datetime, timezone
from typing import Iterable, List, Optional, Tuple

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS messages(
  network TEXT NOT NULL, room TEXT NOT NULL, msgid TEXT NOT NULL,
  ts TEXT NOT NULL, nick TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'msg',
  text TEXT NOT NULL, reply_to TEXT, tags TEXT,
  PRIMARY KEY(network, room, msgid)
);
CREATE INDEX IF NOT EXISTS idx_msg_room_ts ON messages(network, room, ts);
CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(text, nick, room, network, content='messages', content_rowid='rowid');
CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
  INSERT INTO messages_fts(rowid, text, nick, room, network) VALUES (new.rowid, new.text, new.nick, new.room, new.network);
END;
CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
  INSERT INTO messages_fts(messages_fts, rowid, text, nick, room, network) VALUES('delete', old.rowid, old.text, old.nick, old.room, old.network);
END;
CREATE TABLE IF NOT EXISTS reactions(
  network TEXT NOT NULL, room TEXT NOT NULL, msgid TEXT NOT NULL, nick TEXT NOT NULL, emoji TEXT NOT NULL,
  PRIMARY KEY(network, room, msgid, nick, emoji)
);
CREATE TABLE IF NOT EXISTS read_markers(network TEXT NOT NULL, room TEXT NOT NULL, ts TEXT NOT NULL, PRIMARY KEY(network, room));
CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
"""

def local_msgid(network: str, room: str, nick: str, ts: str, text: str) -> str:
    """Deterministic id for classic networks: same line replayed = same id (so a reconnect never duplicates)."""
    return "L" + hashlib.sha1(f"{network}\x00{room}\x00{nick}\x00{ts[:16]}\x00{text}".encode()).hexdigest()[:20]

class Store:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        self.path = path; self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False); self.db.executescript(SCHEMA); self.db.commit()

    def add(self, network: str, room: str, msgid: str, ts: datetime, nick: str, text: str, kind: str = "msg",
            reply_to: Optional[str] = None, tags: Optional[str] = None) -> bool:
        """Insert; returns True if new, False if the (network, room, msgid) was already stored."""
        with self._lock:
            cur = self.db.execute("INSERT OR IGNORE INTO messages(network,room,msgid,ts,nick,kind,text,reply_to,tags) VALUES(?,?,?,?,?,?,?,?,?)",
                                  (network, room, msgid, ts.astimezone(timezone.utc).isoformat(), nick, kind, text, reply_to, tags))
            self.db.commit(); return cur.rowcount == 1

    def react(self, network: str, room: str, msgid: str, nick: str, emoji: str) -> bool:
        with self._lock:
            cur = self.db.execute("INSERT OR IGNORE INTO reactions VALUES(?,?,?,?,?)", (network, room, msgid, nick, emoji)); self.db.commit(); return cur.rowcount == 1

    def reactions(self, network: str, room: str, msgid: str) -> dict:
        rows = self.db.execute("SELECT emoji, COUNT(*) FROM reactions WHERE network=? AND room=? AND msgid=? GROUP BY emoji", (network, room, msgid)).fetchall()
        return {e: n for e, n in rows}

    def get(self, network: str, room: str, msgid: str) -> Optional[sqlite3.Row]:
        self.db.row_factory = sqlite3.Row
        return self.db.execute("SELECT * FROM messages WHERE network=? AND room=? AND msgid=?", (network, room, msgid)).fetchone()

    def recent(self, network: str, room: str, limit: int = 200) -> List[sqlite3.Row]:
        self.db.row_factory = sqlite3.Row
        rows = self.db.execute("SELECT * FROM messages WHERE network=? AND room=? ORDER BY ts DESC LIMIT ?", (network, room, limit)).fetchall()
        return list(reversed(rows))

    def newest_ts(self, network: str, room: str) -> Optional[str]:
        r = self.db.execute("SELECT MAX(ts) FROM messages WHERE network=? AND room=?", (network, room)).fetchone(); return r[0] if r else None

    def search(self, q: str, network: Optional[str] = None, room: Optional[str] = None, limit: int = 50) -> List[sqlite3.Row]:
        self.db.row_factory = sqlite3.Row
        sql = "SELECT m.* FROM messages_fts f JOIN messages m ON m.rowid=f.rowid WHERE messages_fts MATCH ?"
        args: list = [q]
        if network: sql += " AND m.network=?"; args.append(network)
        if room: sql += " AND m.room=?"; args.append(room)
        sql += " ORDER BY m.ts DESC LIMIT ?"; args.append(limit)
        try: return self.db.execute(sql, args).fetchall()
        except sqlite3.OperationalError: return []  # bad FTS syntax from the user -> empty, never a crash

    def mark_read(self, network: str, room: str, ts: str) -> None:
        with self._lock:
            self.db.execute("INSERT INTO read_markers VALUES(?,?,?) ON CONFLICT(network,room) DO UPDATE SET ts=excluded.ts WHERE excluded.ts>read_markers.ts", (network, room, ts)); self.db.commit()

    def read_marker(self, network: str, room: str) -> Optional[str]:
        r = self.db.execute("SELECT ts FROM read_markers WHERE network=? AND room=?", (network, room)).fetchone(); return r[0] if r else None

    def count(self, network: Optional[str] = None) -> int:
        return self.db.execute("SELECT COUNT(*) FROM messages" + (" WHERE network=?" if network else ""), (network,) if network else ()).fetchone()[0]

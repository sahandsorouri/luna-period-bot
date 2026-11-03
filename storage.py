"""SQLite storage.

users.blob holds everything personal (name, periods, logs, hints), encrypted per user.
Plain columns are only what the hourly job needs to pick who to message.
"""
from __future__ import annotations

import json
import secrets
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from crypto import Crypto

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY,
  role TEXT NOT NULL DEFAULT 'tracker',
  lang TEXT NOT NULL DEFAULT 'en',
  cal TEXT NOT NULL DEFAULT 'g',
  tz TEXT NOT NULL DEFAULT 'Asia/Dubai',
  notify_hour INTEGER NOT NULL DEFAULT 9,
  discreet INTEGER NOT NULL DEFAULT 0,
  daily_reminder INTEGER NOT NULL DEFAULT 0,
  show_fertile INTEGER NOT NULL DEFAULT 1,
  onboarded INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  blob BLOB
);
CREATE TABLE IF NOT EXISTS links(
  owner_id INTEGER PRIMARY KEY,
  partner_id INTEGER NOT NULL UNIQUE,
  flags TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invites(
  token_hash TEXT PRIMARY KEY,
  owner_id INTEGER NOT NULL,
  flags TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
"""

COLS = ["role", "lang", "cal", "tz", "notify_hour", "discreet", "daily_reminder",
        "show_fertile", "onboarded"]
BOOLS = {"discreet", "daily_reminder", "show_fertile", "onboarded"}

FLAG_KEYS = ["phase", "start", "pms", "late", "mood", "fertile"]
DEFAULT_FLAGS = {"phase": True, "start": True, "pms": True, "late": True,
                 "mood": False, "fertile": False}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class User:
    id: int
    role: str = "tracker"
    lang: str = "en"
    cal: str = "g"
    tz: str = "Asia/Dubai"
    notify_hour: int = 9
    discreet: bool = False
    daily_reminder: bool = False
    show_fertile: bool = True
    onboarded: bool = False
    created_at: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class Link:
    owner_id: int
    partner_id: int
    flags: dict


class Store:
    def __init__(self, path: str, crypto: Crypto):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self.c = crypto

    # ---- users ----
    def get(self, uid: int) -> User | None:
        r = self.db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        if not r:
            return None
        kw = {k: (bool(r[k]) if k in BOOLS else r[k]) for k in COLS}
        return User(id=r["id"], created_at=r["created_at"], data=self.c.dec(uid, r["blob"]), **kw)

    def create(self, uid: int, lang: str, role: str = "tracker") -> User:
        u = User(id=uid, lang=lang, role=role, cal="j" if lang == "fa" else "g",
                 tz="Asia/Tehran" if lang == "fa" else "Asia/Dubai",
                 created_at=now_utc().isoformat(timespec="seconds"))
        self.save(u, insert=True)
        return u

    def save(self, u: User, insert: bool = False) -> None:
        vals = [int(getattr(u, k)) if k in BOOLS else getattr(u, k) for k in COLS]
        blob = self.c.enc(u.id, u.data)
        if insert:
            self.db.execute(
                f"INSERT OR REPLACE INTO users(id,{','.join(COLS)},created_at,blob) "
                f"VALUES(?,{','.join('?' * len(COLS))},?,?)",
                [u.id, *vals, u.created_at, blob])
        else:
            self.db.execute(
                f"UPDATE users SET {','.join(k + '=?' for k in COLS)},blob=? WHERE id=?",
                [*vals, blob, u.id])
        self.db.commit()

    def delete(self, uid: int) -> None:
        self.db.execute("DELETE FROM users WHERE id=?", (uid,))
        self.db.execute("DELETE FROM links WHERE owner_id=? OR partner_id=?", (uid, uid))
        self.db.execute("DELETE FROM invites WHERE owner_id=?", (uid,))
        self.db.commit()

    def all_ids(self) -> list[int]:
        return [r[0] for r in self.db.execute("SELECT id FROM users WHERE onboarded=1")]

    # ---- links ----
    def _link(self, r) -> Link | None:
        return Link(r["owner_id"], r["partner_id"], json.loads(r["flags"])) if r else None

    def link_by_owner(self, uid: int) -> Link | None:
        return self._link(self.db.execute(
            "SELECT * FROM links WHERE owner_id=?", (uid,)).fetchone())

    def link_by_partner(self, uid: int) -> Link | None:
        return self._link(self.db.execute(
            "SELECT * FROM links WHERE partner_id=?", (uid,)).fetchone())

    def create_link(self, owner: int, partner: int, flags: dict) -> None:
        self.db.execute("INSERT INTO links VALUES(?,?,?,?)",
                        (owner, partner, json.dumps(flags), now_utc().isoformat()))
        self.db.commit()

    def set_flags(self, owner: int, flags: dict) -> None:
        self.db.execute("UPDATE links SET flags=? WHERE owner_id=?", (json.dumps(flags), owner))
        self.db.commit()

    def delete_link(self, owner: int) -> None:
        self.db.execute("DELETE FROM links WHERE owner_id=?", (owner,))
        self.db.commit()

    # ---- invites (one-time, expiring, stored as HMAC) ----
    def create_invite(self, owner: int, flags: dict, ttl_hours: int) -> str:
        self.db.execute("DELETE FROM invites WHERE owner_id=? OR expires_at<?",
                        (owner, now_utc().isoformat()))
        token = secrets.token_urlsafe(16)
        exp = (now_utc() + timedelta(hours=ttl_hours)).isoformat()
        self.db.execute("INSERT INTO invites VALUES(?,?,?,?)",
                        (self.c.token_hash(token), owner, json.dumps(flags), exp))
        self.db.commit()
        return token

    def peek_invite(self, token: str) -> tuple[int, dict] | None:
        r = self.db.execute("SELECT * FROM invites WHERE token_hash=?",
                            (self.c.token_hash(token),)).fetchone()
        if not r or r["expires_at"] < now_utc().isoformat():
            return None
        return r["owner_id"], json.loads(r["flags"])

    def drop_invite(self, token: str) -> None:
        self.db.execute("DELETE FROM invites WHERE token_hash=?", (self.c.token_hash(token),))
        self.db.commit()

    def has_invite(self, owner: int) -> bool:
        return self.db.execute("SELECT 1 FROM invites WHERE owner_id=? AND expires_at>=?",
                               (owner, now_utc().isoformat())).fetchone() is not None

    def cancel_invites(self, owner: int) -> None:
        self.db.execute("DELETE FROM invites WHERE owner_id=?", (owner,))
        self.db.commit()

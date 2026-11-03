"""Encryption at rest.

Each user's health data is one JSON blob, encrypted with a Fernet key that is
derived from MASTER_KEY and the user's id (HKDF-SHA256). A copied database file
alone is unreadable. Invite tokens are never stored, only their HMAC.
"""
import base64
import hashlib
import hmac
import json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def decode_master(s: str) -> bytes:
    raw = base64.urlsafe_b64decode(s.strip().encode())
    if len(raw) < 32:
        raise ValueError("MASTER_KEY must be 32+ bytes, urlsafe base64")
    return raw


class Crypto:
    def __init__(self, master: bytes):
        self.master = master
        self._cache: dict[int, Fernet] = {}

    def _f(self, uid: int) -> Fernet:
        f = self._cache.get(uid)
        if f is None:
            key = HKDF(algorithm=hashes.SHA256(), length=32, salt=b"luna-v1",
                       info=f"user:{uid}".encode()).derive(self.master)
            f = self._cache[uid] = Fernet(base64.urlsafe_b64encode(key))
        return f

    def enc(self, uid: int, obj: dict) -> bytes:
        return self._f(uid).encrypt(json.dumps(obj, separators=(",", ":")).encode())

    def dec(self, uid: int, blob: bytes | None) -> dict:
        if not blob:
            return {}
        return json.loads(self._f(uid).decrypt(blob))

    def token_hash(self, token: str) -> str:
        return hmac.new(self.master, token.encode(), hashlib.sha256).hexdigest()

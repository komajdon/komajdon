from __future__ import annotations

import time
from typing import Any


class Cache:
    """In-memory cache with TTL. Swap for Redis later without changing callers."""

    def __init__(self):
        self._store: dict[str, tuple[float, Any]] = {}

    def _key(self, prefix: str, *parts: str) -> str:
        return f"{prefix}:{':'.join(parts)}"

    def get(self, prefix: str, *parts: str) -> Any | None:
        key = self._key(prefix, *parts)
        entry = self._store.get(key)
        if entry is None:
            return None
        expires, value = entry
        if expires < time.monotonic():
            self._store.pop(key, None)
            return None
        return value

    def set(self, prefix: str, value: Any, ttl: float = 30.0, *parts: str) -> None:
        key = self._key(prefix, *parts)
        self._store[key] = (time.monotonic() + ttl, value)

    def invalidate_prefix(self, prefix: str) -> None:
        prefix_match = f"{prefix}:"
        keys = [k for k in self._store if k.startswith(prefix_match)]
        for k in keys:
            del self._store[k]


cache = Cache()

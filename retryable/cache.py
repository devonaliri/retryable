"""Result caching for successful retry outcomes."""
from __future__ import annotations

import hashlib
import pickle
import time
from typing import Any, Callable, Dict, Optional, Tuple


class CacheEntry:
    """A single cached result with an optional expiry."""

    def __init__(self, value: Any, ttl: Optional[float] = None) -> None:
        self.value = value
        self.created_at: float = time.monotonic()
        self.ttl = ttl

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return (time.monotonic() - self.created_at) >= self.ttl


class RetryCache:
    """In-memory cache that stores successful call results keyed by arguments.

    When a decorated function succeeds after retries the result can be stored
    so that identical future calls are served from cache without any attempts.
    """

    def __init__(self, ttl: Optional[float] = None, max_size: int = 256) -> None:
        if ttl is not None and ttl <= 0:
            raise ValueError("ttl must be a positive number")
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self._ttl = ttl
        self._max_size = max_size
        self._store: Dict[str, CacheEntry] = {}

    @property
    def ttl(self) -> Optional[float]:
        return self._ttl

    @property
    def max_size(self) -> int:
        return self._max_size

    def _make_key(self, args: Tuple, kwargs: Dict) -> str:
        try:
            raw = pickle.dumps((args, sorted(kwargs.items())))
        except Exception:
            raw = str((args, kwargs)).encode()
        return hashlib.sha256(raw).hexdigest()

    def get(self, args: Tuple, kwargs: Dict) -> Tuple[bool, Any]:
        """Return (hit, value). hit is False when missing or expired."""
        key = self._make_key(args, kwargs)
        entry = self._store.get(key)
        if entry is None:
            return False, None
        if entry.is_expired:
            del self._store[key]
            return False, None
        return True, entry.value

    def put(self, args: Tuple, kwargs: Dict, value: Any) -> None:
        """Store a successful result, evicting the oldest entry if at capacity."""
        if len(self._store) >= self._max_size:
            oldest_key = next(iter(self._store))
            del self._store[oldest_key]
        key = self._make_key(args, kwargs)
        self._store[key] = CacheEntry(value, ttl=self._ttl)

    def invalidate(self, args: Tuple, kwargs: Dict) -> bool:
        """Remove a specific entry. Returns True if it existed."""
        key = self._make_key(args, kwargs)
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Remove all cached entries."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def wrap(self, fn: Callable) -> Callable:
        """Return a thin wrapper that checks this cache before calling *fn*."""
        def cached(*args, **kwargs):
            hit, value = self.get(args, kwargs)
            if hit:
                return value
            result = fn(*args, **kwargs)
            self.put(args, kwargs, result)
            return result
        cached.__wrapped__ = fn  # type: ignore[attr-defined]
        return cached

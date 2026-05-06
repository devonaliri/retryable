"""Per-key retry quota enforcement.

Allows you to cap the total number of retry attempts across all calls
for a given key (e.g. a remote service name or endpoint).  Once the
quota is exhausted every subsequent attempt is denied until the quota
is explicitly reset.
"""
from __future__ import annotations

from threading import Lock
from typing import Dict, Optional


class QuotaExceeded(Exception):
    """Raised when a retry quota has been fully consumed."""

    def __init__(self, key: str, limit: int) -> None:
        self.key = key
        self.limit = limit
        super().__init__(f"Retry quota exceeded for '{key}' (limit={limit})")


class RetryQuota:
    """Track and enforce a maximum number of retry attempts per key.

    Parameters
    ----------
    limit:
        Maximum number of retry attempts allowed for any single key.
    """

    def __init__(self, limit: int) -> None:
        if limit <= 0:
            raise ValueError(f"limit must be a positive integer, got {limit!r}")
        self._limit = limit
        self._counts: Dict[str, int] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def limit(self) -> int:
        """The maximum number of retry attempts allowed per key."""
        return self._limit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def remaining(self, key: str) -> int:
        """Return the number of retry attempts still available for *key*."""
        with self._lock:
            return max(0, self._limit - self._counts.get(key, 0))

    def consume(self, key: str) -> bool:
        """Consume one retry attempt for *key*.

        Returns
        -------
        bool
            ``True`` if the attempt was allowed, ``False`` if the quota
            was already exhausted.
        """
        with self._lock:
            used = self._counts.get(key, 0)
            if used >= self._limit:
                return False
            self._counts[key] = used + 1
            return True

    def reset(self, key: Optional[str] = None) -> None:
        """Reset the consumed count.

        If *key* is given only that key is reset; otherwise **all** keys
        are cleared.
        """
        with self._lock:
            if key is None:
                self._counts.clear()
            else:
                self._counts.pop(key, None)

    def is_exhausted(self, key: str) -> bool:
        """Return ``True`` when the quota for *key* has been fully consumed."""
        return self.remaining(key) == 0

    def __repr__(self) -> str:  # pragma: no cover
        return f"RetryQuota(limit={self._limit})"

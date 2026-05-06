"""Fingerprinting: group retry calls by a stable string key derived from context."""
from __future__ import annotations

import hashlib
import re
from typing import Callable, Optional

from retryable.context import RetryContext


def _sanitise(name: str) -> str:
    """Replace non-alphanumeric runs with underscores and lowercase."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def default_fingerprint(ctx: RetryContext) -> str:
    """Return a fingerprint based on the callable's qualified name."""
    fn = ctx.fn
    qualname = getattr(fn, "__qualname__", None) or getattr(fn, "__name__", repr(fn))
    module = getattr(fn, "__module__", "unknown") or "unknown"
    return f"{_sanitise(module)}.{_sanitise(qualname)}"


def hashed_fingerprint(ctx: RetryContext, length: int = 8) -> str:
    """Return a short hex-digest fingerprint of the default key."""
    key = default_fingerprint(ctx)
    digest = hashlib.sha256(key.encode()).hexdigest()
    return digest[:length]


class FingerprintRegistry:
    """Map fingerprint strings to call counts and latest contexts."""

    def __init__(self, strategy: Optional[Callable[[RetryContext], str]] = None) -> None:
        self._strategy: Callable[[RetryContext], str] = strategy or default_fingerprint
        self._counts: dict[str, int] = {}
        self._latest: dict[str, RetryContext] = {}

    def record(self, ctx: RetryContext) -> str:
        """Compute fingerprint, update registry, return the fingerprint."""
        fp = self._strategy(ctx)
        self._counts[fp] = self._counts.get(fp, 0) + 1
        self._latest[fp] = ctx
        return fp

    def count(self, fingerprint: str) -> int:
        """Return how many times *fingerprint* has been recorded."""
        return self._counts.get(fingerprint, 0)

    def latest(self, fingerprint: str) -> Optional[RetryContext]:
        """Return the most recent context for *fingerprint*, or None."""
        return self._latest.get(fingerprint)

    @property
    def all_fingerprints(self) -> list[str]:
        """Return all known fingerprints sorted alphabetically."""
        return sorted(self._counts)

    def __repr__(self) -> str:  # pragma: no cover
        return f"FingerprintRegistry(tracked={len(self._counts)})"

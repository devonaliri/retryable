"""Sentinel values and markers for retry state transitions."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional


class SentinelKind(Enum):
    """Classifies why a sentinel was raised during retry execution."""
    SKIP = auto()       # skip this attempt, do not count as failure
    ABORT = auto()      # stop retrying immediately, surface the cause
    SUCCEED = auto()    # treat this attempt as successful with a given value


@dataclass
class RetrySentinel:
    """Carries a control signal that alters the retry loop's behaviour."""

    kind: SentinelKind
    value: Any = None
    reason: str = ""
    timestamp: float = field(default_factory=time.monotonic)

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def skip(cls, reason: str = "") -> "RetrySentinel":
        """Signal that the current attempt should be silently skipped."""
        return cls(kind=SentinelKind.SKIP, reason=reason)

    @classmethod
    def abort(cls, reason: str = "") -> "RetrySentinel":
        """Signal that retrying should stop immediately."""
        return cls(kind=SentinelKind.ABORT, reason=reason)

    @classmethod
    def succeed(cls, value: Any = None, reason: str = "") -> "RetrySentinel":
        """Signal that the retry loop should exit with *value* as the result."""
        return cls(kind=SentinelKind.SUCCEED, value=value, reason=reason)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def is_skip(self) -> bool:
        return self.kind is SentinelKind.SKIP

    def is_abort(self) -> bool:
        return self.kind is SentinelKind.ABORT

    def is_succeed(self) -> bool:
        return self.kind is SentinelKind.SUCCEED

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"RetrySentinel(kind={self.kind.name}, "
            f"value={self.value!r}, reason={self.reason!r})"
        )


class SentinelRaised(Exception):
    """Internal exception used to propagate a RetrySentinel through the call stack."""

    def __init__(self, sentinel: RetrySentinel) -> None:
        self.sentinel = sentinel
        super().__init__(repr(sentinel))

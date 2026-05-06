"""Correlation ID tracking for retry attempts.

Associates a unique correlation ID with each top-level call so that all
attempts belonging to the same logical operation can be linked together.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class CorrelationEntry:
    """Record of a single top-level call and its attempt IDs."""

    correlation_id: str
    attempt_ids: List[str] = field(default_factory=list)

    def add_attempt(self) -> str:
        """Generate and store a new attempt ID, returning it."""
        attempt_id = str(uuid.uuid4())
        self.attempt_ids.append(attempt_id)
        return attempt_id

    @property
    def total_attempts(self) -> int:
        return len(self.attempt_ids)


class CorrelationTracker:
    """Maintains a registry of correlation entries keyed by correlation ID."""

    def __init__(self, id_factory: Callable[[], str] = lambda: str(uuid.uuid4())) -> None:
        if not callable(id_factory):
            raise TypeError("id_factory must be callable")
        self._id_factory = id_factory
        self._entries: Dict[str, CorrelationEntry] = {}

    def new_call(self) -> CorrelationEntry:
        """Create and register a new correlation entry for a top-level call."""
        cid = self._id_factory()
        entry = CorrelationEntry(correlation_id=cid)
        self._entries[cid] = entry
        return entry

    def get(self, correlation_id: str) -> Optional[CorrelationEntry]:
        return self._entries.get(correlation_id)

    def all_entries(self) -> List[CorrelationEntry]:
        return list(self._entries.values())

    def total_calls(self) -> int:
        return len(self._entries)

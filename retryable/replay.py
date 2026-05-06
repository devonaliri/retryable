"""Replay log: records every attempt across retried calls for post-mortem inspection."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import List, Optional

from retryable.context import AttemptRecord, RetryContext


@dataclass
class CallReplay:
    """All attempt records for a single retried function invocation."""

    fn_name: str
    attempts: List[AttemptRecord] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        """True when the final recorded attempt has no exception."""
        return bool(self.attempts) and self.attempts[-1].exception is None

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    @property
    def total_delay(self) -> float:
        return sum(a.delay for a in self.attempts)

    def __repr__(self) -> str:  # pragma: no cover
        status = "ok" if self.succeeded else "failed"
        return (
            f"<CallReplay fn={self.fn_name!r} attempts={self.total_attempts} "
            f"delay={self.total_delay:.3f}s status={status}>"
        )


class ReplayLog:
    """Thread-safe store of :class:`CallReplay` entries."""

    def __init__(self, max_entries: int = 1000) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        self._max_entries = max_entries
        self._entries: List[CallReplay] = []
        self._lock = threading.Lock()

    @property
    def max_entries(self) -> int:
        return self._max_entries

    def record(self, replay: CallReplay) -> None:
        """Append *replay*, evicting the oldest entry when the log is full."""
        with self._lock:
            if len(self._entries) >= self._max_entries:
                self._entries.pop(0)
            self._entries.append(replay)

    def entries(self) -> List[CallReplay]:
        """Return a snapshot of all recorded replays."""
        with self._lock:
            return list(self._entries)

    def latest(self) -> Optional[CallReplay]:
        with self._lock:
            return self._entries[-1] if self._entries else None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def failed_entries(self) -> List[CallReplay]:
        """Return a snapshot of all recorded replays that did not succeed."""
        with self._lock:
            return [e for e in self._entries if not e.succeeded]

    def make_hooks(self, fn_name: str):
        """Return *(before_hook, after_hook)* suitable for use with :class:`HookSet`."""
        state: dict = {}

        def before_hook(ctx: RetryContext) -> None:
            if "replay" not in state:
                state["replay"] = CallReplay(fn_name=fn_name)

        def after_hook(ctx: RetryContext, record: AttemptRecord) -> None:
            replay: CallReplay = state.setdefault(
                "replay", CallReplay(fn_name=fn_name)
            )
            replay.attempts.append(record)
            if record.exception is None or ctx.is_exhausted:
                self.record(replay)
                state.clear()

        return before_hook, after_hook

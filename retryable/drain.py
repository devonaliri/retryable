"""RetryDrain — collects and flushes buffered retry events in batches."""
from __future__ import annotations

from collections import deque
from threading import Lock
from typing import Callable, Deque, List, Optional

from retryable.event_log import RetryEvent


class DrainOverflow(Exception):
    """Raised when the drain buffer exceeds its configured capacity."""


class RetryDrain:
    """Thread-safe buffer that accumulates :class:`RetryEvent` objects and
    flushes them to a sink in configurable batch sizes.

    Parameters
    ----------
    sink:
        Callable that receives a list of events on each flush.
    batch_size:
        Maximum number of events sent to *sink* in a single flush call.
    max_capacity:
        Hard upper bound on buffered events.  ``None`` means unbounded.
    """

    def __init__(
        self,
        sink: Callable[[List[RetryEvent]], None],
        *,
        batch_size: int = 50,
        max_capacity: Optional[int] = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        if max_capacity is not None and max_capacity < batch_size:
            raise ValueError("max_capacity must be >= batch_size")

        self._sink = sink
        self._batch_size = batch_size
        self._max_capacity = max_capacity
        self._buffer: Deque[RetryEvent] = deque()
        self._lock = Lock()
        self._total_flushed = 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def batch_size(self) -> int:
        return self._batch_size

    @property
    def max_capacity(self) -> Optional[int]:
        return self._max_capacity

    @property
    def pending(self) -> int:
        """Number of events currently buffered."""
        with self._lock:
            return len(self._buffer)

    @property
    def total_flushed(self) -> int:
        """Cumulative number of events sent to the sink."""
        return self._total_flushed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def put(self, event: RetryEvent) -> None:
        """Add *event* to the buffer, auto-flushing when a full batch is ready."""
        with self._lock:
            if self._max_capacity is not None and len(self._buffer) >= self._max_capacity:
                raise DrainOverflow(
                    f"RetryDrain buffer full ({self._max_capacity} events)"
                )
            self._buffer.append(event)
            if len(self._buffer) >= self._batch_size:
                self._flush_locked()

    def flush(self) -> int:
        """Immediately flush all buffered events.  Returns the count sent."""
        with self._lock:
            return self._flush_locked()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _flush_locked(self) -> int:
        """Must be called with *self._lock* held."""
        if not self._buffer:
            return 0
        batch: List[RetryEvent] = []
        while self._buffer and len(batch) < self._batch_size:
            batch.append(self._buffer.popleft())
        self._sink(batch)
        self._total_flushed += len(batch)
        return len(batch)

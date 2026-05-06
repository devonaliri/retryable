"""Telemetry: structured event emission for retry lifecycle hooks."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TelemetryEvent:
    """A single structured event emitted during retry execution."""

    event_type: str  # 'before_attempt' | 'after_attempt' | 'exhausted' | 'success'
    attempt_number: int
    timestamp: float = field(default_factory=time.time)
    elapsed: Optional[float] = None
    exception_type: Optional[str] = None
    delay: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp,
            "elapsed": self.elapsed,
            "exception_type": self.exception_type,
            "delay": self.delay,
            "metadata": self.metadata,
        }


Sink = Callable[[TelemetryEvent], None]


class TelemetryCollector:
    """Collects telemetry events and dispatches them to registered sinks."""

    def __init__(self) -> None:
        self._sinks: List[Sink] = []
        self._events: List[TelemetryEvent] = []

    def add_sink(self, sink: Sink) -> None:
        """Register a callable that receives each TelemetryEvent."""
        if not callable(sink):
            raise TypeError("sink must be callable")
        self._sinks.append(sink)

    def emit(self, event: TelemetryEvent) -> None:
        """Record an event and dispatch it to all sinks."""
        self._events.append(event)
        for sink in self._sinks:
            sink(event)

    @property
    def events(self) -> List[TelemetryEvent]:
        return list(self._events)

    def clear(self) -> None:
        self._events.clear()

    def __len__(self) -> int:
        return len(self._events)

"""Export utilities: convert collected telemetry to JSON or CSV."""
from __future__ import annotations

import csv
import io
import json
from typing import List

from retryable.telemetry import TelemetryEvent


def to_json(events: List[TelemetryEvent], *, indent: int = 2) -> str:
    """Serialise a list of TelemetryEvents to a JSON string."""
    return json.dumps([e.as_dict() for e in events], indent=indent, default=str)


def to_csv(events: List[TelemetryEvent]) -> str:
    """Serialise a list of TelemetryEvents to a CSV string."""
    if not events:
        return ""
    fieldnames = list(events[0].as_dict().keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for event in events:
        row = event.as_dict()
        # Flatten metadata to a string so CSV stays flat
        row["metadata"] = json.dumps(row["metadata"], default=str)
        writer.writerow(row)
    return buf.getvalue()


def summary(events: List[TelemetryEvent]) -> dict:
    """Return a high-level summary dict from a list of events."""
    total = len(events)
    successes = sum(1 for e in events if e.event_type == "success")
    failures = sum(1 for e in events if e.event_type == "after_attempt" and e.exception_type)
    exc_counts: dict = {}
    for e in events:
        if e.exception_type:
            exc_counts[e.exception_type] = exc_counts.get(e.exception_type, 0) + 1
    return {
        "total_events": total,
        "successes": successes,
        "failures": failures,
        "exception_counts": exc_counts,
    }

"""Trace support: attach a unique trace ID to each top-level retry call
and propagate attempt-level span IDs through context metadata.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RetrySpan:
    """Represents a single attempt within a traced retry call."""

    trace_id: str
    span_id: str
    attempt_number: int
    succeeded: bool
    exception_type: Optional[str] = None

    def as_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "attempt_number": self.attempt_number,
            "succeeded": self.succeeded,
            "exception_type": self.exception_type,
        }


@dataclass
class RetryTrace:
    """Accumulates all spans for a single retry call."""

    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    spans: List[RetrySpan] = field(default_factory=list)

    def add_span(self, attempt_number: int, succeeded: bool,
                 exception_type: Optional[str] = None) -> RetrySpan:
        span = RetrySpan(
            trace_id=self.trace_id,
            span_id=uuid.uuid4().hex,
            attempt_number=attempt_number,
            succeeded=succeeded,
            exception_type=exception_type,
        )
        self.spans.append(span)
        return span

    @property
    def total_spans(self) -> int:
        return len(self.spans)

    @property
    def succeeded(self) -> bool:
        return bool(self.spans) and self.spans[-1].succeeded

    def as_dict(self) -> Dict:
        return {
            "trace_id": self.trace_id,
            "succeeded": self.succeeded,
            "total_spans": self.total_spans,
            "spans": [s.as_dict() for s in self.spans],
        }

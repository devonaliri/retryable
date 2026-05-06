"""Tests for RetryDrain and its integration hook-set."""
from __future__ import annotations

import time
from typing import List

import pytest

from retryable.context import AttemptRecord, RetryContext
from retryable.drain import DrainOverflow, RetryDrain
from retryable.drain_integration import make_drain_hookset
from retryable.event_log import RetryEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect() -> tuple[list, callable]:
    """Return (bucket, sink) where sink appends batches to bucket."""
    bucket: list = []

    def sink(batch: List[RetryEvent]) -> None:
        bucket.extend(batch)

    return bucket, sink


def _record(exc=None, delay=0.0) -> AttemptRecord:
    return AttemptRecord(exception=exc, delay=delay)


def _ctx() -> RetryContext:
    ctx = RetryContext()
    ctx.record_attempt(_record())
    return ctx


# ---------------------------------------------------------------------------
# RetryDrain — init
# ---------------------------------------------------------------------------

class TestRetryDrainInit:
    def test_valid_construction(self):
        _, sink = _collect()
        d = RetryDrain(sink)
        assert d.batch_size == 50
        assert d.max_capacity is None
        assert d.pending == 0
        assert d.total_flushed == 0

    def test_custom_batch_size(self):
        _, sink = _collect()
        d = RetryDrain(sink, batch_size=10)
        assert d.batch_size == 10

    def test_zero_batch_size_raises(self):
        _, sink = _collect()
        with pytest.raises(ValueError, match="batch_size"):
            RetryDrain(sink, batch_size=0)

    def test_capacity_less_than_batch_raises(self):
        _, sink = _collect()
        with pytest.raises(ValueError, match="max_capacity"):
            RetryDrain(sink, batch_size=10, max_capacity=5)


# ---------------------------------------------------------------------------
# RetryDrain — behaviour
# ---------------------------------------------------------------------------

class TestRetryDrainBehaviour:
    def _event(self) -> RetryEvent:
        return RetryEvent(kind="failure", attempt=1, delay=0.0)

    def test_put_accumulates_pending(self):
        bucket, sink = _collect()
        d = RetryDrain(sink, batch_size=5)
        for _ in range(3):
            d.put(self._event())
        assert d.pending == 3
        assert bucket == []

    def test_auto_flush_on_full_batch(self):
        bucket, sink = _collect()
        d = RetryDrain(sink, batch_size=3)
        for _ in range(3):
            d.put(self._event())
        assert len(bucket) == 3
        assert d.pending == 0
        assert d.total_flushed == 3

    def test_manual_flush_sends_partial_batch(self):
        bucket, sink = _collect()
        d = RetryDrain(sink, batch_size=10)
        d.put(self._event())
        d.put(self._event())
        sent = d.flush()
        assert sent == 2
        assert len(bucket) == 2

    def test_flush_empty_returns_zero(self):
        _, sink = _collect()
        d = RetryDrain(sink, batch_size=5)
        assert d.flush() == 0

    def test_overflow_raises(self):
        _, sink = _collect()
        d = RetryDrain(sink, batch_size=5, max_capacity=5)
        for _ in range(5):
            d.put(self._event())
        # buffer is now flushed automatically; fill again to trigger overflow
        # Fill without triggering auto-flush by using batch_size=10, cap=3
        _, sink2 = _collect()
        d2 = RetryDrain(sink2, batch_size=10, max_capacity=3)
        for _ in range(3):
            d2.put(self._event())
        with pytest.raises(DrainOverflow):
            d2.put(self._event())


# ---------------------------------------------------------------------------
# drain_integration
# ---------------------------------------------------------------------------

class TestDrainIntegration:
    def test_hookset_and_drain_returned(self):
        _, sink = _collect()
        hooks, drain = make_drain_hookset(sink)
        assert drain is not None
        assert len(hooks._after) == 1

    def test_failure_event_buffered(self):
        bucket, sink = _collect()
        hooks, drain = make_drain_hookset(sink, batch_size=10)
        ctx = _ctx()
        rec = _record(exc=ValueError("boom"))
        hooks.fire_after_attempt(ctx, rec)
        assert drain.pending == 1
        assert bucket == []

    def test_success_event_flushes_immediately(self):
        bucket, sink = _collect()
        hooks, drain = make_drain_hookset(sink, batch_size=10, flush_on_success=True)
        ctx = _ctx()
        rec = _record()
        hooks.fire_after_attempt(ctx, rec)
        assert len(bucket) == 1
        assert bucket[0].kind == "success"

    def test_no_flush_on_success_when_disabled(self):
        bucket, sink = _collect()
        hooks, drain = make_drain_hookset(sink, batch_size=10, flush_on_success=False)
        ctx = _ctx()
        hooks.fire_after_attempt(ctx, _record())
        assert drain.pending == 1
        assert bucket == []

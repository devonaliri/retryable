"""Integration tests for correlation hooks wired into the retry decorator."""
from __future__ import annotations

from retryable.context import AttemptRecord, RetryContext
from retryable.correlation import CorrelationTracker
from retryable.correlation_integration import _ENTRY_ATTR, make_correlation_hookset
from retryable.hooks import HookSet


def _make_ctx() -> RetryContext:
    return RetryContext()


def _make_record(exc=None) -> AttemptRecord:
    return AttemptRecord(exception=exc)


class TestCorrelationHookSet:
    def test_before_first_attempt_creates_entry(self):
        tracker = CorrelationTracker()
        hooks = make_correlation_hookset(tracker)
        ctx = _make_ctx()
        hooks.fire_before_attempt(ctx)
        assert tracker.total_calls() == 1
        entry = getattr(ctx, _ENTRY_ATTR)
        assert entry.total_attempts == 1

    def test_metadata_populated_with_ids(self):
        tracker = CorrelationTracker()
        hooks = make_correlation_hookset(tracker)
        ctx = _make_ctx()
        hooks.fire_before_attempt(ctx)
        assert "correlation_id" in ctx.metadata
        assert "attempt_id" in ctx.metadata

    def test_subsequent_attempts_reuse_correlation_id(self):
        tracker = CorrelationTracker()
        hooks = make_correlation_hookset(tracker)
        ctx = _make_ctx()
        hooks.fire_before_attempt(ctx)
        cid_first = ctx.metadata["correlation_id"]
        ctx.record_attempt(_make_record(exc=ValueError()))
        hooks.fire_before_attempt(ctx)
        cid_second = ctx.metadata["correlation_id"]
        assert cid_first == cid_second
        assert tracker.total_calls() == 1

    def test_attempt_ids_are_unique_across_retries(self):
        tracker = CorrelationTracker()
        hooks = make_correlation_hookset(tracker)
        ctx = _make_ctx()
        hooks.fire_before_attempt(ctx)
        aid1 = ctx.metadata["attempt_id"]
        ctx.record_attempt(_make_record(exc=ValueError()))
        hooks.fire_before_attempt(ctx)
        aid2 = ctx.metadata["attempt_id"]
        assert aid1 != aid2

    def test_two_independent_calls_get_different_correlation_ids(self):
        tracker = CorrelationTracker()
        hooks = make_correlation_hookset(tracker)
        ctx1, ctx2 = _make_ctx(), _make_ctx()
        hooks.fire_before_attempt(ctx1)
        hooks.fire_before_attempt(ctx2)
        assert ctx1.metadata["correlation_id"] != ctx2.metadata["correlation_id"]
        assert tracker.total_calls() == 2

    def test_after_attempt_does_not_raise(self):
        tracker = CorrelationTracker()
        hooks = make_correlation_hookset(tracker)
        ctx = _make_ctx()
        hooks.fire_before_attempt(ctx)
        hooks.fire_after_attempt(ctx, _make_record())

"""Tests for retryable.replay."""

from __future__ import annotations

import pytest

from retryable.context import AttemptRecord, RetryContext
from retryable.replay import CallReplay, ReplayLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record(exc=None, delay=0.0) -> AttemptRecord:
    r = AttemptRecord(delay=delay)
    if exc is not None:
        r.exception = exc
    return r


def _ctx(exhausted: bool = False) -> RetryContext:
    ctx = RetryContext(max_attempts=3)
    ctx.is_exhausted = exhausted
    return ctx


# ---------------------------------------------------------------------------
# CallReplay
# ---------------------------------------------------------------------------

class TestCallReplay:
    def test_succeeded_false_when_empty(self):
        r = CallReplay(fn_name="f")
        assert r.succeeded is False

    def test_succeeded_true_when_last_attempt_ok(self):
        r = CallReplay(fn_name="f", attempts=[_record(), ])
        assert r.succeeded is True

    def test_succeeded_false_when_last_attempt_failed(self):
        r = CallReplay(fn_name="f", attempts=[_record(exc=ValueError())])
        assert r.succeeded is False

    def test_total_attempts(self):
        r = CallReplay(fn_name="f", attempts=[_record(), _record()])
        assert r.total_attempts == 2

    def test_total_delay_sums_delays(self):
        r = CallReplay(fn_name="f", attempts=[_record(delay=0.5), _record(delay=1.5)])
        assert r.total_delay == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# ReplayLog init
# ---------------------------------------------------------------------------

class TestReplayLogInit:
    def test_valid_construction(self):
        log = ReplayLog(max_entries=10)
        assert log.max_entries == 10

    def test_zero_max_entries_raises(self):
        with pytest.raises(ValueError):
            ReplayLog(max_entries=0)

    def test_negative_max_entries_raises(self):
        with pytest.raises(ValueError):
            ReplayLog(max_entries=-5)

    def test_default_max_entries(self):
        log = ReplayLog()
        assert log.max_entries == 1000


# ---------------------------------------------------------------------------
# ReplayLog behaviour
# ---------------------------------------------------------------------------

class TestReplayLogBehaviour:
    def _replay(self, name="fn", ok=True) -> CallReplay:
        exc = None if ok else ValueError("boom")
        return CallReplay(fn_name=name, attempts=[_record(exc=exc)])

    def test_entries_empty_initially(self):
        assert ReplayLog().entries() == []

    def test_latest_none_when_empty(self):
        assert ReplayLog().latest() is None

    def test_record_and_latest(self):
        log = ReplayLog()
        r = self._replay()
        log.record(r)
        assert log.latest() is r

    def test_evicts_oldest_when_full(self):
        log = ReplayLog(max_entries=2)
        r1, r2, r3 = self._replay("a"), self._replay("b"), self._replay("c")
        log.record(r1)
        log.record(r2)
        log.record(r3)
        entries = log.entries()
        assert len(entries) == 2
        assert r1 not in entries
        assert r3 in entries

    def test_clear_empties_log(self):
        log = ReplayLog()
        log.record(self._replay())
        log.clear()
        assert log.entries() == []

    def test_entries_returns_snapshot(self):
        log = ReplayLog()
        snapshot = log.entries()
        log.record(self._replay())
        assert snapshot == []  # original snapshot unaffected


# ---------------------------------------------------------------------------
# make_hooks integration
# ---------------------------------------------------------------------------

class TestMakeHooks:
    def test_successful_call_recorded(self):
        log = ReplayLog()
        before, after = log.make_hooks("my_fn")
        ctx = _ctx(exhausted=False)
        before(ctx)
        after(ctx, _record())  # success -> flushed immediately
        assert len(log.entries()) == 1
        assert log.latest().succeeded is True

    def test_failed_exhausted_call_recorded(self):
        log = ReplayLog()
        before, after = log.make_hooks("my_fn")
        ctx = _ctx(exhausted=True)
        before(ctx)
        after(ctx, _record(exc=RuntimeError()))
        assert len(log.entries()) == 1
        assert log.latest().succeeded is False

    def test_intermediate_failure_not_flushed(self):
        log = ReplayLog()
        before, after = log.make_hooks("my_fn")
        ctx = _ctx(exhausted=False)
        before(ctx)
        after(ctx, _record(exc=ValueError()))  # still retrying
        assert len(log.entries()) == 0

    def test_attempts_accumulated_before_flush(self):
        log = ReplayLog()
        before, after = log.make_hooks("fn")
        ctx_mid = _ctx(exhausted=False)
        ctx_last = _ctx(exhausted=False)
        before(ctx_mid)
        after(ctx_mid, _record(exc=ValueError(), delay=0.1))  # retry
        after(ctx_last, _record(delay=0.2))                   # success
        assert log.latest().total_attempts == 2
        assert log.latest().total_delay == pytest.approx(0.3)

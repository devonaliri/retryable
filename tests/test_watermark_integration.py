"""Integration tests for watermark hooks wired into a RetryPolicy."""
import pytest

from retryable.context import AttemptRecord, RetryContext
from retryable.watermark import Watermark
from retryable.watermark_integration import make_watermark_hookset
from retryable.policy import RetryPolicy
from retryable.predicates import on_all_exceptions


def _make_ctx(history=None):
    ctx = RetryContext(fn_name="test_fn")
    for rec in (history or []):
        ctx.record_attempt(rec)
    return ctx


def _make_record(delay: float = 0.0, exc=None) -> AttemptRecord:
    return AttemptRecord(delay=delay, exception=exc)


class TestMakeWatermarkHookSet:
    def test_returns_hookset_with_after_hook(self):
        from retryable.hooks import HookSet
        w = Watermark()
        hs = make_watermark_hookset(w)
        assert isinstance(hs, HookSet)
        assert len(hs.after_attempt) == 1

    def test_no_before_hooks_registered(self):
        w = Watermark()
        hs = make_watermark_hookset(w)
        assert len(hs.before_attempt) == 0

    def test_after_hook_updates_watermark(self):
        w = Watermark()
        hs = make_watermark_hookset(w)
        ctx = _make_ctx()
        ctx.record_attempt(_make_record(delay=1.0))
        ctx.record_attempt(_make_record(delay=2.0))
        record = _make_record(delay=0.5)
        ctx.record_attempt(record)
        hs.fire_after_attempt(ctx, record)
        assert w.peak_attempts == 3
        assert w.peak_delay == 0.5
        assert w.peak_total_delay == pytest.approx(3.5)

    def test_peak_grows_across_multiple_calls(self):
        w = Watermark()
        hs = make_watermark_hookset(w)

        ctx1 = _make_ctx()
        r1 = _make_record(delay=1.0)
        ctx1.record_attempt(r1)
        hs.fire_after_attempt(ctx1, r1)

        ctx2 = _make_ctx()
        r2a = _make_record(delay=2.0)
        r2b = _make_record(delay=3.0)
        ctx2.record_attempt(r2a)
        ctx2.record_attempt(r2b)
        hs.fire_after_attempt(ctx2, r2b)

        assert w.peak_attempts == 2
        assert w.peak_delay == 3.0
        assert w.peak_total_delay == pytest.approx(5.0)
        assert w.total_records == 2


class TestWatermarkWithPolicy:
    def test_policy_updates_watermark_on_success(self):
        w = Watermark()
        hs = make_watermark_hookset(w)

        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        policy = RetryPolicy(
            max_attempts=5,
            predicate=on_all_exceptions(),
            hooks=hs,
            wait=0.0,
        )
        result = policy(flaky)()
        assert result == "ok"
        assert w.peak_attempts >= 3
        assert w.total_records >= 1

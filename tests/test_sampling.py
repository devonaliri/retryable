"""Tests for retryable.sampling and retryable.sampling_integration."""
from __future__ import annotations

import pytest

from retryable.sampling import RetrySampler
from retryable.sampling_integration import (
    _SAMPLED_KEY,
    always_sample_hookset,
    make_sampled_hookset,
)
from retryable.context import RetryContext, AttemptRecord


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx() -> RetryContext:
    ctx = RetryContext()
    ctx.metadata = {}
    return ctx


def _record(exc: Exception | None = None) -> AttemptRecord:
    r = AttemptRecord()
    r.exception = exc
    r.delay = 0.0
    return r


# ---------------------------------------------------------------------------
# RetrySampler – initialisation
# ---------------------------------------------------------------------------

class TestRetrySamplerInit:
    def test_default_rate_is_one(self):
        s = RetrySampler()
        assert s.rate == 1.0

    def test_custom_rate_stored(self):
        s = RetrySampler(rate=0.5)
        assert s.rate == 0.5

    def test_zero_rate_raises(self):
        with pytest.raises(ValueError):
            RetrySampler(rate=0.0)

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError):
            RetrySampler(rate=-0.1)

    def test_rate_above_one_raises(self):
        with pytest.raises(ValueError):
            RetrySampler(rate=1.1)

    def test_initial_counters_zero(self):
        s = RetrySampler()
        assert s.total_calls == 0
        assert s.sampled_calls == 0


# ---------------------------------------------------------------------------
# RetrySampler – behaviour
# ---------------------------------------------------------------------------

class TestRetrySamplerBehaviour:
    def test_always_samples_at_rate_one(self):
        s = RetrySampler(rate=1.0)
        assert all(s.should_sample() for _ in range(10))

    def test_never_samples_when_rng_returns_one(self):
        s = RetrySampler(rate=0.5, rng=lambda: 1.0)
        for _ in range(5):
            assert s.should_sample() is False

    def test_always_samples_when_rng_returns_zero(self):
        s = RetrySampler(rate=0.5, rng=lambda: 0.0)
        for _ in range(5):
            assert s.should_sample() is True

    def test_total_calls_incremented(self):
        s = RetrySampler()
        s.should_sample()
        s.should_sample()
        assert s.total_calls == 2

    def test_sampled_calls_incremented_only_when_sampled(self):
        values = iter([0.0, 1.0, 0.0])
        s = RetrySampler(rate=0.5, rng=lambda: next(values))
        s.should_sample()  # sampled
        s.should_sample()  # not sampled
        s.should_sample()  # sampled
        assert s.sampled_calls == 2

    def test_effective_rate_none_before_calls(self):
        assert RetrySampler().effective_rate() is None

    def test_effective_rate_after_calls(self):
        values = iter([0.0, 1.0])
        s = RetrySampler(rate=0.5, rng=lambda: next(values))
        s.should_sample()
        s.should_sample()
        assert s.effective_rate() == 0.5

    def test_reset_clears_counters(self):
        s = RetrySampler()
        s.should_sample()
        s.reset()
        assert s.total_calls == 0
        assert s.sampled_calls == 0

    def test_reset_preserves_rate(self):
        s = RetrySampler(rate=0.3)
        s.reset()
        assert s.rate == 0.3


# ---------------------------------------------------------------------------
# sampling_integration
# ---------------------------------------------------------------------------

class TestMakeSampledHookset:
    def test_before_fires_when_sampled(self):
        fired = []
        s = RetrySampler(rate=1.0)
        hs = make_sampled_hookset(s, lambda ctx: fired.append("before"), lambda ctx, r: None)
        ctx = _ctx()
        hs.fire_before_attempt(ctx)
        assert fired == ["before"]

    def test_before_suppressed_when_not_sampled(self):
        fired = []
        s = RetrySampler(rate=0.5, rng=lambda: 1.0)  # never sampled
        hs = make_sampled_hookset(s, lambda ctx: fired.append("before"), lambda ctx, r: None)
        ctx = _ctx()
        hs.fire_before_attempt(ctx)
        assert fired == []

    def test_after_fires_when_sampled(self):
        fired = []
        s = RetrySampler(rate=1.0)
        hs = make_sampled_hookset(s, lambda ctx: None, lambda ctx, r: fired.append("after"))
        ctx = _ctx()
        hs.fire_before_attempt(ctx)
        hs.fire_after_attempt(ctx, _record())
        assert fired == ["after"]

    def test_after_suppressed_when_not_sampled(self):
        fired = []
        s = RetrySampler(rate=0.5, rng=lambda: 1.0)
        hs = make_sampled_hookset(s, lambda ctx: None, lambda ctx, r: fired.append("after"))
        ctx = _ctx()
        hs.fire_before_attempt(ctx)
        hs.fire_after_attempt(ctx, _record())
        assert fired == []

    def test_sampled_key_stored_in_metadata(self):
        s = RetrySampler(rate=1.0)
        hs = make_sampled_hookset(s, lambda ctx: None, lambda ctx, r: None)
        ctx = _ctx()
        hs.fire_before_attempt(ctx)
        assert ctx.metadata[_SAMPLED_KEY] is True

    def test_always_sample_hookset_fires_both(self):
        log = []
        hs = always_sample_hookset(
            lambda ctx: log.append("before"),
            lambda ctx, r: log.append("after"),
        )
        ctx = _ctx()
        hs.fire_before_attempt(ctx)
        hs.fire_after_attempt(ctx, _record())
        assert log == ["before", "after"]

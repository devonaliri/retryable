"""Integration tests: profiler hooks wired into the retry decorator."""

import pytest

from retryable.hooks import HookSet
from retryable.profiler import RetryProfiler
from retryable.profiler_integration import attach_profiler
from retryable.policy import RetryPolicy
from retryable.backoff import constant


def _make_hookset_and_profiler():
    hs = HookSet()
    rp = RetryProfiler()
    attach_profiler(hs, rp)
    return hs, rp


class TestProfilerIntegration:
    def test_success_on_first_attempt_records_one_profile(self):
        hs, rp = _make_hookset_and_profiler()
        policy = RetryPolicy(max_attempts=3, backoff=constant(0), hooks=hs)

        @policy
        def ok():
            return 42

        result = ok()
        assert result == 42
        assert rp.total_calls == 1
        assert rp.profiles[0].succeeded is True
        assert rp.profiles[0].total_attempts == 1

    def test_retried_success_records_profile(self):
        hs, rp = _make_hookset_and_profiler()
        policy = RetryPolicy(max_attempts=3, backoff=constant(0), hooks=hs)

        call_count = {"n": 0}

        @policy
        def flaky():
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise ValueError("not yet")
            return "done"

        result = flaky()
        assert result == "done"
        assert rp.total_calls == 1
        profile = rp.profiles[0]
        assert profile.succeeded is True
        assert profile.total_attempts == 3
        assert len(profile.attempt_durations) == 3

    def test_success_rate_across_multiple_calls(self):
        hs, rp = _make_hookset_and_profiler()
        policy = RetryPolicy(max_attempts=1, backoff=constant(0), hooks=hs)

        @policy
        def ok():
            return 1

        ok()
        ok()
        assert rp.total_calls == 2
        assert rp.success_rate == pytest.approx(1.0)

    def test_elapsed_is_positive(self):
        hs, rp = _make_hookset_and_profiler()
        policy = RetryPolicy(max_attempts=2, backoff=constant(0), hooks=hs)

        @policy
        def ok():
            return True

        ok()
        assert rp.profiles[0].total_elapsed >= 0.0

"""Unit tests for RetryProfiler and CallProfile."""

import pytest

from retryable.profiler import CallProfile, RetryProfiler


def _profile(attempts=1, succeeded=True, elapsed=0.1, durations=None):
    return CallProfile(
        total_attempts=attempts,
        succeeded=succeeded,
        total_elapsed=elapsed,
        attempt_durations=durations or [elapsed],
    )


class TestCallProfile:
    def test_average_attempt_duration_single(self):
        p = _profile(durations=[0.2])
        assert p.average_attempt_duration == pytest.approx(0.2)

    def test_average_attempt_duration_multiple(self):
        p = _profile(durations=[0.1, 0.3])
        assert p.average_attempt_duration == pytest.approx(0.2)

    def test_average_attempt_duration_empty(self):
        p = CallProfile(total_attempts=0, succeeded=False, total_elapsed=0.0)
        assert p.average_attempt_duration is None

    def test_fields_stored(self):
        p = _profile(attempts=3, succeeded=False, elapsed=0.5)
        assert p.total_attempts == 3
        assert p.succeeded is False
        assert p.total_elapsed == pytest.approx(0.5)


class TestRetryProfilerInitial:
    def test_zero_state(self):
        rp = RetryProfiler()
        assert rp.total_calls == 0
        assert rp.profiles == []
        assert rp.success_rate is None
        assert rp.average_elapsed() is None


class TestRetryProfilerRecord:
    def test_record_increases_count(self):
        rp = RetryProfiler()
        rp.record(_profile())
        assert rp.total_calls == 1

    def test_success_rate_all_success(self):
        rp = RetryProfiler()
        rp.record(_profile(succeeded=True))
        rp.record(_profile(succeeded=True))
        assert rp.success_rate == pytest.approx(1.0)

    def test_success_rate_mixed(self):
        rp = RetryProfiler()
        rp.record(_profile(succeeded=True))
        rp.record(_profile(succeeded=False))
        assert rp.success_rate == pytest.approx(0.5)

    def test_average_elapsed(self):
        rp = RetryProfiler()
        rp.record(_profile(elapsed=0.2))
        rp.record(_profile(elapsed=0.4))
        assert rp.average_elapsed() == pytest.approx(0.3)

    def test_profiles_returns_copy(self):
        rp = RetryProfiler()
        rp.record(_profile())
        copy = rp.profiles
        copy.clear()
        assert rp.total_calls == 1

    def test_reset_clears_state(self):
        rp = RetryProfiler()
        rp.record(_profile())
        rp.reset()
        assert rp.total_calls == 0
        assert rp.success_rate is None

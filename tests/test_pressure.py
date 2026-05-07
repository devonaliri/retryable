"""Tests for retryable.pressure."""
import pytest
from retryable.pressure import RetryPressure, PressureSnapshot


class TestRetryPressureInit:
    def test_valid_construction(self):
        p = RetryPressure(max_retries=3)
        assert p.max_retries == 3

    def test_default_max_retries(self):
        p = RetryPressure()
        assert p.max_retries == 3

    def test_zero_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            RetryPressure(max_retries=0)

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError):
            RetryPressure(max_retries=-1)


class TestRetryPressureCounters:
    def test_initial_snapshot_all_zeros(self):
        p = RetryPressure()
        snap = p.snapshot()
        assert snap.total_retries == 0
        assert snap.active_calls == 0
        assert snap.pressure_ratio == 0.0

    def test_enter_call_increments_active(self):
        p = RetryPressure()
        p.enter_call()
        assert p.snapshot().active_calls == 1

    def test_exit_call_decrements_active(self):
        p = RetryPressure()
        p.enter_call()
        p.exit_call()
        assert p.snapshot().active_calls == 0

    def test_exit_call_never_goes_negative(self):
        p = RetryPressure()
        p.exit_call()  # extra exit — should not go below 0
        assert p.snapshot().active_calls == 0

    def test_record_retry_increments_total(self):
        p = RetryPressure()
        p.enter_call()
        p.record_retry()
        p.record_retry()
        assert p.snapshot().total_retries == 2

    def test_pressure_ratio_capped_at_one(self):
        p = RetryPressure(max_retries=1)
        p.enter_call()
        for _ in range(10):
            p.record_retry()
        assert p.snapshot().pressure_ratio <= 1.0

    def test_pressure_ratio_calculation(self):
        p = RetryPressure(max_retries=4)
        p.enter_call()   # 1 call
        p.record_retry() # 1 retry  => ratio = 1 / (1*4) = 0.25
        snap = p.snapshot()
        assert abs(snap.pressure_ratio - 0.25) < 1e-9

    def test_reset_clears_state(self):
        p = RetryPressure()
        p.enter_call()
        p.record_retry()
        p.reset()
        snap = p.snapshot()
        assert snap.total_retries == 0
        assert snap.active_calls == 0


class TestPressureSnapshot:
    def test_is_elevated_above_threshold(self):
        snap = PressureSnapshot(total_retries=5, active_calls=2, pressure_ratio=0.8)
        assert snap.is_elevated(threshold=0.5) is True

    def test_not_elevated_below_threshold(self):
        snap = PressureSnapshot(total_retries=1, active_calls=1, pressure_ratio=0.2)
        assert snap.is_elevated(threshold=0.5) is False

    def test_timestamp_is_set(self):
        snap = PressureSnapshot(total_retries=0, active_calls=0, pressure_ratio=0.0)
        assert snap.sampled_at > 0

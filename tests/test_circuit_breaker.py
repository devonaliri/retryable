"""Tests for retryable.circuit_breaker."""

from __future__ import annotations

import time
import pytest

from retryable.circuit_breaker import CircuitBreaker, CircuitState


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestCircuitBreakerInit:
    def test_defaults(self):
        cb = CircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30.0
        assert cb.state is CircuitState.CLOSED

    def test_custom_values(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=10.0)
        assert cb.failure_threshold == 3
        assert cb.recovery_timeout == 10.0

    def test_zero_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreaker(failure_threshold=0)

    def test_negative_failure_threshold_raises(self):
        with pytest.raises(ValueError, match="failure_threshold"):
            CircuitBreaker(failure_threshold=-1)

    def test_zero_recovery_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreaker(recovery_timeout=0)

    def test_negative_recovery_timeout_raises(self):
        with pytest.raises(ValueError, match="recovery_timeout"):
            CircuitBreaker(recovery_timeout=-5.0)


# ---------------------------------------------------------------------------
# Failure recording and state transitions
# ---------------------------------------------------------------------------

class TestCircuitBreakerBehavior:
    def test_starts_closed_and_allows_requests(self):
        cb = CircuitBreaker(failure_threshold=3)
        assert cb.allow_request() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state is CircuitState.OPEN
        assert cb.allow_request() is False

    def test_does_not_open_before_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.consecutive_failures == 0
        assert cb.state is CircuitState.CLOSED

    def test_success_closes_open_circuit(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        cb.record_success()
        assert cb.state is CircuitState.CLOSED

    def test_transitions_to_half_open_after_timeout(self, monkeypatch):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
        cb.record_failure()
        assert cb.state is CircuitState.OPEN

        # Simulate time passing beyond recovery_timeout.
        monkeypatch.setattr(
            "retryable.circuit_breaker.time.monotonic",
            lambda: cb._opened_at + 2.0,  # type: ignore[operator]
        )
        assert cb.state is CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_reset_restores_closed_state(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        cb.reset()
        assert cb.state is CircuitState.CLOSED
        assert cb.consecutive_failures == 0
        assert cb.allow_request() is True

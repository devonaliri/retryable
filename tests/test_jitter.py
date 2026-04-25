"""Tests for retryable.jitter strategies."""

import pytest
from unittest.mock import patch

from retryable.jitter import none, full, equal, bounded


class TestNoneJitter:
    def test_returns_delay_unchanged(self):
        strategy = none()
        assert strategy(1.0) == 1.0
        assert strategy(5.5) == 5.5
        assert strategy(0.0) == 0.0

    def test_name(self):
        assert none().__name__ == "none"


class TestFullJitter:
    def test_result_within_range(self):
        strategy = full()
        for _ in range(50):
            result = strategy(10.0)
            assert 0.0 <= result <= 10.0

    def test_zero_delay_returns_zero(self):
        strategy = full()
        assert strategy(0.0) == 0.0

    def test_name(self):
        assert full().__name__ == "full"

    def test_uses_uniform(self):
        strategy = full()
        with patch("retryable.jitter.random.uniform", return_value=3.0) as mock_uniform:
            result = strategy(10.0)
            mock_uniform.assert_called_once_with(0.0, 10.0)
            assert result == 3.0


class TestEqualJitter:
    def test_result_within_range(self):
        strategy = equal()
        for _ in range(50):
            result = strategy(10.0)
            assert 5.0 <= result <= 10.0

    def test_zero_delay_returns_zero(self):
        strategy = equal()
        assert strategy(0.0) == 0.0

    def test_name(self):
        assert equal().__name__ == "equal"

    def test_uses_half_delay(self):
        strategy = equal()
        with patch("retryable.jitter.random.uniform", return_value=2.5) as mock_uniform:
            result = strategy(10.0)
            mock_uniform.assert_called_once_with(0.0, 5.0)
            assert result == 7.5


class TestBoundedJitter:
    def test_result_within_factor_range(self):
        strategy = bounded(0.8, 1.2)
        for _ in range(50):
            result = strategy(10.0)
            assert 8.0 <= result <= 12.0

    def test_default_factors(self):
        strategy = bounded()
        for _ in range(50):
            result = strategy(10.0)
            assert 5.0 <= result <= 15.0

    def test_name(self):
        assert bounded().__name__ == "bounded"

    def test_invalid_min_factor_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            bounded(min_factor=-0.1)

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="<= max_factor"):
            bounded(min_factor=2.0, max_factor=1.0)

    def test_equal_factors_gives_deterministic_result(self):
        strategy = bounded(min_factor=1.0, max_factor=1.0)
        assert strategy(5.0) == pytest.approx(5.0)

"""Integration test: LoggingObserver wired into a retry decorator."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from retryable.decorator import retry
from retryable.observer import LoggingObserver


class TestObserverWithDecorator:
    def test_observer_logs_retries(self):
        logger = MagicMock(spec=logging.Logger)
        obs = LoggingObserver(logger=logger, failure_level=logging.WARNING)

        calls = {"n": 0}

        @retry(max_attempts=3, exceptions=(ValueError,), observer=obs)
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("not yet")
            return "ok"

        result = flaky()
        assert result == "ok"
        # at least one warning logged for the failed attempts
        warning_calls = [
            c for c in logger.log.call_args_list if c[0][0] == logging.WARNING
        ]
        assert len(warning_calls) >= 2

    def test_no_logs_on_immediate_success(self):
        logger = MagicMock(spec=logging.Logger)
        obs = LoggingObserver(logger=logger)

        @retry(max_attempts=3, observer=obs)
        def ok():
            return 42

        assert ok() == 42
        warning_calls = [
            c for c in logger.log.call_args_list if c[0][0] == logging.WARNING
        ]
        assert len(warning_calls) == 0

"""Integration tests: ReplayLog wired into the retry decorator via HookSet."""

from __future__ import annotations

import pytest

from retryable.decorator import retry
from retryable.hooks import HookSet
from retryable.replay import ReplayLog


class TestReplayIntegration:
    def _make_log_and_hooks(self, fn_name: str):
        log = ReplayLog()
        before, after = log.make_hooks(fn_name)
        hooks = HookSet(before_attempt=[before], after_attempt=[after])
        return log, hooks

    def test_single_success_creates_one_entry(self):
        log, hooks = self._make_log_and_hooks("ok_fn")

        @retry(max_attempts=3, hooks=hooks)
        def ok_fn():
            return 42

        result = ok_fn()
        assert result == 42
        assert len(log.entries()) == 1
        assert log.latest().succeeded is True
        assert log.latest().total_attempts == 1

    def test_retried_success_records_all_attempts(self):
        log, hooks = self._make_log_and_hooks("flaky_fn")
        call_count = 0

        @retry(max_attempts=4, hooks=hooks)
        def flaky_fn():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "done"

        flaky_fn()
        assert log.latest().total_attempts == 3
        assert log.latest().succeeded is True

    def test_exhausted_retries_records_failed_replay(self):
        log, hooks = self._make_log_and_hooks("always_fails")

        @retry(max_attempts=3, hooks=hooks)
        def always_fails():
            raise RuntimeError("boom")

        with pytest.raises(Exception):
            always_fails()

        assert len(log.entries()) == 1
        assert log.latest().succeeded is False
        assert log.latest().total_attempts == 3

    def test_multiple_calls_create_multiple_entries(self):
        log, hooks = self._make_log_and_hooks("multi")

        @retry(max_attempts=2, hooks=hooks)
        def multi():
            return True

        multi()
        multi()
        multi()
        assert len(log.entries()) == 3

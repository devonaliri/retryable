"""Integration tests: telemetry hooks wired through RetryPolicy."""
import pytest

from retryable.policy import RetryPolicy
from retryable.telemetry import TelemetryCollector
from retryable.telemetry_integration import default_telemetry, make_telemetry_hookset
from retryable.telemetry_export import summary, to_json, to_csv


class TestTelemetryWithPolicy:
    def _policy(self, collector: TelemetryCollector, max_attempts: int = 3) -> RetryPolicy:
        hookset = make_telemetry_hookset(collector)
        return RetryPolicy(max_attempts=max_attempts, hooks=hookset)

    def test_success_emits_before_and_success_events(self):
        collector = TelemetryCollector()
        policy = self._policy(collector)

        @policy
        def ok():
            return 42

        result = ok()
        assert result == 42
        types = [e.event_type for e in collector.events]
        assert "before_attempt" in types
        assert "success" in types

    def test_retried_failure_emits_after_attempt_events(self):
        collector = TelemetryCollector()
        policy = self._policy(collector, max_attempts=3)
        calls = {"n": 0}

        @policy
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("boom")
            return "ok"

        flaky()
        after = [e for e in collector.events if e.event_type == "after_attempt"]
        assert len(after) == 2
        assert all(e.exception_type == "ValueError" for e in after)

    def test_default_telemetry_returns_collector_and_hookset(self):
        collector, hookset = default_telemetry()
        assert isinstance(collector, TelemetryCollector)
        assert hookset is not None


class TestTelemetryExport:
    def test_to_json_is_valid_json(self):
        import json
        collector, hookset = default_telemetry()
        policy = RetryPolicy(max_attempts=2, hooks=hookset)

        @policy
        def ok():
            return 1

        ok()
        result = to_json(collector.events)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

    def test_to_csv_contains_header(self):
        collector, hookset = default_telemetry()
        policy = RetryPolicy(max_attempts=2, hooks=hookset)

        @policy
        def ok():
            return 1

        ok()
        csv_output = to_csv(collector.events)
        assert "event_type" in csv_output

    def test_summary_counts_successes(self):
        collector, hookset = default_telemetry()
        policy = RetryPolicy(max_attempts=2, hooks=hookset)

        @policy
        def ok():
            return 1

        ok()
        s = summary(collector.events)
        assert s["successes"] >= 1
        assert "total_events" in s

"""Integration tests for trace hooks wired through RetryPolicy."""
import pytest
from retryable.policy import RetryPolicy
from retryable.trace import RetryTrace
from retryable.trace_integration import make_trace_hookset, _TRACE_KEY


class TestTraceIntegration:
    def _policy(self, collected: list, max_attempts: int = 3) -> RetryPolicy:
        hookset = make_trace_hookset(on_trace_complete=collected.append)
        return RetryPolicy(
            max_attempts=max_attempts,
            hookset=hookset,
        )

    def test_success_on_first_attempt_produces_one_span(self):
        collected: list = []
        policy = self._policy(collected)

        @policy
        def ok():
            return 42

        result = ok()
        assert result == 42
        assert len(collected) == 1
        trace: RetryTrace = collected[0]
        assert trace.total_spans == 1
        assert trace.succeeded is True

    def test_retried_success_records_all_spans(self):
        collected: list = []
        policy = self._policy(collected, max_attempts=3)
        call_count = 0

        @policy
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "ok"

        flaky()
        assert len(collected) == 1
        trace: RetryTrace = collected[0]
        assert trace.total_spans == 3
        assert trace.succeeded is True
        assert trace.spans[0].exception_type == "ValueError"
        assert trace.spans[-1].succeeded is True

    def test_all_failures_records_spans_and_not_succeeded(self):
        collected: list = []
        policy = self._policy(collected, max_attempts=2)

        @policy
        def always_fails():
            raise RuntimeError("boom")

        with pytest.raises(Exception):
            always_fails()

        assert len(collected) == 1
        trace: RetryTrace = collected[0]
        assert trace.total_spans == 2
        assert trace.succeeded is False
        for span in trace.spans:
            assert span.exception_type == "RuntimeError"

    def test_trace_ids_differ_across_calls(self):
        collected: list = []
        policy = self._policy(collected)

        @policy
        def ok():
            return 1

        ok()
        ok()
        assert len(collected) == 2
        assert collected[0].trace_id != collected[1].trace_id

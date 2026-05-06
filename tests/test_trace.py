"""Unit tests for retryable.trace."""
import pytest
from retryable.trace import RetrySpan, RetryTrace


class TestRetrySpan:
    def test_as_dict_contains_all_keys(self):
        span = RetrySpan(
            trace_id="abc",
            span_id="def",
            attempt_number=1,
            succeeded=True,
        )
        d = span.as_dict()
        assert d["trace_id"] == "abc"
        assert d["span_id"] == "def"
        assert d["attempt_number"] == 1
        assert d["succeeded"] is True
        assert d["exception_type"] is None

    def test_exception_type_stored(self):
        span = RetrySpan(
            trace_id="t", span_id="s", attempt_number=2,
            succeeded=False, exception_type="ValueError",
        )
        assert span.as_dict()["exception_type"] == "ValueError"


class TestRetryTrace:
    def test_trace_id_unique(self):
        t1 = RetryTrace()
        t2 = RetryTrace()
        assert t1.trace_id != t2.trace_id

    def test_add_span_increments_total(self):
        t = RetryTrace()
        t.add_span(1, False, "IOError")
        t.add_span(2, True)
        assert t.total_spans == 2

    def test_succeeded_true_when_last_span_ok(self):
        t = RetryTrace()
        t.add_span(1, False)
        t.add_span(2, True)
        assert t.succeeded is True

    def test_succeeded_false_when_last_span_failed(self):
        t = RetryTrace()
        t.add_span(1, False)
        assert t.succeeded is False

    def test_succeeded_false_when_empty(self):
        assert RetryTrace().succeeded is False

    def test_span_ids_unique(self):
        t = RetryTrace()
        s1 = t.add_span(1, False)
        s2 = t.add_span(2, True)
        assert s1.span_id != s2.span_id

    def test_as_dict_structure(self):
        t = RetryTrace()
        t.add_span(1, True)
        d = t.as_dict()
        assert "trace_id" in d
        assert d["total_spans"] == 1
        assert len(d["spans"]) == 1
        assert d["succeeded"] is True

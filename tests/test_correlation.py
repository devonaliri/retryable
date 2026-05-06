"""Tests for retryable.correlation."""
from __future__ import annotations

import pytest

from retryable.correlation import CorrelationEntry, CorrelationTracker


class TestCorrelationEntry:
    def test_initial_attempt_ids_empty(self):
        e = CorrelationEntry(correlation_id="abc")
        assert e.attempt_ids == []
        assert e.total_attempts == 0

    def test_add_attempt_returns_unique_ids(self):
        e = CorrelationEntry(correlation_id="abc")
        id1 = e.add_attempt()
        id2 = e.add_attempt()
        assert id1 != id2
        assert e.total_attempts == 2

    def test_attempt_ids_stored_in_order(self):
        e = CorrelationEntry(correlation_id="abc")
        ids = [e.add_attempt() for _ in range(3)]
        assert e.attempt_ids == ids


class TestCorrelationTrackerInit:
    def test_default_construction(self):
        t = CorrelationTracker()
        assert t.total_calls() == 0

    def test_non_callable_id_factory_raises(self):
        with pytest.raises(TypeError):
            CorrelationTracker(id_factory="not-callable")  # type: ignore[arg-type]


class TestCorrelationTrackerNewCall:
    def test_new_call_returns_entry(self):
        t = CorrelationTracker()
        entry = t.new_call()
        assert isinstance(entry, CorrelationEntry)
        assert entry.total_attempts == 0

    def test_each_call_has_unique_id(self):
        t = CorrelationTracker()
        e1 = t.new_call()
        e2 = t.new_call()
        assert e1.correlation_id != e2.correlation_id

    def test_get_returns_registered_entry(self):
        t = CorrelationTracker()
        entry = t.new_call()
        assert t.get(entry.correlation_id) is entry

    def test_get_unknown_id_returns_none(self):
        t = CorrelationTracker()
        assert t.get("nonexistent") is None

    def test_all_entries_grows_with_calls(self):
        t = CorrelationTracker()
        t.new_call()
        t.new_call()
        assert len(t.all_entries()) == 2
        assert t.total_calls() == 2

    def test_custom_id_factory_used(self):
        counter = iter(range(100))
        factory = lambda: f"id-{next(counter)}"
        t = CorrelationTracker(id_factory=factory)
        e = t.new_call()
        assert e.correlation_id == "id-0"

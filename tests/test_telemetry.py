"""Unit tests for TelemetryEvent and TelemetryCollector."""
import time

import pytest

from retryable.telemetry import TelemetryCollector, TelemetryEvent


def _event(event_type="after_attempt", attempt=1, **kw) -> TelemetryEvent:
    return TelemetryEvent(event_type=event_type, attempt_number=attempt, **kw)


class TestTelemetryEvent:
    def test_as_dict_contains_all_keys(self):
        e = _event()
        d = e.as_dict()
        assert set(d.keys()) == {
            "event_type", "attempt_number", "timestamp",
            "elapsed", "exception_type", "delay", "metadata",
        }

    def test_timestamp_is_recent(self):
        before = time.time()
        e = _event()
        assert e.timestamp >= before

    def test_metadata_defaults_to_empty(self):
        e = _event()
        assert e.metadata == {}

    def test_custom_metadata_stored(self):
        e = _event(metadata={"key": "val"})
        assert e.metadata["key"] == "val"


class TestTelemetryCollector:
    def test_starts_empty(self):
        c = TelemetryCollector()
        assert len(c) == 0
        assert c.events == []

    def test_emit_stores_event(self):
        c = TelemetryCollector()
        c.emit(_event())
        assert len(c) == 1

    def test_events_returns_copy(self):
        c = TelemetryCollector()
        c.emit(_event())
        evts = c.events
        evts.clear()
        assert len(c) == 1

    def test_sink_receives_event(self):
        received = []
        c = TelemetryCollector()
        c.add_sink(received.append)
        e = _event()
        c.emit(e)
        assert received == [e]

    def test_multiple_sinks(self):
        a, b = [], []
        c = TelemetryCollector()
        c.add_sink(a.append)
        c.add_sink(b.append)
        c.emit(_event())
        assert len(a) == 1
        assert len(b) == 1

    def test_non_callable_sink_raises(self):
        c = TelemetryCollector()
        with pytest.raises(TypeError):
            c.add_sink("not_callable")  # type: ignore

    def test_clear_removes_events(self):
        c = TelemetryCollector()
        c.emit(_event())
        c.clear()
        assert len(c) == 0

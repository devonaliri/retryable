"""Wires TelemetryCollector into a HookSet for use with RetryPolicy."""
from __future__ import annotations

from retryable.context import AttemptRecord, RetryContext
from retryable.hooks import HookSet
from retryable.telemetry import TelemetryCollector, TelemetryEvent


def _before_hook(collector: TelemetryCollector):
    def hook(ctx: RetryContext) -> None:
        event = TelemetryEvent(
            event_type="before_attempt",
            attempt_number=ctx.total_attempts + 1,
        )
        collector.emit(event)

    return hook


def _after_hook(collector: TelemetryCollector):
    def hook(ctx: RetryContext, record: AttemptRecord) -> None:
        exc = record.exception
        event = TelemetryEvent(
            event_type="success" if record.succeeded else "after_attempt",
            attempt_number=ctx.total_attempts,
            elapsed=record.delay,
            exception_type=type(exc).__name__ if exc is not None else None,
            delay=record.delay,
        )
        collector.emit(event)

    return hook


def make_telemetry_hookset(collector: TelemetryCollector) -> HookSet:
    """Return a HookSet that emits telemetry events into *collector*."""
    hs = HookSet()
    hs.before.append(_before_hook(collector))
    hs.after.append(_after_hook(collector))
    return hs


# A ready-to-use collector + hookset pair for simple setups.
def default_telemetry() -> tuple[TelemetryCollector, HookSet]:
    """Create a TelemetryCollector and its matching HookSet."""
    collector = TelemetryCollector()
    hookset = make_telemetry_hookset(collector)
    return collector, hookset

"""Hooks that wire RetryPressure into a HookSet."""
from __future__ import annotations

from retryable.context import RetryContext, AttemptRecord
from retryable.hooks import HookSet
from retryable.pressure import RetryPressure


def make_pressure_hookset(
    pressure: RetryPressure,
    *,
    metadata_key: str = "pressure",
) -> HookSet:
    """Return a HookSet that records pressure events and annotates metadata.

    * ``before_attempt`` on attempt 1 calls :meth:`~RetryPressure.enter_call`.
    * ``before_attempt`` on attempt > 1 calls :meth:`~RetryPressure.record_retry`.
    * ``after_attempt`` on the final attempt (no next delay) calls
      :meth:`~RetryPressure.exit_call` and writes the current snapshot into
      ``ctx.metadata[metadata_key]``.
    """
    hookset = HookSet()

    def before(ctx: RetryContext) -> None:
        attempt_number = ctx.total_attempts + 1  # not yet recorded
        if attempt_number == 1:
            pressure.enter_call()
        else:
            pressure.record_retry()

    def after(ctx: RetryContext, record: AttemptRecord) -> None:
        snap = pressure.snapshot()
        ctx.metadata[metadata_key] = snap
        # If this attempt succeeded or no further retries will happen we close.
        if record.succeeded or record.delay is None:
            pressure.exit_call()

    hookset.fire_before_attempt  # satisfy linters — we add directly
    hookset._before_hooks.append(before)  # type: ignore[attr-defined]
    hookset._after_hooks.append(after)   # type: ignore[attr-defined]
    return hookset

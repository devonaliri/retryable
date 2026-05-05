"""Hooks that integrate RetryProfiler with the retry decorator."""

from __future__ import annotations

import time
from typing import Any, Dict

from retryable.context import AttemptRecord, RetryContext
from retryable.profiler import CallProfile, RetryProfiler

# Per-call mutable state keyed by context id.
_STATE_KEY = "_profiler_state"


def _get_state(ctx: RetryContext) -> Dict[str, Any]:
    if not hasattr(ctx, _STATE_KEY):
        object.__setattr__(ctx, _STATE_KEY, {"start": time.monotonic(), "durations": [], "attempt_start": None})
    return getattr(ctx, _STATE_KEY)  # type: ignore[return-value]


def make_before_hook(profiler: RetryProfiler):  # noqa: ANN201
    """Return a before-attempt hook that timestamps each attempt start."""

    def hook(ctx: RetryContext) -> None:
        state = _get_state(ctx)
        state["attempt_start"] = time.monotonic()

    return hook


def make_after_hook(profiler: RetryProfiler):  # noqa: ANN201
    """Return an after-attempt hook that finalises profiling on last attempt."""

    def hook(ctx: RetryContext, record: AttemptRecord) -> None:
        state = _get_state(ctx)
        if state["attempt_start"] is not None:
            state["durations"].append(time.monotonic() - state["attempt_start"])

        # Emit a profile when the call is finished (success or final failure).
        finished = record.exception is None or ctx.total_attempts >= getattr(ctx, "max_attempts", float("inf"))
        if record.exception is None or finished:
            elapsed = time.monotonic() - state["start"]
            profile = CallProfile(
                total_attempts=ctx.total_attempts,
                succeeded=record.exception is None,
                total_elapsed=elapsed,
                attempt_durations=list(state["durations"]),
            )
            profiler.record(profile)

    return hook


def attach_profiler(hookset, profiler: RetryProfiler) -> None:  # noqa: ANN001
    """Convenience: register both hooks on an existing HookSet."""
    hookset.before_attempt.append(make_before_hook(profiler))
    hookset.after_attempt.append(make_after_hook(profiler))

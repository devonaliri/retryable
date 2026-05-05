"""Simple text/dict report generation from a RetryProfiler."""

from __future__ import annotations

from typing import Any, Dict, Optional

from retryable.profiler import RetryProfiler


def as_dict(profiler: RetryProfiler) -> Dict[str, Any]:
    """Serialise profiler state to a plain dictionary."""
    avg_elapsed = profiler.average_elapsed()
    return {
        "total_calls": profiler.total_calls,
        "success_rate": profiler.success_rate,
        "average_elapsed_seconds": avg_elapsed,
        "profiles": [
            {
                "total_attempts": p.total_attempts,
                "succeeded": p.succeeded,
                "total_elapsed": p.total_elapsed,
                "average_attempt_duration": p.average_attempt_duration,
            }
            for p in profiler.profiles
        ],
    }


def summary(profiler: RetryProfiler) -> str:
    """Return a human-readable summary string."""
    if profiler.total_calls == 0:
        return "RetryProfiler: no calls recorded."

    rate = profiler.success_rate
    rate_str = f"{rate * 100:.1f}%" if rate is not None else "n/a"
    avg = profiler.average_elapsed()
    avg_str = f"{avg:.4f}s" if avg is not None else "n/a"

    lines = [
        f"RetryProfiler summary ({profiler.total_calls} call(s)):",
        f"  Success rate : {rate_str}",
        f"  Avg elapsed  : {avg_str}",
    ]
    return "\n".join(lines)

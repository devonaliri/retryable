"""Reporting utilities for hedged-call statistics.

Consumes a :class:`~retryable.context.RetryContext` sequence (or any iterable
of contexts) and summarises hedge behaviour.
"""
from __future__ import annotations

from typing import Iterable, Dict, Any

from retryable.context import RetryContext


def _hedge_fired(ctx: RetryContext) -> bool:
    """Return True when the hedge attempt was launched for *ctx*."""
    hedge = ctx.metadata.get("hedge")
    return isinstance(hedge, dict) and ctx.total_attempts > 1


def _timed_out(ctx: RetryContext) -> bool:
    return bool(ctx.metadata.get("hedge_timeout"))


def hedge_summary(contexts: Iterable[RetryContext]) -> Dict[str, Any]:
    """Aggregate hedge statistics across multiple call contexts.

    Returns
    -------
    dict with keys:
        total_calls       – number of contexts examined
        hedge_fired       – calls where a speculative twin was launched
        hedge_timeout     – calls that exceeded the deadline entirely
        hedge_rate        – fraction of calls that fired a hedge (0-1 or None)
        timeout_rate      – fraction of calls that timed out (0-1 or None)
    """
    total = 0
    fired = 0
    timed_out = 0

    for ctx in contexts:
        total += 1
        if _hedge_fired(ctx):
            fired += 1
        if _timed_out(ctx):
            timed_out += 1

    return {
        "total_calls": total,
        "hedge_fired": fired,
        "hedge_timeout": timed_out,
        "hedge_rate": fired / total if total else None,
        "timeout_rate": timed_out / total if total else None,
    }


def format_hedge_summary(contexts: Iterable[RetryContext]) -> str:
    """Return a human-readable summary string."""
    s = hedge_summary(contexts)
    rate = f"{s['hedge_rate']:.1%}" if s["hedge_rate"] is not None else "n/a"
    timeout = f"{s['timeout_rate']:.1%}" if s["timeout_rate"] is not None else "n/a"
    return (
        f"HedgeSummary(total={s['total_calls']}, "
        f"fired={s['hedge_fired']} [{rate}], "
        f"timeouts={s['hedge_timeout']} [{timeout}])"
    )

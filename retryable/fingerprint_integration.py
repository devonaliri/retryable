"""Hooks that attach fingerprint data to retry contexts via a FingerprintRegistry."""
from __future__ import annotations

from typing import Callable, Optional

from retryable.context import AttemptRecord, RetryContext
from retryable.fingerprint import FingerprintRegistry, default_fingerprint
from retryable.hooks import HookSet

_METADATA_KEY = "fingerprint"


def _make_before_hook(registry: FingerprintRegistry) -> Callable[[RetryContext], None]:
    def hook(ctx: RetryContext) -> None:
        fp = registry.record(ctx)
        ctx.metadata[_METADATA_KEY] = fp

    return hook


def _make_after_hook(registry: FingerprintRegistry) -> Callable[[RetryContext, AttemptRecord], None]:
    def hook(ctx: RetryContext, record: AttemptRecord) -> None:
        # Ensure fingerprint is present even if before hook was skipped.
        if _METADATA_KEY not in ctx.metadata:
            ctx.metadata[_METADATA_KEY] = registry.record(ctx)

    return hook


def make_fingerprint_hookset(
    registry: Optional[FingerprintRegistry] = None,
    strategy: Optional[Callable] = None,
) -> tuple[HookSet, FingerprintRegistry]:
    """Return a (HookSet, FingerprintRegistry) pair wired together.

    Parameters
    ----------
    registry:
        Existing registry to reuse; a new one is created when *None*.
    strategy:
        Custom fingerprint callable ``(RetryContext) -> str``.
        Ignored when *registry* is supplied.
    """
    if registry is None:
        registry = FingerprintRegistry(strategy=strategy or default_fingerprint)
    hookset = HookSet()
    hookset.before_attempt.append(_make_before_hook(registry))
    hookset.after_attempt.append(_make_after_hook(registry))
    return hookset, registry

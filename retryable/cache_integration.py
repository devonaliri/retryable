"""Hooks that integrate RetryCache with the retry decorator pipeline."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple

from retryable.cache import RetryCache
from retryable.context import AttemptRecord, RetryContext


def _make_before_hook(cache: RetryCache, args: Tuple, kwargs: Dict):
    """Return a before-attempt hook that short-circuits if a cached value exists.

    Because hooks cannot directly return a value to the caller the cache check
    is best done at the call-site (see :func:`cached_call`).  This hook is
    provided for observability — it records whether the upcoming attempt was
    skipped due to a cache hit via ``ctx.metadata``.
    """
    def hook(ctx: RetryContext) -> None:
        hit, _ = cache.get(args, kwargs)
        ctx.metadata["cache_hit"] = hit  # type: ignore[attr-defined]
    return hook


def _make_after_hook(cache: RetryCache, args: Tuple, kwargs: Dict):
    """Return an after-attempt hook that stores a successful result in *cache*."""
    def hook(ctx: RetryContext, record: AttemptRecord) -> None:
        if record.succeeded:
            cache.put(args, kwargs, record.result)  # type: ignore[attr-defined]
    return hook


def cached_call(
    fn: Callable,
    cache: RetryCache,
    args: Tuple,
    kwargs: Dict,
    *,
    retry_fn: Optional[Callable] = None,
) -> Any:
    """Call *fn* with cache-aside logic.

    If a live entry exists in *cache* for (*args*, *kwargs*) it is returned
    immediately without invoking *fn* or the retry machinery.  On a miss the
    call is forwarded to *retry_fn* (or *fn* directly when not provided) and
    the result is stored on success.

    Parameters
    ----------
    fn:
        The original unwrapped callable (used as cache key context).
    cache:
        A :class:`~retryable.cache.RetryCache` instance.
    args / kwargs:
        Positional and keyword arguments for the call.
    retry_fn:
        Optional already-wrapped retry callable.  When supplied it is invoked
        instead of *fn* on a cache miss.
    """
    hit, value = cache.get(args, kwargs)
    if hit:
        return value
    target = retry_fn if retry_fn is not None else fn
    result = target(*args, **kwargs)
    cache.put(args, kwargs, result)
    return result

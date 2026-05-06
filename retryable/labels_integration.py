"""High-level helper that wires label stamping into a RetryPolicy's HookSet."""
from __future__ import annotations

from typing import Any, Dict

from retryable.hooks import HookSet
from retryable.labels import make_label_hookset


def attach_labels(hookset: HookSet, labels: Dict[str, Any]) -> HookSet:
    """Register label-stamping hooks on *hookset* and return it.

    Both the *before_attempt* and *after_attempt* phases are covered so that
    the label data is available to any hook that runs after this one.

    Parameters
    ----------
    hookset:
        The :class:`~retryable.hooks.HookSet` belonging to the policy you
        want to label.
    labels:
        Arbitrary key/value pairs to attach, e.g.
        ``{"service": "payments", "env": "prod"}``.

    Returns
    -------
    HookSet
        The same *hookset* instance (mutated in-place) for easy chaining.
    """
    before, after = make_label_hookset(labels)
    hookset.before_attempt.append(before)
    hookset.after_attempt.append(after)
    return hookset

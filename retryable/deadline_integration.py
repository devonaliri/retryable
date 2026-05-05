"""Integration helpers that wire a :class:`~retryable.deadline.Deadline`
into a :class:`~retryable.policy.RetryPolicy` via its hook system.

Usage example::

    from retryable.policy import RetryPolicy
    from retryable.deadline import Deadline
    from retryable.deadline_integration import attach_deadline

    policy = RetryPolicy(max_attempts=10)
    attach_deadline(policy, Deadline(30.0))

    @policy
    def fetch():
        ...
"""

from __future__ import annotations

from typing import Any

from retryable.deadline import Deadline, DeadlineExceeded
from retryable.policy import RetryPolicy


def _make_before_hook(deadline: Deadline):
    """Return a *before-attempt* hook that starts and checks the deadline."""

    def hook(ctx: Any) -> None:  # ctx is RetryContext
        deadline.start()
        deadline.check()

    hook.__name__ = "deadline_before_hook"
    return hook


def _make_after_hook(deadline: Deadline):
    """Return an *after-attempt* hook that clamps the next sleep delay."""

    def hook(ctx: Any, record: Any) -> None:  # ctx, AttemptRecord
        # If the deadline is already expired, raise immediately so the
        # decorator does not proceed to sleep.
        if deadline.is_expired:
            raise DeadlineExceeded(deadline)

    hook.__name__ = "deadline_after_hook"
    return hook


def attach_deadline(policy: RetryPolicy, deadline: Deadline) -> RetryPolicy:
    """Register deadline enforcement hooks on *policy* and return it.

    The before-attempt hook starts the deadline (idempotent) and raises
    :class:`~retryable.deadline.DeadlineExceeded` if the budget is
    exhausted before the attempt begins.

    The after-attempt hook raises :class:`~retryable.deadline.DeadlineExceeded`
    if the budget expired during the last attempt, preventing further sleeps.

    Args:
        policy: The :class:`~retryable.policy.RetryPolicy` to augment.
        deadline: A :class:`~retryable.deadline.Deadline` instance.

    Returns:
        The same *policy* object (for chaining).
    """
    policy.hooks.fire_before_attempt  # noqa: B018 – ensure attribute exists
    policy.hooks._before.append(_make_before_hook(deadline))
    policy.hooks._after.append(_make_after_hook(deadline))
    return policy


def deadline_policy(
    total_seconds: float,
    **policy_kwargs: Any,
) -> RetryPolicy:
    """Convenience factory: create a :class:`~retryable.policy.RetryPolicy`
    with a :class:`~retryable.deadline.Deadline` already attached.

    Args:
        total_seconds: Maximum wall-clock budget for all retry attempts.
        **policy_kwargs: Forwarded verbatim to :class:`~retryable.policy.RetryPolicy`.

    Returns:
        A configured :class:`~retryable.policy.RetryPolicy`.
    """
    policy = RetryPolicy(**policy_kwargs)
    attach_deadline(policy, Deadline(total_seconds))
    return policy

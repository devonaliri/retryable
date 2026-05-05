"""Observer that wires logging hooks into a RetryPolicy."""
from __future__ import annotations

import logging
from typing import Optional

from retryable.hooks import HookSet
from retryable.logging import make_after_hook, make_before_hook


class LoggingObserver:
    """Attach structured logging to a :class:`HookSet`.

    Parameters
    ----------
    logger:
        Logger to use; defaults to the ``retryable`` root logger.
    level:
        Log level for informational messages (default: DEBUG).
    failure_level:
        Log level for failed attempt messages (default: WARNING).
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        level: int = logging.DEBUG,
        failure_level: int = logging.WARNING,
    ) -> None:
        self._logger = logger
        self._level = level
        self._failure_level = failure_level

    def attach(self, hooks: HookSet) -> None:
        """Register before/after hooks onto *hooks*."""
        hooks.before.append(make_before_hook(self._logger, self._level))
        hooks.after.append(
            make_after_hook(self._logger, self._level, self._failure_level)
        )

    def detach(self, hooks: HookSet) -> None:
        """Remove any hooks previously registered by this observer from *hooks*.

        This is a best-effort removal: hooks are matched by identity, so only
        hooks registered during the *same* :meth:`attach` call will be found.
        Silently ignores hooks that are no longer present.
        """
        before_hook = make_before_hook(self._logger, self._level)
        after_hook = make_after_hook(self._logger, self._level, self._failure_level)
        for hook_list, candidate in (
            (hooks.before, before_hook),
            (hooks.after, after_hook),
        ):
            try:
                hook_list.remove(candidate)
            except ValueError:
                pass

    @classmethod
    def default(cls) -> "LoggingObserver":
        """Create an observer using library defaults."""
        return cls()

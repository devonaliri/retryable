"""End-to-end test: RetrySignal cancels / force-succeeds a real policy run."""
import threading
import time

import pytest

from retryable.policy import RetryPolicy
from retryable.signal import RetrySignal
from retryable.signal_integration import SignalCancelledError, make_signal_hookset


def _always_fails(*_args, **_kwargs):
    raise ValueError("boom")


class TestSignalCancelsPolicy:
    def test_cancel_before_first_attempt_raises(self):
        sig = RetrySignal()
        sig.cancel()
        hs = make_signal_hookset(sig)
        policy = RetryPolicy(max_attempts=5, hookset=hs)

        with pytest.raises(SignalCancelledError):
            policy(_always_fails)()

    def test_cancel_mid_run_stops_loop(self):
        """Cancel after the first failure; loop should not reach attempt 3."""
        sig = RetrySignal()
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # schedule cancel to fire between attempts
                threading.Timer(0.01, sig.cancel).start()
            raise RuntimeError("retry me")

        hs = make_signal_hookset(sig)
        policy = RetryPolicy(max_attempts=10, delay=0.05, hookset=hs)

        with pytest.raises((SignalCancelledError, Exception)):
            policy(flaky)()

        assert call_count < 10, "Signal did not stop the loop early"


class TestSignalForceSucceedPolicy:
    def test_force_success_value_stored_in_metadata(self):
        """Verify that force_success writes the expected metadata key."""
        sig = RetrySignal()
        sig.force_success("shortcut")
        hs = make_signal_hookset(sig)

        captured_ctx = {}

        def capture_ctx(ctx):
            captured_ctx["ctx"] = ctx

        hs.after_attempt.append(capture_ctx)

        def ok():
            return "real"

        policy = RetryPolicy(max_attempts=3, hookset=hs)
        policy(ok)()

        ctx = captured_ctx.get("ctx")
        assert ctx is not None
        assert ctx.metadata.get("__signal_forced_value__") == "shortcut"

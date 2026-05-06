"""Unit tests for retryable.checkpoint."""
import json
import time
from pathlib import Path

import pytest

from retryable.checkpoint import CheckpointData, RetryCheckpoint


# ---------------------------------------------------------------------------
# CheckpointData
# ---------------------------------------------------------------------------

class TestCheckpointData:
    def test_to_dict_round_trip(self):
        d = CheckpointData(key="op", attempts=3,
                           last_exception_type="ValueError",
                           last_exception_message="bad")
        restored = CheckpointData.from_dict(d.to_dict())
        assert restored.key == d.key
        assert restored.attempts == d.attempts
        assert restored.last_exception_type == d.last_exception_type

    def test_extra_defaults_to_empty_dict(self):
        d = CheckpointData(key="x", attempts=1,
                           last_exception_type=None,
                           last_exception_message=None)
        assert d.extra == {}

    def test_timestamps_are_floats(self):
        before = time.time()
        d = CheckpointData(key="t", attempts=0,
                           last_exception_type=None,
                           last_exception_message=None)
        assert d.created_at >= before
        assert d.updated_at >= before


# ---------------------------------------------------------------------------
# RetryCheckpoint
# ---------------------------------------------------------------------------

class TestRetryCheckpoint:
    def test_save_and_load(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        data = CheckpointData(key="job1", attempts=2,
                              last_exception_type="IOError",
                              last_exception_message="disk full")
        cp.save(data)
        loaded = cp.load("job1")
        assert loaded is not None
        assert loaded.attempts == 2
        assert loaded.last_exception_type == "IOError"

    def test_load_missing_returns_none(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        assert cp.load("nonexistent") is None

    def test_exists_after_save(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        data = CheckpointData(key="j", attempts=1,
                              last_exception_type=None,
                              last_exception_message=None)
        cp.save(data)
        assert cp.exists("j")

    def test_clear_removes_file(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        data = CheckpointData(key="j2", attempts=1,
                              last_exception_type=None,
                              last_exception_message=None)
        cp.save(data)
        cp.clear("j2")
        assert not cp.exists("j2")

    def test_clear_nonexistent_is_noop(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        cp.clear("ghost")  # should not raise

    def test_updated_at_changes_on_save(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        d = CheckpointData(key="ts", attempts=1,
                           last_exception_type=None,
                           last_exception_message=None)
        d.updated_at = 0.0
        cp.save(d)
        loaded = cp.load("ts")
        assert loaded.updated_at > 0.0

    def test_key_with_slashes_is_safe(self, tmp_path):
        cp = RetryCheckpoint(tmp_path)
        d = CheckpointData(key="a/b/c", attempts=1,
                           last_exception_type=None,
                           last_exception_message=None)
        cp.save(d)
        assert cp.exists("a/b/c")
        cp.clear("a/b/c")

"""Property-style tests ensuring CheckpointData survives JSON round-trips."""
import json
import pytest

from retryable.checkpoint import CheckpointData


CASES = [
    {"key": "simple", "attempts": 0, "last_exception_type": None,
     "last_exception_message": None},
    {"key": "with-exc", "attempts": 7, "last_exception_type": "TimeoutError",
     "last_exception_message": "timed out after 30 s"},
    {"key": "with-extra", "attempts": 1, "last_exception_type": "ValueError",
     "last_exception_message": "bad value",
     "extra": {"user_id": 42, "queue": "high"}},
]


@pytest.mark.parametrize("params", CASES)
def test_json_round_trip(params):
    original = CheckpointData(**params)
    serialised = json.dumps(original.to_dict())
    restored = CheckpointData.from_dict(json.loads(serialised))
    assert restored.key == original.key
    assert restored.attempts == original.attempts
    assert restored.last_exception_type == original.last_exception_type
    assert restored.last_exception_message == original.last_exception_message
    assert restored.extra == original.extra


def test_extra_field_preserved():
    d = CheckpointData(
        key="k", attempts=2,
        last_exception_type="OSError",
        last_exception_message="no such file",
        extra={"shard": 3},
    )
    restored = CheckpointData.from_dict(d.to_dict())
    assert restored.extra["shard"] == 3


def test_from_dict_requires_all_fields():
    with pytest.raises(TypeError):
        CheckpointData.from_dict({"key": "only-key"})

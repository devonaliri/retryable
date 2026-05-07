"""Tests for retryable.watermark."""
import pytest

from retryable.watermark import Watermark


class TestWatermarkInit:
    def test_all_zeros_initially(self):
        w = Watermark()
        assert w.peak_attempts == 0
        assert w.peak_delay == 0.0
        assert w.peak_total_delay == 0.0
        assert w.total_records == 0


class TestWatermarkRecord:
    def test_single_record_sets_peaks(self):
        w = Watermark()
        w.record(attempts=3, delay=1.5, total_delay=4.0)
        assert w.peak_attempts == 3
        assert w.peak_delay == 1.5
        assert w.peak_total_delay == 4.0
        assert w.total_records == 1

    def test_higher_values_update_peaks(self):
        w = Watermark()
        w.record(attempts=2, delay=1.0, total_delay=2.0)
        w.record(attempts=5, delay=3.0, total_delay=8.0)
        assert w.peak_attempts == 5
        assert w.peak_delay == 3.0
        assert w.peak_total_delay == 8.0

    def test_lower_values_do_not_lower_peaks(self):
        w = Watermark()
        w.record(attempts=5, delay=3.0, total_delay=8.0)
        w.record(attempts=1, delay=0.1, total_delay=0.1)
        assert w.peak_attempts == 5
        assert w.peak_delay == 3.0
        assert w.peak_total_delay == 8.0

    def test_total_records_increments(self):
        w = Watermark()
        for i in range(4):
            w.record(attempts=i, delay=float(i), total_delay=float(i))
        assert w.total_records == 4

    def test_negative_attempts_raises(self):
        w = Watermark()
        with pytest.raises(ValueError, match="attempts"):
            w.record(attempts=-1, delay=0.0, total_delay=0.0)

    def test_negative_delay_raises(self):
        w = Watermark()
        with pytest.raises(ValueError, match="delay"):
            w.record(attempts=1, delay=-0.5, total_delay=0.0)

    def test_negative_total_delay_raises(self):
        w = Watermark()
        with pytest.raises(ValueError, match="total_delay"):
            w.record(attempts=1, delay=0.0, total_delay=-1.0)


class TestWatermarkReset:
    def test_reset_clears_all_fields(self):
        w = Watermark()
        w.record(attempts=3, delay=2.0, total_delay=5.0)
        w.reset()
        assert w.peak_attempts == 0
        assert w.peak_delay == 0.0
        assert w.peak_total_delay == 0.0
        assert w.total_records == 0


class TestWatermarkAsDict:
    def test_as_dict_keys(self):
        w = Watermark()
        w.record(attempts=2, delay=1.0, total_delay=3.0)
        d = w.as_dict()
        assert set(d.keys()) == {
            "peak_attempts",
            "peak_delay",
            "peak_total_delay",
            "total_records",
        }

    def test_as_dict_values(self):
        w = Watermark()
        w.record(attempts=2, delay=1.0, total_delay=3.0)
        d = w.as_dict()
        assert d["peak_attempts"] == 2
        assert d["peak_delay"] == 1.0
        assert d["peak_total_delay"] == 3.0
        assert d["total_records"] == 1

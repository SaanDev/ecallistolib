"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import pytest

from conftest import create_sample_fits

from ecallistolib.combine import (
    can_combine_frequency,
    can_combine_time,
    combine_frequency,
    combine_time,
)
from ecallistolib.exceptions import CombineError


def test_can_combine_frequency_true(tmp_path):
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_120000_02.fit"
    create_sample_fits(f1, n_freq=10, n_time=20, freq_start=100, freq_end=200)
    create_sample_fits(f2, n_freq=10, n_time=20, freq_start=200, freq_end=300)

    assert can_combine_frequency(f1, f2)


def test_combine_frequency_raises_on_time_mismatch(tmp_path):
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_120000_02.fit"
    create_sample_fits(f1, n_freq=10, n_time=20)
    create_sample_fits(f2, n_freq=10, n_time=15)

    with pytest.raises(CombineError, match="time axes"):
        combine_frequency(f1, f2)


def test_combine_frequency_happy_path(tmp_path):
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_120000_02.fit"
    create_sample_fits(f1, n_freq=10, n_time=20, freq_start=100, freq_end=200)
    create_sample_fits(f2, n_freq=10, n_time=20, freq_start=200, freq_end=300)

    out = combine_frequency(f1, f2)
    assert out.shape == (20, 20)
    assert out.meta["combined"]["mode"] == "frequency"


def test_can_combine_time_true(tmp_path):
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_121500_01.fit"
    create_sample_fits(f1, n_freq=10, n_time=20, freq_start=100, freq_end=200)
    create_sample_fits(f2, n_freq=10, n_time=20, freq_start=100, freq_end=200)

    assert can_combine_time([f1, f2])


def test_can_combine_time_false_when_frequency_axes_differ(tmp_path):
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_121500_01.fit"
    create_sample_fits(f1, n_freq=10, n_time=20, freq_start=100, freq_end=200)
    create_sample_fits(f2, n_freq=10, n_time=20, freq_start=120, freq_end=220)

    assert not can_combine_time([f1, f2])


def test_combine_time_raises_on_empty_input():
    with pytest.raises(CombineError, match="At least one path"):
        combine_time([])


def test_combine_time_raises_on_frequency_mismatch(tmp_path):
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_121500_01.fit"
    create_sample_fits(f1, n_freq=10, n_time=20, freq_start=100, freq_end=200)
    create_sample_fits(f2, n_freq=10, n_time=20, freq_start=120, freq_end=220)

    with pytest.raises(CombineError, match="frequency axes"):
        combine_time([f1, f2])


def test_combine_time_happy_path(tmp_path):
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_121500_01.fit"
    create_sample_fits(f1, n_freq=10, n_time=20, freq_start=100, freq_end=200)
    create_sample_fits(f2, n_freq=10, n_time=20, freq_start=100, freq_end=200)

    out = combine_time([f1, f2])
    assert out.shape == (10, 40)
    assert out.meta["combined"]["mode"] == "time"
    assert out.time_s[20] > out.time_s[19]


def test_can_combine_time_invalid_filename_returns_false(tmp_path):
    p1 = tmp_path / "BADNAME.fit"
    p2 = tmp_path / "SAMPLE_20240101_121500_01.fit"
    p1.write_text("x")
    create_sample_fits(p2, n_freq=10, n_time=20, freq_start=100, freq_end=200)

    assert not can_combine_time([p1, p2])

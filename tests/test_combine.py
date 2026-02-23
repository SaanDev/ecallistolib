"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import pytest
import numpy as np
from pathlib import Path

from conftest import create_sample_fits

import ecallistolib.combine as combine_mod
from ecallistolib.combine import (
    can_combine_frequency,
    can_combine_time,
    combine_frequency,
    combine_time,
)
from ecallistolib.exceptions import CombineError
from ecallistolib.models import DynamicSpectrum


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
    assert out.meta["combined"]["time_alignment"] == "legacy"
    assert out.meta["combined"]["freq_atol"] == 0.01
    assert out.time_s[20] > out.time_s[19]


def test_can_combine_time_invalid_filename_returns_false(tmp_path):
    p1 = tmp_path / "BADNAME.fit"
    p2 = tmp_path / "SAMPLE_20240101_121500_01.fit"
    p1.write_text("x")
    create_sample_fits(p2, n_freq=10, n_time=20, freq_start=100, freq_end=200)

    assert not can_combine_time([p1, p2])


def test_combine_time_normalized_segment_time(monkeypatch):
    p1 = Path("SAMPLE_20240101_120000_01.fit")
    p2 = Path("SAMPLE_20240101_121500_01.fit")

    ds1 = DynamicSpectrum(
        data=np.array([[1.0, 2.0, 3.0]]),
        freqs_mhz=np.array([100.0]),
        time_s=np.array([0.0, 1.0, 2.0]),
        source=p1,
        meta={},
    )
    ds2 = DynamicSpectrum(
        data=np.array([[4.0, 5.0, 6.0]]),
        freqs_mhz=np.array([100.0]),
        time_s=np.array([10.0, 11.0, 12.0]),
        source=p2,
        meta={},
    )

    def fake_read_fits(path):
        return ds1 if "120000" in str(path) else ds2

    monkeypatch.setattr(combine_mod, "read_fits", fake_read_fits)

    legacy = combine_time([p1, p2], normalize_segment_time=False)
    normalized = combine_time([p1, p2], normalize_segment_time=True)

    assert np.allclose(legacy.time_s, [0.0, 1.0, 2.0, 13.0, 14.0, 15.0])
    assert np.allclose(normalized.time_s, [0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    assert normalized.meta["combined"]["time_alignment"] == "normalized"


def test_combine_time_freq_atol_controls_compatibility(monkeypatch):
    p1 = Path("SAMPLE_20240101_120000_01.fit")
    p2 = Path("SAMPLE_20240101_121500_01.fit")

    ds1 = DynamicSpectrum(
        data=np.array([[1.0, 2.0, 3.0]]),
        freqs_mhz=np.array([100.0]),
        time_s=np.array([0.0, 1.0, 2.0]),
        source=p1,
        meta={},
    )
    ds2 = DynamicSpectrum(
        data=np.array([[4.0, 5.0, 6.0]]),
        freqs_mhz=np.array([100.03]),
        time_s=np.array([0.0, 1.0, 2.0]),
        source=p2,
        meta={},
    )

    def fake_read_fits(path):
        return ds1 if "120000" in str(path) else ds2

    monkeypatch.setattr(combine_mod, "read_fits", fake_read_fits)

    with pytest.raises(CombineError, match="frequency axes"):
        combine_time([p1, p2])

    out = combine_time([p1, p2], freq_atol=0.05)
    assert out.shape == (1, 6)
    assert out.meta["combined"]["freq_atol"] == 0.05

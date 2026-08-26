from pathlib import Path

import numpy as np
import pytest

import ecallistolib.combine as combine_module
from ecallistolib.combine import (
    FrequencyCombinationReport,
    combine_frequency,
    describe_frequency_combination,
)
from ecallistolib.exceptions import CombineError
from ecallistolib.models import DynamicSpectrum


def _spectrum(path: Path, freqs, values, *, time=None, meta=None) -> DynamicSpectrum:
    freq_array = np.asarray(freqs, dtype=float)
    data = np.asarray(values, dtype=float).reshape(freq_array.size, -1)
    return DynamicSpectrum(
        data=data,
        freqs_mhz=freq_array,
        time_s=np.asarray([0.0] if time is None else time, dtype=float),
        source=path,
        meta={} if meta is None else meta,
    )


def _install(monkeypatch, mapping):
    monkeypatch.setattr(combine_module, "read_fits", lambda path: mapping[Path(path)])


def test_frequency_report_describes_gap(monkeypatch):
    low = Path("STAT_20240101_120000_01.fit")
    high = Path("STAT_20240101_120000_02.fit")
    _install(
        monkeypatch,
        {
            low: _spectrum(low, [20, 10], [[1], [2]]),
            high: _spectrum(high, [50, 40], [[5], [4]]),
        },
    )

    report = describe_frequency_combination([low, high])

    assert isinstance(report, FrequencyCombinationReport)
    assert report.has_gap is True
    assert report.has_overlap is False
    assert report.gaps[0].low_mhz == pytest.approx(20.0)
    assert report.gaps[0].high_mhz == pytest.approx(40.0)


def test_frequency_gap_modes_match_analyzer_rules(monkeypatch):
    low = Path("STAT_20240101_120000_01.fit")
    high = Path("STAT_20240101_120000_02.fit")
    mapping = {
        low: _spectrum(low, [20, 10], [[10], [20]]),
        high: _spectrum(high, [50, 40], [[30], [40]]),
    }
    _install(monkeypatch, mapping)

    background = combine_frequency([low, high], gap_fill="background")
    average = combine_frequency([low, high], gap_fill="average")
    hatched = combine_frequency([low, high], gap_fill="hatched")
    zero = combine_frequency([low, high], gap_fill="zero")

    assert np.array_equal(background.freqs_mhz, [50, 40, 30, 20, 10])
    assert background.data[2, 0] == pytest.approx(22.5)
    assert average.data[2, 0] == pytest.approx(22.5)
    assert np.isnan(hatched.data[2, 0])
    assert hatched.meta["combined"]["gap_row_mask"].tolist() == [False, False, True, False, False]
    assert zero.data[2, 0] == 0.0


def test_frequency_overlap_policies_and_custom_connection(monkeypatch):
    low = Path("STAT_20240101_120000_01.fit")
    high = Path("STAT_20240101_120000_02.fit")
    mapping = {
        low: _spectrum(low, [40, 30, 20, 10], [[40], [30], [20], [10]]),
        high: _spectrum(high, [60, 50, 40, 30], [[600], [500], [400], [300]]),
    }
    _install(monkeypatch, mapping)

    split = combine_frequency([low, high], overlap_policy="split", overlap_connection_mhz=35)
    keep_low = combine_frequency([low, high], overlap_policy="low")
    keep_high = combine_frequency([low, high], overlap_policy="high")

    assert np.array_equal(split.data.ravel(), [600, 500, 400, 30, 20, 10])
    assert np.array_equal(keep_low.data.ravel(), [600, 500, 40, 30, 20, 10])
    assert np.array_equal(keep_high.data.ravel(), [600, 500, 400, 300, 20, 10])
    with pytest.raises(CombineError, match="rejects overlap"):
        combine_frequency([low, high], overlap_policy="reject")


def test_frequency_combines_three_irregular_bands(monkeypatch):
    paths = [Path(f"STAT_20240101_120000_0{index}.fit") for index in range(1, 4)]
    mapping = {
        paths[0]: _spectrum(paths[0], [11.0, 10.0], [[1], [2]]),
        paths[1]: _spectrum(paths[1], [20.1, 18.9], [[3], [4]]),
        paths[2]: _spectrum(paths[2], [31.0, 29.0], [[5], [6]]),
    }
    _install(monkeypatch, mapping)

    result = combine_frequency(paths)

    assert result.freqs_mhz[0] == pytest.approx(31.0)
    assert result.freqs_mhz[-1] == pytest.approx(10.0)
    assert result.meta["combined"]["algorithm"] == "ecallisto_fits_analyzer_2.8.0"
    assert len(result.meta["combined"]["sources"]) == 3


def test_frequency_rejects_duplicate_focus_and_time_mismatch(monkeypatch):
    one = Path("STAT_20240101_120000_01.fit")
    duplicate = Path("duplicate/STAT_20240101_120000_01.fit")
    other = Path("STAT_20240101_120000_02.fit")
    mapping = {
        one: _spectrum(one, [20, 10], [[1, 2], [3, 4]], time=[0, 1]),
        duplicate: _spectrum(duplicate, [40, 30], [[1, 2], [3, 4]], time=[0, 1]),
        other: _spectrum(other, [40, 30], [[1], [2]], time=[0]),
    }
    _install(monkeypatch, mapping)

    with pytest.raises(CombineError, match="distinct focus"):
        combine_frequency(one, duplicate)
    with pytest.raises(CombineError, match="time axes"):
        combine_frequency(one, other)


def test_frequency_rejects_focus_and_frequency_header_mismatches(monkeypatch):
    one = Path("STAT_20240101_120000_01.fit")
    two = Path("STAT_20240101_120000_02.fit")
    mapping = {
        one: _spectrum(
            one,
            [20, 10],
            [[1], [2]],
            meta={"fits_header": {"FOCUS": "02"}},
        ),
        two: _spectrum(two, [40, 30], [[3], [4]]),
    }
    _install(monkeypatch, mapping)

    with pytest.raises(CombineError, match="Focus code mismatch"):
        combine_frequency(one, two)

    mapping[one] = _spectrum(
        one,
        [20, 10],
        [[1], [2]],
        meta={"fits_header": {"FREQMIN": 0, "FREQMAX": 20}},
    )
    with pytest.raises(CombineError, match="Header frequency range"):
        combine_frequency(one, two)

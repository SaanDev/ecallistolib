"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Literal

import numpy as np

from .exceptions import CombineError, InvalidFITSError, InvalidFilenameError
from .io import parse_callisto_filename, read_fits
from .models import DynamicSpectrum


def _require_observation_start(ds: DynamicSpectrum, path: str | Path) -> datetime:
    """Return the observation start datetime for actual-timeline combination."""
    observation_start = ds.start_datetime
    if observation_start is None:
        raise CombineError(
            "Actual timeline combination requires observation_start metadata "
            f"for every segment. Missing for: {path}"
        )
    return observation_start


def can_combine_frequency(path1: str | Path, path2: str | Path, time_atol: float = 0.01) -> bool:
    """
    True if:
      - same station/date/time
      - different focus (01 vs 02)
      - time axes match within tolerance
    """
    try:
        p1 = parse_callisto_filename(path1)
        p2 = parse_callisto_filename(path2)
    except InvalidFilenameError:
        return False

    if (
        (p1.station != p2.station)
        or (p1.date_yyyymmdd != p2.date_yyyymmdd)
        or (p1.time_hhmmss != p2.time_hhmmss)
    ):
        return False
    if p1.focus == p2.focus:
        return False

    try:
        ds1 = read_fits(path1)
        ds2 = read_fits(path2)
    except (FileNotFoundError, InvalidFITSError):
        return False

    if ds1.time_s.shape != ds2.time_s.shape:
        return False
    return bool(np.allclose(ds1.time_s, ds2.time_s, atol=time_atol))


def combine_frequency(path1: str | Path, path2: str | Path) -> DynamicSpectrum:
    """
    Stack two spectra along frequency axis (vertical stacking).
    """
    try:
        p1 = parse_callisto_filename(path1)
        p2 = parse_callisto_filename(path2)
    except InvalidFilenameError as e:
        raise CombineError(f"Invalid filename for frequency combination: {e}") from e

    if (
        (p1.station != p2.station)
        or (p1.date_yyyymmdd != p2.date_yyyymmdd)
        or (p1.time_hhmmss != p2.time_hhmmss)
    ):
        raise CombineError("Frequency combination requires same station/date/time.")
    if p1.focus == p2.focus:
        raise CombineError("Frequency combination requires different focus values.")

    try:
        ds1 = read_fits(path1)
        ds2 = read_fits(path2)
    except (FileNotFoundError, InvalidFITSError) as e:
        raise CombineError(f"Failed to read input FITS file: {e}") from e

    if ds1.time_s.shape != ds2.time_s.shape or not np.allclose(ds1.time_s, ds2.time_s, atol=0.01):
        raise CombineError("Cannot combine along frequency: time axes are not compatible.")

    data = np.vstack([ds1.data, ds2.data])
    freqs = np.concatenate([ds1.freqs_mhz, ds2.freqs_mhz])

    meta = dict(ds1.meta)
    meta["combined"] = {"mode": "frequency", "sources": [str(ds1.source), str(ds2.source)]}
    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=ds1.time_s, source=ds1.source, meta=meta)


def can_combine_time(paths: Iterable[str | Path], freq_atol: float = 0.01) -> bool:
    """
    True if all files:
      - same station/date/focus
      - same frequency axis within tolerance
    """
    paths = list(paths)
    if len(paths) < 2:
        return False

    try:
        parts = [parse_callisto_filename(p) for p in paths]
    except InvalidFilenameError:
        return False

    stations = {p.station for p in parts}
    dates = {p.date_yyyymmdd for p in parts}
    focuses = {p.focus for p in parts}

    if len(stations) != 1 or len(dates) != 1 or len(focuses) != 1:
        return False

    try:
        ref = read_fits(paths[0]).freqs_mhz
    except (FileNotFoundError, InvalidFITSError):
        return False

    for p in paths[1:]:
        try:
            freqs = read_fits(p).freqs_mhz
        except (FileNotFoundError, InvalidFITSError):
            return False
        if freqs.shape != ref.shape:
            return False
        if not np.allclose(freqs, ref, atol=freq_atol):
            return False

    return True


def combine_time(
    paths: Iterable[str | Path],
    *,
    timeline: Literal["contiguous", "actual"] = "contiguous",
    normalize_segment_time: bool = False,
    freq_atol: float = 0.01,
) -> DynamicSpectrum:
    """
    Concatenate spectra along time axis (horizontal concatenation).
    Assumes all have identical frequency axis.

    Parameters
    ----------
    paths : Iterable[str | Path]
        Input FITS paths.
    timeline : {"contiguous", "actual"}
        - ``"contiguous"`` (default): place each segment immediately after the
          previous segment, ignoring gaps in observation start times.
        - ``"actual"``: preserve real offsets between segment start times using
          absolute observation timestamps from FITS headers or filenames.
    normalize_segment_time : bool
        Applies only when ``timeline="contiguous"``.
        If False (default), preserve legacy behavior by shifting each segment's
        full time axis by ``last_time + dt``. If True, normalize each segment to
        start at zero before shifting, which avoids over-shifting when a segment
        has a non-zero local start time.
    freq_atol : float
        Absolute tolerance for frequency axis compatibility checks.
    """
    paths = list(paths)
    if not paths:
        raise CombineError("At least one path is required to combine spectra in time.")
    if timeline not in {"contiguous", "actual"}:
        raise ValueError("timeline must be one of: 'contiguous', 'actual'")
    if freq_atol < 0:
        raise ValueError("freq_atol must be >= 0")
    if timeline == "actual" and normalize_segment_time:
        raise ValueError("normalize_segment_time cannot be used with timeline='actual'")

    try:
        parsed = [(p, parse_callisto_filename(p)) for p in paths]
    except InvalidFilenameError as e:
        raise CombineError(f"Invalid filename for time combination: {e}") from e

    stations = {item[1].station for item in parsed}
    dates = {item[1].date_yyyymmdd for item in parsed}
    focuses = {item[1].focus for item in parsed}
    if len(stations) != 1 or len(dates) != 1 or len(focuses) != 1:
        raise CombineError("Time combination requires same station/date/focus across all files.")

    paths = [item[0] for item in sorted(parsed, key=lambda item: item[1].time_hhmmss)]

    try:
        ds0 = read_fits(paths[0])
    except (FileNotFoundError, InvalidFITSError) as e:
        raise CombineError(f"Failed to read input FITS file: {e}") from e

    if ds0.time_s.size == 0:
        raise CombineError("Cannot combine spectra with empty time axis.")

    combined_data = ds0.data
    combined_time = ds0.time_s
    freqs = ds0.freqs_mhz
    segment_offsets_s = [0.0]
    base_observation_start = ds0.start_datetime if timeline == "actual" else None
    if timeline == "actual":
        base_observation_start = _require_observation_start(ds0, paths[0])

    for p in paths[1:]:
        try:
            ds = read_fits(p)
        except (FileNotFoundError, InvalidFITSError) as e:
            raise CombineError(f"Failed to read input FITS file: {e}") from e

        if ds.time_s.size == 0:
            raise CombineError(f"Cannot combine spectrum with empty time axis: {p}")
        if ds.freqs_mhz.shape != freqs.shape or not np.allclose(ds.freqs_mhz, freqs, atol=freq_atol):
            raise CombineError("Cannot combine along time: frequency axes are not compatible.")

        if timeline == "actual":
            observation_start = _require_observation_start(ds, p)
            assert base_observation_start is not None
            start_offset_s = float((observation_start - base_observation_start).total_seconds())
            adjusted_time = ds.time_s + start_offset_s
        else:
            if ds.time_s.size > 1:
                dt = float(ds.time_s[1] - ds.time_s[0])
            else:
                dt = 1.0

            shift = float(combined_time[-1] + dt)
            if normalize_segment_time:
                adjusted_time = (ds.time_s - float(ds.time_s[0])) + shift
            else:
                adjusted_time = ds.time_s + shift
            start_offset_s = float(shift)

        combined_data = np.concatenate([combined_data, ds.data], axis=1)
        combined_time = np.concatenate([combined_time, adjusted_time])
        segment_offsets_s.append(start_offset_s)

    meta = dict(ds0.meta)
    if ds0.start_datetime is not None:
        meta["observation_start"] = ds0.start_datetime
        meta["observation_end"] = ds0.start_datetime + timedelta(seconds=float(np.max(combined_time)))
        if ds0.meta.get("ut_start_sec") is not None:
            meta["ut_start_sec"] = float(ds0.meta["ut_start_sec"])
    meta["combined"] = {
        "mode": "time",
        "sources": [str(Path(p)) for p in paths],
        "timeline": timeline,
        "time_alignment": (
            "actual"
            if timeline == "actual"
            else ("normalized" if normalize_segment_time else "legacy")
        ),
        "freq_atol": float(freq_atol),
        "segment_offsets_s": segment_offsets_s,
    }
    return DynamicSpectrum(data=combined_data, freqs_mhz=freqs, time_s=combined_time, source=ds0.source, meta=meta)

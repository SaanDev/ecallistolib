"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from .exceptions import CombineError, InvalidFITSError, InvalidFilenameError
from .io import parse_callisto_filename, read_fits
from .models import DynamicSpectrum


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


def combine_time(paths: Iterable[str | Path]) -> DynamicSpectrum:
    """
    Concatenate spectra along time axis (horizontal concatenation).
    Assumes all have identical frequency axis.
    """
    paths = list(paths)
    if not paths:
        raise CombineError("At least one path is required to combine spectra in time.")

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

    for p in paths[1:]:
        try:
            ds = read_fits(p)
        except (FileNotFoundError, InvalidFITSError) as e:
            raise CombineError(f"Failed to read input FITS file: {e}") from e

        if ds.time_s.size == 0:
            raise CombineError(f"Cannot combine spectrum with empty time axis: {p}")
        if ds.freqs_mhz.shape != freqs.shape or not np.allclose(ds.freqs_mhz, freqs, atol=0.01):
            raise CombineError("Cannot combine along time: frequency axes are not compatible.")

        if ds.time_s.size > 1:
            dt = float(ds.time_s[1] - ds.time_s[0])
        else:
            dt = 1.0

        shift = float(combined_time[-1] + dt)
        adjusted_time = ds.time_s + shift

        combined_data = np.concatenate([combined_data, ds.data], axis=1)
        combined_time = np.concatenate([combined_time, adjusted_time])

    meta = dict(ds0.meta)
    meta["combined"] = {"mode": "time", "sources": [str(Path(p)) for p in paths]}
    return DynamicSpectrum(data=combined_data, freqs_mhz=freqs, time_s=combined_time, source=ds0.source, meta=meta)

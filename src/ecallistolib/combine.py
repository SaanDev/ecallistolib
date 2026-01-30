"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.3
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np

from .io import parse_callisto_filename, read_fits
from .models import DynamicSpectrum


def can_combine_frequency(path1: str | Path, path2: str | Path, time_atol: float = 0.01) -> bool:
    """
    True if:
      - same station/date/time
      - different focus (01 vs 02)
      - time axes match within tolerance
    """
    p1 = parse_callisto_filename(path1)
    p2 = parse_callisto_filename(path2)

    if (p1.station != p2.station) or (p1.date_yyyymmdd != p2.date_yyyymmdd) or (p1.time_hhmmss != p2.time_hhmmss):
        return False
    if p1.focus == p2.focus:
        return False

    ds1 = read_fits(path1)
    ds2 = read_fits(path2)
    return np.allclose(ds1.time_s, ds2.time_s, atol=time_atol)


def combine_frequency(path1: str | Path, path2: str | Path) -> DynamicSpectrum:
    """
    Stack two spectra along frequency axis (vertical stacking).
    """
    ds1 = read_fits(path1)
    ds2 = read_fits(path2)

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

    parts = [parse_callisto_filename(p) for p in paths]
    stations = {p.station for p in parts}
    dates = {p.date_yyyymmdd for p in parts}
    focuses = {p.focus for p in parts}

    if len(stations) != 1 or len(dates) != 1 or len(focuses) != 1:
        return False

    ref = read_fits(paths[0]).freqs_mhz
    for p in paths[1:]:
        freqs = read_fits(p).freqs_mhz
        if not np.allclose(freqs, ref, atol=freq_atol):
            return False

    return True


def combine_time(paths: Iterable[str | Path]) -> DynamicSpectrum:
    """
    Concatenate spectra along time axis (horizontal concatenation).
    Assumes all have identical frequency axis.
    """
    paths = sorted(list(paths), key=lambda p: parse_callisto_filename(p).time_hhmmss)

    ds0 = read_fits(paths[0])
    combined_data = ds0.data
    combined_time = ds0.time_s
    freqs = ds0.freqs_mhz

    for p in paths[1:]:
        ds = read_fits(p)

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


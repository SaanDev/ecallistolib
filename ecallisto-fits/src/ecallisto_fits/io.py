from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from astropy.io import fits

from .models import DynamicSpectrum


@dataclass(frozen=True)
class CallistoFileParts:
    station: str
    date_yyyymmdd: str
    time_hhmmss: str
    focus: str


def parse_callisto_filename(path: str | Path) -> CallistoFileParts:
    """
    Parse e-CALLISTO style filenames like:
    STATION_YYYYMMDD_HHMMSS_FOCUS.fit.gz
    """
    base = Path(path).name
    parts = base.split("_")
    if len(parts) < 4:
        raise ValueError(f"Invalid CALLISTO filename format: {base}")

    station = parts[0]
    date_yyyymmdd = parts[1]
    time_hhmmss = parts[2]
    focus = parts[3].split(".")[0]
    return CallistoFileParts(station, date_yyyymmdd, time_hhmmss, focus)


def _try_read_ut_start_seconds(hdul: fits.HDUList) -> Optional[float]:
    """
    Reads TIME-OBS from primary header if present and returns seconds since 00:00:00.
    """
    try:
        hdr = hdul[0].header
        hh, mm, ss = str(hdr["TIME-OBS"]).split(":")
        return int(hh) * 3600 + int(mm) * 60 + float(ss)
    except Exception:
        return None


def read_fits(path: str | Path) -> DynamicSpectrum:
    """
    Read an e-CALLISTO FITS file (.fit or .fit.gz) into a DynamicSpectrum.
    """
    path = Path(path)

    with fits.open(path) as hdul:
        data = np.asarray(hdul[0].data, dtype=float)
        freqs = np.asarray(hdul[1].data["frequency"][0], dtype=float)
        time_s = np.asarray(hdul[1].data["time"][0], dtype=float)
        ut_start_sec = _try_read_ut_start_seconds(hdul)

    meta = {"ut_start_sec": ut_start_sec}
    try:
        parts = parse_callisto_filename(path)
        meta |= {
            "station": parts.station,
            "date": parts.date_yyyymmdd,
            "time": parts.time_hhmmss,
            "focus": parts.focus,
        }
    except Exception:
        pass

    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=time_s, source=path, meta=meta)

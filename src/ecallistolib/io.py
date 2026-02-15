"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Optional

import numpy as np
from astropy.io import fits

from .exceptions import InvalidFilenameError, InvalidFITSError
from .models import DynamicSpectrum


@dataclass(frozen=True)
class CallistoFileParts:
    station: str
    date_yyyymmdd: str
    time_hhmmss: str
    focus: str


_DATE_RE = re.compile(r"^\d{8}$")
_TIME_RE = re.compile(r"^\d{6}$")
_FOCUS_RE = re.compile(r"^\d+$")
_KNOWN_SUFFIXES = (".fit.gz", ".fit")


def parse_callisto_filename(path: str | Path) -> CallistoFileParts:
    """
    Parse e-CALLISTO style filenames like:
    STATION_YYYYMMDD_HHMMSS_FOCUS.fit.gz

    Raises
    ------
    InvalidFilenameError
        If the filename doesn't match the expected format.
    """
    base = Path(path).name
    stem = base
    for suffix in _KNOWN_SUFFIXES:
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break

    parts = stem.split("_")
    if len(parts) < 4:
        raise InvalidFilenameError(f"Invalid CALLISTO filename format: {base}")

    station = "_".join(parts[:-3])
    date_yyyymmdd = parts[-3]
    time_hhmmss = parts[-2]
    focus = parts[-1]

    if not station:
        raise InvalidFilenameError(f"Invalid CALLISTO filename format: {base}")
    if not _DATE_RE.fullmatch(date_yyyymmdd):
        raise InvalidFilenameError(f"Invalid date in CALLISTO filename: {base}")
    if not _TIME_RE.fullmatch(time_hhmmss):
        raise InvalidFilenameError(f"Invalid time in CALLISTO filename: {base}")
    if not _FOCUS_RE.fullmatch(focus):
        raise InvalidFilenameError(f"Invalid focus in CALLISTO filename: {base}")
    try:
        datetime.strptime(f"{date_yyyymmdd}{time_hhmmss}", "%Y%m%d%H%M%S")
    except ValueError as e:
        raise InvalidFilenameError(f"Invalid date/time in CALLISTO filename: {base}") from e

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

    Parameters
    ----------
    path : str or Path
        Path to the FITS file.

    Returns
    -------
    DynamicSpectrum
        The loaded dynamic spectrum.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    InvalidFITSError
        If the file cannot be read or is not a valid e-CALLISTO FITS file.
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"FITS file not found: {path}")

    try:
        with fits.open(path) as hdul:
            if len(hdul) < 2:
                raise InvalidFITSError(
                    f"Expected at least 2 HDUs in FITS file, got {len(hdul)}: {path}"
                )

            if hdul[0].data is None:
                raise InvalidFITSError(f"Primary HDU contains no data: {path}")

            data = np.asarray(hdul[0].data, dtype=float)

            # Check for frequency and time data in extension
            try:
                freqs = np.asarray(hdul[1].data["frequency"][0], dtype=float)
                time_s = np.asarray(hdul[1].data["time"][0], dtype=float)
            except (KeyError, IndexError) as e:
                raise InvalidFITSError(
                    f"Missing frequency or time data in FITS extension: {path}"
                ) from e

            ut_start_sec = _try_read_ut_start_seconds(hdul)

    except OSError as e:
        raise InvalidFITSError(f"Failed to open FITS file: {path}") from e

    meta: dict[str, object] = {"ut_start_sec": ut_start_sec}
    try:
        parts = parse_callisto_filename(path)
        meta |= {
            "station": parts.station,
            "date": parts.date_yyyymmdd,
            "time": parts.time_hhmmss,
            "focus": parts.focus,
        }
    except InvalidFilenameError:
        # Filename parsing is optional, continue without metadata
        pass

    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=time_s, source=path, meta=meta)

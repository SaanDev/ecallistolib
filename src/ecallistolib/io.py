"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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


def _try_parse_iso_datetime(value: str) -> Optional[datetime]:
    """Parse a FITS date/time string into a UTC datetime."""
    text = value.strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _seconds_since_midnight(dt: datetime) -> float:
    """Return seconds since UTC midnight for a timezone-aware datetime."""
    dt_utc = dt.astimezone(timezone.utc)
    return (
        dt_utc.hour * 3600
        + dt_utc.minute * 60
        + dt_utc.second
        + (dt_utc.microsecond / 1_000_000.0)
    )


def _try_read_observation_start(
    hdul: fits.HDUList,
    filename_parts: CallistoFileParts | None,
) -> Optional[datetime]:
    """
    Read observation start time as an absolute UTC datetime.

    Prefer FITS headers, but fall back to the e-CALLISTO filename when needed.
    """
    hdr = hdul[0].header
    date_obs = hdr.get("DATE-OBS")
    time_obs = hdr.get("TIME-OBS")

    if date_obs is not None and time_obs is not None:
        date_text = str(date_obs).strip()
        time_text = str(time_obs).strip()

        parsed = _try_parse_iso_datetime(f"{date_text}T{time_text}")
        if parsed is not None:
            return parsed

        parsed = _try_parse_iso_datetime(date_text)
        if parsed is not None and ("T" in date_text or " " in date_text):
            return parsed

    if date_obs is not None:
        date_text = str(date_obs).strip()
        parsed = _try_parse_iso_datetime(date_text)
        if parsed is not None and ("T" in date_text or " " in date_text):
            return parsed

    if filename_parts is None:
        return None

    try:
        parsed = datetime.strptime(
            f"{filename_parts.date_yyyymmdd}{filename_parts.time_hhmmss}",
            "%Y%m%d%H%M%S",
        )
    except ValueError:
        return None

    return parsed.replace(tzinfo=timezone.utc)


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

    parts: CallistoFileParts | None = None
    try:
        parts = parse_callisto_filename(path)
    except InvalidFilenameError:
        # Filename parsing is optional, continue without metadata
        pass

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
            observation_start = _try_read_observation_start(hdul, parts)
            if ut_start_sec is None and observation_start is not None:
                ut_start_sec = _seconds_since_midnight(observation_start)

    except OSError as e:
        raise InvalidFITSError(f"Failed to open FITS file: {path}") from e

    observation_end = None
    if observation_start is not None and time_s.size > 0:
        observation_end = observation_start + timedelta(seconds=float(np.max(time_s)))

    meta: dict[str, object] = {
        "ut_start_sec": ut_start_sec,
        "observation_start": observation_start,
        "observation_end": observation_end,
    }
    if parts is not None:
        meta |= {
            "station": parts.station,
            "date": parts.date_yyyymmdd,
            "time": parts.time_hhmmss,
            "focus": parts.focus,
        }

    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=time_s, source=path, meta=meta)

"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.3
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

from .exceptions import DownloadError

DEFAULT_BASE_URL = "http://soleil80.cs.technik.fhnw.ch/solarradio/data/2002-20yy_Callisto/"


@dataclass(frozen=True)
class RemoteFITS:
    """Represents a remote FITS file available for download."""
    name: str
    url: str


def list_remote_fits(
    day: date,
    hour: int,
    station_substring: str,
    base_url: str = DEFAULT_BASE_URL,
    timeout_s: float = 10.0,
) -> List[RemoteFITS]:
    """
    Return RemoteFITS entries for a given day/hour and station substring.

    Parameters
    ----------
    day : date
        The date to search for files.
    hour : int
        UTC hour (0-23) to filter files.
    station_substring : str
        Case-insensitive substring to match station names.
    base_url : str
        Base URL of the e-CALLISTO archive.
    timeout_s : float
        HTTP request timeout in seconds.

    Returns
    -------
    List[RemoteFITS]
        List of available remote FITS files matching the criteria.

    Raises
    ------
    ValueError
        If hour is not in [0, 23].
    DownloadError
        If the remote server cannot be reached or returns an error.
    """
    if not (0 <= hour <= 23):
        raise ValueError("hour must be in [0, 23]")

    url_day = f"{base_url.rstrip('/')}/{day.year}/{day.month:02}/{day.day:02}/"

    try:
        r = requests.get(url_day, timeout=timeout_s)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        raise DownloadError(f"Timeout while connecting to {url_day}")
    except requests.exceptions.ConnectionError as e:
        raise DownloadError(f"Failed to connect to {url_day}: {e}")
    except requests.exceptions.HTTPError as e:
        raise DownloadError(f"HTTP error accessing {url_day}: {e}")

    soup = BeautifulSoup(r.content, "html.parser")
    fits_files = [a.get("href") for a in soup.find_all("a") if a.get("href", "").endswith(".fit.gz")]

    out: List[RemoteFITS] = []
    station_substring = station_substring.lower().strip()

    for fn in fits_files:
        if station_substring and (station_substring not in fn.lower()):
            continue
        parts = fn.split("_")
        if len(parts) >= 3:
            try:
                hh = int(parts[2][:2])
                if hh == hour:
                    out.append(RemoteFITS(name=fn, url=url_day + fn))
            except ValueError:
                # Skip files with invalid time format
                continue

    return out


def list_remote_fits_range(
    start_date: date,
    end_date: date,
    hours: Iterable[int] | None = None,
    station_substring: str = "",
    base_url: str = DEFAULT_BASE_URL,
    timeout_s: float = 10.0,
) -> List[RemoteFITS]:
    """
    List available FITS files over a date range.

    Parameters
    ----------
    start_date : date
        Start date (inclusive).
    end_date : date
        End date (inclusive).
    hours : Iterable[int] | None
        UTC hours to include (0-23). If None, includes all hours (0-23).
    station_substring : str
        Case-insensitive substring to match station names.
    base_url : str
        Base URL of the e-CALLISTO archive.
    timeout_s : float
        HTTP request timeout in seconds.

    Returns
    -------
    List[RemoteFITS]
        All matching remote FITS files across the date range.

    Raises
    ------
    ValueError
        If start_date > end_date.

    Example
    -------
    >>> from datetime import date
    >>> files = list_remote_fits_range(
    ...     start_date=date(2023, 6, 1),
    ...     end_date=date(2023, 6, 3),
    ...     hours=[12, 13, 14],
    ...     station_substring="alaska"
    ... )
    """
    from datetime import timedelta

    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")

    hours_to_check = list(hours) if hours is not None else list(range(24))

    results: List[RemoteFITS] = []
    current = start_date

    while current <= end_date:
        for hour in hours_to_check:
            try:
                found = list_remote_fits(
                    day=current,
                    hour=hour,
                    station_substring=station_substring,
                    base_url=base_url,
                    timeout_s=timeout_s,
                )
                results.extend(found)
            except DownloadError:
                # Skip days/hours with no data or connection issues
                continue
        current += timedelta(days=1)

    return results


def download_files(
    items: Iterable[RemoteFITS],
    out_dir: str | Path,
    timeout_s: float = 30.0,
) -> List[Path]:
    """
    Download FITS files to a local directory.

    Parameters
    ----------
    items : Iterable[RemoteFITS]
        Remote FITS files to download.
    out_dir : str or Path
        Output directory for downloaded files.
    timeout_s : float
        HTTP request timeout per file in seconds.

    Returns
    -------
    List[Path]
        List of paths to saved files.

    Raises
    ------
    DownloadError
        If a file cannot be downloaded.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: List[Path] = []
    with requests.Session() as s:
        for it in items:
            try:
                r = s.get(it.url, timeout=timeout_s)
                r.raise_for_status()
            except requests.exceptions.Timeout:
                raise DownloadError(f"Timeout downloading {it.name}")
            except requests.exceptions.RequestException as e:
                raise DownloadError(f"Failed to download {it.name}: {e}")

            target = out_dir / it.name
            target.write_bytes(r.content)
            saved.append(target)

    return saved

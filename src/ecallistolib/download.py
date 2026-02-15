"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, List, Literal

import requests
from bs4 import BeautifulSoup

from .exceptions import DownloadError

DEFAULT_BASE_URL = "http://soleil80.cs.technik.fhnw.ch/solarradio/data/2002-20yy_Callisto/"


@dataclass(frozen=True)
class RemoteFITS:
    """Represents a remote FITS file available for download."""
    name: str
    url: str


def _day_url(day: date, base_url: str) -> str:
    """Build the day directory URL in the e-CALLISTO archive."""
    return f"{base_url.rstrip('/')}/{day.year}/{day.month:02}/{day.day:02}/"


def _extract_hour_from_filename(filename: str) -> int | None:
    """Extract hour from a CALLISTO filename. Returns None if parsing fails."""
    parts = filename.split("_")
    if len(parts) < 4:
        return None
    time_token = parts[-2]
    if len(time_token) < 2 or (not time_token[:2].isdigit()):
        return None
    return int(time_token[:2])


def _fetch_day_listing(
    day: date,
    base_url: str = DEFAULT_BASE_URL,
    timeout_s: float = 10.0,
) -> tuple[str, List[str]]:
    """Fetch and parse all .fit.gz filenames listed for one day."""
    url_day = _day_url(day, base_url)
    try:
        response = requests.get(url_day, timeout=timeout_s)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise DownloadError(f"Timeout while connecting to {url_day}")
    except requests.exceptions.ConnectionError as e:
        raise DownloadError(f"Failed to connect to {url_day}: {e}")
    except requests.exceptions.HTTPError as e:
        raise DownloadError(f"HTTP error accessing {url_day}: {e}")

    soup = BeautifulSoup(response.content, "html.parser")
    fits_files: List[str] = []
    for anchor in soup.find_all("a"):
        href = anchor.get("href")
        if isinstance(href, str) and href.endswith(".fit.gz"):
            fits_files.append(href)
    return url_day, fits_files


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

    url_day, fits_files = _fetch_day_listing(day=day, base_url=base_url, timeout_s=timeout_s)

    out: List[RemoteFITS] = []
    station_substring = station_substring.lower().strip()

    for fn in fits_files:
        if station_substring and (station_substring not in fn.lower()):
            continue
        hh = _extract_hour_from_filename(fn)
        if hh is None:
            continue
        if hh == hour:
            out.append(RemoteFITS(name=fn, url=url_day + fn))

    return out


def list_remote_fits_range(
    start_date: date,
    end_date: date,
    hours: Iterable[int] | None = None,
    station_substring: str = "",
    base_url: str = DEFAULT_BASE_URL,
    timeout_s: float = 10.0,
    error_policy: Literal["skip", "raise"] = "skip",
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
    error_policy : {"skip", "raise"}
        - "skip": skip days that fail to fetch and continue (default).
        - "raise": raise DownloadError on first failed day fetch.

    Returns
    -------
    List[RemoteFITS]
        All matching remote FITS files across the date range.

    Raises
    ------
    ValueError
        If start_date > end_date, an hour is invalid, or error_policy is invalid.

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
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")
    if error_policy not in {"skip", "raise"}:
        raise ValueError("error_policy must be one of: 'skip', 'raise'")

    hours_to_check = list(hours) if hours is not None else list(range(24))
    for hour in hours_to_check:
        if not (0 <= hour <= 23):
            raise ValueError("hours must contain values in [0, 23]")
    hours_set = set(hours_to_check)

    results: List[RemoteFITS] = []
    current = start_date
    station_substring = station_substring.lower().strip()

    while current <= end_date:
        try:
            url_day, fits_files = _fetch_day_listing(
                day=current,
                base_url=base_url,
                timeout_s=timeout_s,
            )
        except DownloadError:
            if error_policy == "raise":
                raise
            current += timedelta(days=1)
            continue

        for fn in fits_files:
            if station_substring and (station_substring not in fn.lower()):
                continue
            hh = _extract_hour_from_filename(fn)
            if hh is None or hh not in hours_set:
                continue
            results.append(RemoteFITS(name=fn, url=url_day + fn))

        current += timedelta(days=1)

    return results


def download_files(
    items: Iterable[RemoteFITS],
    out_dir: str | Path,
    timeout_s: float = 30.0,
    chunk_size: int = 1_048_576,
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
    chunk_size : int
        Number of bytes per chunk when streaming response content.

    Returns
    -------
    List[Path]
        List of paths to saved files.

    Raises
    ------
    DownloadError
        If a file cannot be downloaded.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: List[Path] = []
    with requests.Session() as s:
        for it in items:
            target = out_dir / it.name
            try:
                with s.get(it.url, timeout=timeout_s, stream=True) as r:
                    r.raise_for_status()
                    with target.open("wb") as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
            except requests.exceptions.Timeout:
                if target.exists():
                    target.unlink(missing_ok=True)
                raise DownloadError(f"Timeout downloading {it.name}")
            except requests.exceptions.RequestException as e:
                if target.exists():
                    target.unlink(missing_ok=True)
                raise DownloadError(f"Failed to download {it.name}: {e}")
            except OSError as e:
                if target.exists():
                    target.unlink(missing_ok=True)
                raise DownloadError(f"Failed to save {it.name}: {e}") from e

            saved.append(target)

    return saved

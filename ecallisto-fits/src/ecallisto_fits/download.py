from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

DEFAULT_BASE_URL = "http://soleil80.cs.technik.fhnw.ch/solarradio/data/2002-20yy_Callisto/"


@dataclass(frozen=True)
class RemoteFITS:
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
    """
    if not (0 <= hour <= 23):
        raise ValueError("hour must be in [0, 23]")

    url_day = f"{base_url.rstrip('/')}/{day.year}/{day.month:02}/{day.day:02}/"

    r = requests.get(url_day, timeout=timeout_s)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "html.parser")
    fits_files = [a.get("href") for a in soup.find_all("a") if a.get("href", "").endswith(".fit.gz")]

    out: List[RemoteFITS] = []
    station_substring = station_substring.lower().strip()

    for fn in fits_files:
        if station_substring and (station_substring not in fn.lower()):
            continue
        parts = fn.split("_")
        if len(parts) >= 3:
            hh = int(parts[2][:2])
            if hh == hour:
                out.append(RemoteFITS(name=fn, url=url_day + fn))

    return out


def download_files(
    items: Iterable[RemoteFITS],
    out_dir: str | Path,
    timeout_s: float = 30.0,
) -> List[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved: List[Path] = []
    with requests.Session() as s:
        for it in items:
            r = s.get(it.url, timeout=timeout_s)
            r.raise_for_status()
            target = out_dir / it.name
            target.write_bytes(r.content)
            saved.append(target)

    return saved

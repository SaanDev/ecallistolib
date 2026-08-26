"""GOES XRS science-quality data access and adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.parse import urljoin

import numpy as np

from .exceptions import GOESConnectionError, GOESDataError, GOESDownloadError
from .models import DynamicSpectrum


GOES_CHANNEL_LABELS: Mapping[str, str] = MappingProxyType(
    {"xrsa": "Short (XRS-A, 0.5–4 Å)", "xrsb": "Long (XRS-B, 1–8 Å)"}
)
GOES_CLASS_LEVELS: tuple[tuple[float, str], ...] = (
    (1.0e-8, "A"),
    (1.0e-7, "B"),
    (1.0e-6, "C"),
    (1.0e-5, "M"),
    (1.0e-4, "X"),
)


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _as_datetime64_ns(values: Any) -> np.ndarray:
    array = np.asarray(values)
    if np.issubdtype(array.dtype, np.datetime64):
        return array.astype("datetime64[ns]", copy=False).ravel()
    objects = np.asarray(values, dtype=object).ravel()
    converted = np.empty(objects.size, dtype="datetime64[ns]")
    for index, item in enumerate(objects):
        if not isinstance(item, datetime) and callable(getattr(item, "to_pydatetime", None)):
            item = item.to_pydatetime()
        if isinstance(item, datetime):
            item = _ensure_utc(item).replace(tzinfo=None)
        converted[index] = np.datetime64(item, "ns")
    return converted


@dataclass(frozen=True)
class GOESXRayData:
    """Normalized GOES XRS-A/XRS-B observations in UTC and W/m²."""

    time_utc: np.ndarray
    xrsa_flux_wm2: np.ndarray | None = None
    xrsb_flux_wm2: np.ndarray | None = None
    satellite_number: int | None = None
    sources: tuple[Path, ...] = ()
    meta: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        times = _as_datetime64_ns(self.time_utc)
        if times.size == 0:
            raise GOESDataError("GOES XRS data must contain at least one timestamp.")
        object.__setattr__(self, "time_utc", times)
        for field_name in ("xrsa_flux_wm2", "xrsb_flux_wm2"):
            value = getattr(self, field_name)
            if value is None:
                continue
            array = np.asarray(value, dtype=float).ravel()
            if array.size != times.size:
                raise GOESDataError(
                    f"{field_name} has {array.size} samples but time_utc has {times.size}."
                )
            object.__setattr__(self, field_name, array)
        if self.xrsa_flux_wm2 is None and self.xrsb_flux_wm2 is None:
            raise GOESDataError("GOES XRS data must provide XRS-A or XRS-B flux.")
        object.__setattr__(self, "sources", tuple(Path(item) for item in self.sources))
        object.__setattr__(self, "meta", MappingProxyType(dict(self.meta)))

    @classmethod
    def from_arrays(
        cls,
        time_utc: Sequence[datetime] | np.ndarray,
        *,
        xrsa_flux_wm2: Sequence[float] | np.ndarray | None = None,
        xrsb_flux_wm2: Sequence[float] | np.ndarray | None = None,
        satellite_number: int | None = None,
        meta: Mapping[str, Any] | None = None,
    ) -> "GOESXRayData":
        """Build a normalized data object from user-supplied arrays."""
        return cls(
            time_utc=_as_datetime64_ns(time_utc),
            xrsa_flux_wm2=None if xrsa_flux_wm2 is None else np.asarray(xrsa_flux_wm2, dtype=float),
            xrsb_flux_wm2=None if xrsb_flux_wm2 is None else np.asarray(xrsb_flux_wm2, dtype=float),
            satellite_number=satellite_number,
            meta=dict(meta or {}),
        )

    @property
    def available_channels(self) -> tuple[str, ...]:
        return tuple(
            key
            for key, values in (("xrsa", self.xrsa_flux_wm2), ("xrsb", self.xrsb_flux_wm2))
            if values is not None
        )

    def flux(self, channel: str) -> np.ndarray:
        key = str(channel).lower()
        values = self.xrsa_flux_wm2 if key == "xrsa" else self.xrsb_flux_wm2 if key == "xrsb" else None
        if values is None:
            raise GOESDataError(f"GOES channel {channel!r} is unavailable.")
        return values

    def between(self, start_utc: datetime, end_utc: datetime) -> "GOESXRayData":
        """Return samples inside an inclusive UTC interval."""
        start = np.datetime64(_ensure_utc(start_utc).replace(tzinfo=None), "ns")
        end = np.datetime64(_ensure_utc(end_utc).replace(tzinfo=None), "ns")
        mask = (self.time_utc >= start) & (self.time_utc <= end)
        if not np.any(mask):
            raise GOESDataError("GOES XRS data do not overlap the requested interval.")
        return GOESXRayData(
            self.time_utc[mask],
            None if self.xrsa_flux_wm2 is None else self.xrsa_flux_wm2[mask],
            None if self.xrsb_flux_wm2 is None else self.xrsb_flux_wm2[mask],
            self.satellite_number,
            self.sources,
            self.meta,
        )

def preferred_goes_satellite_numbers(value: date | datetime) -> tuple[int, ...]:
    """Return era-aware satellite candidates in preferred order."""
    year = int(value.year)
    if year >= 2025:
        return (19, 18, 17, 16)
    if year >= 2022:
        return (18, 17, 16, 15, 14, 13)
    if year >= 2017:
        return (17, 16, 15, 14, 13)
    if year >= 2010:
        return (15, 14, 13, 12, 11, 10)
    if year >= 2003:
        return (12, 11, 10, 9, 8)
    return (10, 9, 8)


def _channel_score(name: str, channel: str) -> int:
    text = str(name).lower()
    score = 0
    preferred = ("xrsa", "a_flux", "short", "0.5") if channel == "xrsa" else (
        "xrsb",
        "b_flux",
        "long",
        "1.0",
    )
    if text == f"{channel}_flux":
        score += 200
    if any(token in text for token in preferred):
        score += 80
    if "flux" in text:
        score += 60
    if any(token in text for token in ("flag", "quality", "count", "num", "primary")):
        score -= 250
    return score


def _pick_channel(names: Iterable[str], channel: str) -> str | None:
    scored = sorted(
        ((_channel_score(name, channel), str(name)) for name in names), reverse=True
    )
    return scored[0][1] if scored and scored[0][0] > 0 else None


def _coerce_dataframe(source: Any) -> GOESXRayData:
    frame = source.to_dataframe() if callable(getattr(source, "to_dataframe", None)) else source
    columns = [str(item) for item in getattr(frame, "columns", [])]
    index = getattr(frame, "index", None)
    if not columns or index is None:
        raise GOESDataError("Object is not a supported DataFrame or SunPy TimeSeries.")
    try:
        times = _as_datetime64_ns(index)
    except Exception as exc:
        raise GOESDataError("Could not convert DataFrame index to UTC timestamps.") from exc
    short = _pick_channel(columns, "xrsa")
    long = _pick_channel(columns, "xrsb")
    return _normalize_combined(
        times,
        None if short is None else np.asarray(frame[short], dtype=float),
        None if long is None else np.asarray(frame[long], dtype=float),
        satellite_number=None,
        sources=(),
        meta={"adapter": "dataframe", "xrsa_column": short, "xrsb_column": long},
    )


def _import_netcdf4():
    try:
        import netCDF4
    except ImportError as exc:
        raise ImportError(
            "GOES netCDF support requires the optional dependency group: "
            "pip install 'ecallistolib[goes]'. Restart Python or the Jupyter "
            "kernel after installation."
        ) from exc
    return netCDF4


def _netcdf_times(dataset: Any, netcdf4: Any) -> np.ndarray:
    time_var = dataset.variables.get("time")
    if time_var is None:
        raise GOESDataError("GOES netCDF file is missing the time variable.")
    units = str(getattr(time_var, "units", ""))
    if not units:
        raise GOESDataError("GOES netCDF time variable has no units.")
    calendar = str(getattr(time_var, "calendar", "standard"))
    try:
        values = netcdf4.num2date(
            time_var[:],
            units,
            calendar=calendar,
            only_use_cftime_datetimes=False,
            only_use_python_datetimes=True,
        )
    except Exception as exc:
        raise GOESDataError("Could not decode GOES netCDF timestamps.") from exc
    converted: list[np.datetime64] = []
    for item in np.asarray(values, dtype=object).ravel():
        if isinstance(item, datetime):
            dt = _ensure_utc(item)
        else:
            try:
                dt = datetime(
                    int(item.year),
                    int(item.month),
                    int(item.day),
                    int(getattr(item, "hour", 0)),
                    int(getattr(item, "minute", 0)),
                    int(getattr(item, "second", 0)),
                    int(getattr(item, "microsecond", 0)),
                    tzinfo=timezone.utc,
                )
            except Exception as exc:
                raise GOESDataError(f"Unsupported GOES timestamp {item!r}.") from exc
        converted.append(np.datetime64(dt.replace(tzinfo=None), "ns"))
    return np.asarray(converted, dtype="datetime64[ns]")


def _variable_values(dataset: Any, name: str | None, expected_size: int) -> np.ndarray | None:
    if name is None:
        return None
    array = np.ma.asarray(dataset.variables[name][:]).squeeze()
    if array.ndim != 1 or array.size != expected_size:
        return None
    values = np.asarray(np.ma.filled(array, np.nan), dtype=float)
    return values


def _load_netcdf_path(path: Path) -> GOESXRayData:
    netcdf4 = _import_netcdf4()
    try:
        with netcdf4.Dataset(str(path)) as dataset:
            times = _netcdf_times(dataset, netcdf4)
            names = [str(item) for item in dataset.variables if str(item) != "time"]
            short = _pick_channel(names, "xrsa")
            long = _pick_channel(names, "xrsb")
            xrsa = _variable_values(dataset, short, times.size)
            xrsb = _variable_values(dataset, long, times.size)
            satellite = None
            for attr_name in ("platform", "satellite_id", "satellite", "instrument"):
                value = getattr(dataset, attr_name, None)
                match = re.search(r"(?:GOES|G)?[- ]?(\d{1,2})", str(value or ""), re.IGNORECASE)
                if match:
                    satellite = int(match.group(1))
                    break
    except GOESDataError:
        raise
    except Exception as exc:
        raise GOESDataError(f"Could not read GOES netCDF file {path}.") from exc
    return _normalize_combined(
        times,
        xrsa,
        xrsb,
        satellite_number=satellite,
        sources=(path,),
        meta={"adapter": "netcdf", "xrsa_variable": short, "xrsb_variable": long},
    )


def _normalize_combined(
    times: np.ndarray,
    xrsa: np.ndarray | None,
    xrsb: np.ndarray | None,
    *,
    satellite_number: int | None,
    sources: tuple[Path, ...],
    meta: Mapping[str, Any],
) -> GOESXRayData:
    time_array = np.asarray(times, dtype="datetime64[ns]").ravel()
    arrays = [None if values is None else np.asarray(values, dtype=float).ravel() for values in (xrsa, xrsb)]
    valid_time = ~np.isnat(time_array)
    if not np.any(valid_time):
        raise GOESDataError("GOES data contain no valid timestamps.")
    time_array = time_array[valid_time]
    arrays = [None if values is None else values[valid_time] for values in arrays]
    order = np.argsort(time_array, kind="stable")
    time_array = time_array[order]
    arrays = [None if values is None else values[order] for values in arrays]

    unique_times, inverse = np.unique(time_array, return_inverse=True)
    if unique_times.size != time_array.size:
        merged: list[np.ndarray | None] = []
        for values in arrays:
            if values is None:
                merged.append(None)
                continue
            output = np.full(unique_times.size, np.nan, dtype=float)
            for idx in range(unique_times.size):
                output[idx] = float(np.nanmedian(values[inverse == idx]))
            merged.append(output)
        time_array, arrays = unique_times, merged

    cleaned: list[np.ndarray | None] = []
    for values in arrays:
        if values is None:
            cleaned.append(None)
            continue
        output = np.asarray(values, dtype=float).copy()
        output[~np.isfinite(output) | (output <= 0.0)] = np.nan
        cleaned.append(output)
    if all(values is None or not np.any(np.isfinite(values)) for values in cleaned):
        raise GOESDataError("GOES data contain no positive finite XRS samples.")
    return GOESXRayData(
        time_array,
        cleaned[0],
        cleaned[1],
        satellite_number,
        sources,
        dict(meta),
    )


def load_goes_xray(source: Any) -> GOESXRayData:
    """Load GOES data from arrays/dataframes, SunPy TimeSeries, or netCDF paths."""
    if isinstance(source, GOESXRayData):
        return source
    if isinstance(source, (str, Path)):
        paths = [Path(source)]
    elif isinstance(source, Iterable) and not hasattr(source, "columns"):
        values = list(source)
        if values and all(isinstance(item, (str, Path)) for item in values):
            paths = [Path(item) for item in values]
        else:
            return _coerce_dataframe(source)
    else:
        return _coerce_dataframe(source)
    if not paths:
        raise GOESDataError("At least one GOES data path is required.")
    loaded = [_load_netcdf_path(path) for path in paths]
    if len(loaded) == 1:
        return loaded[0]
    times = np.concatenate([item.time_utc for item in loaded])

    def concatenate_channel(channel: str) -> np.ndarray | None:
        if not any(channel in item.available_channels for item in loaded):
            return None
        return np.concatenate(
            [
                item.flux(channel)
                if channel in item.available_channels
                else np.full(item.time_utc.size, np.nan)
                for item in loaded
            ]
        )

    satellites = {item.satellite_number for item in loaded if item.satellite_number is not None}
    return _normalize_combined(
        times,
        concatenate_channel("xrsa"),
        concatenate_channel("xrsb"),
        satellite_number=next(iter(satellites)) if len(satellites) == 1 else None,
        sources=tuple(path for item in loaded for path in item.sources),
        meta={"adapter": "netcdf_collection", "satellite_numbers": sorted(satellites)},
    )


def _cache_root(cache_dir: str | Path | None) -> Path:
    if cache_dir is not None:
        return Path(cache_dir).expanduser()
    try:
        from platformdirs import user_cache_path

        return Path(user_cache_path("ecallistolib", appauthor=False)) / "goes_xrs"
    except ImportError:
        return Path.home() / ".cache" / "ecallistolib" / "goes_xrs"


def _archive_directory(satellite: int, day: date) -> str:
    if satellite >= 16:
        return (
            "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/"
            f"goes/goes{satellite}/l2/data/xrsf-l2-avg1m_science/{day.year:04d}/{day.month:02d}/"
        )
    return (
        "https://www.ncei.noaa.gov/data/goes-space-environment-monitor/access/science/xrs/"
        f"goes{satellite:02d}/xrsf-l2-avg1m_science/{day.year:04d}/{day.month:02d}/"
    )


def _filename_pattern(satellite: int, day: date) -> re.Pattern[str]:
    return re.compile(
        rf"sci_xrsf-l2-avg1m_g{satellite:02d}_d{day:%Y%m%d}_[A-Za-z0-9._-]+\.nc",
        re.IGNORECASE,
    )


def _request_with_retries(
    session: Any,
    url: str,
    *,
    timeout_s: float,
    retries: int,
    stream: bool = False,
):
    last_error: Exception | None = None
    for _attempt in range(max(0, int(retries)) + 1):
        try:
            response = session.get(url, timeout=timeout_s, stream=stream)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
    if _is_connection_failure(last_error):
        raise GOESConnectionError(
            "Could not connect to the official NOAA/NCEI GOES XRS archive. "
            f"Check the internet connection and try again. URL: {url}"
        ) from last_error
    raise GOESDownloadError(f"Failed to retrieve {url}: {last_error}") from last_error


def _is_connection_failure(error: Exception | None) -> bool:
    """Return whether an HTTP failure indicates unavailable network access."""
    if error is None:
        return False
    if isinstance(error, (OSError, TimeoutError)):
        return True
    return any(
        cls.__name__ in {"ConnectionError", "ConnectTimeout", "ProxyError", "ReadTimeout", "SSLError", "Timeout"}
        for cls in type(error).__mro__
    )


def _download_day(
    satellite: int,
    day: date,
    *,
    cache_root: Path,
    refresh: bool,
    timeout_s: float,
    retries: int,
    session: Any,
) -> Path:
    pattern = _filename_pattern(satellite, day)
    target_dir = cache_root / f"goes{satellite:02d}" / f"{day.year:04d}" / f"{day.month:02d}"
    cached = sorted(path for path in target_dir.glob("*.nc") if pattern.fullmatch(path.name))
    if cached and not refresh:
        try:
            _load_netcdf_path(cached[-1])
            return cached[-1]
        except GOESDataError:
            pass

    directory_url = _archive_directory(satellite, day)
    listing = _request_with_retries(
        session, directory_url, timeout_s=timeout_s, retries=retries
    ).text
    names = sorted(set(pattern.findall(listing)))
    if not names:
        raise GOESDownloadError(
            f"No science-quality one-minute GOES-{satellite} XRS file found for {day}."
        )
    filename = names[-1]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    response = _request_with_retries(
        session,
        urljoin(directory_url, filename),
        timeout_s=timeout_s,
        retries=retries,
        stream=True,
    )
    temporary = target.with_suffix(target.suffix + ".part")
    try:
        with temporary.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1_048_576):
                if chunk:
                    handle.write(chunk)
        temporary.replace(target)
        _load_netcdf_path(target)
    except Exception as exc:
        if temporary.exists():
            temporary.unlink()
        if isinstance(exc, GOESDataError):
            raise GOESDownloadError(f"Downloaded GOES file failed validation: {target}") from exc
        raise
    return target


def _days_inclusive(start: datetime, end: datetime) -> list[date]:
    current = start.date()
    output = []
    while current <= end.date():
        output.append(current)
        current += timedelta(days=1)
    return output


def _validate_requested_coverage(
    data: GOESXRayData,
    start: datetime,
    end: datetime,
    *,
    tolerance_s: float = 90.0,
) -> None:
    """Reject files that do not span the requested one-minute-data window."""
    times = np.asarray(data.time_utc, dtype="datetime64[ns]")
    start_value = np.datetime64(start.replace(tzinfo=None), "ns")
    end_value = np.datetime64(end.replace(tzinfo=None), "ns")
    tolerance = np.timedelta64(int(round(tolerance_s * 1_000_000_000)), "ns")
    if times.min() > start_value + tolerance or times.max() < end_value - tolerance:
        raise GOESDataError("GOES XRS files do not cover the requested UTC interval.")


def fetch_goes_xray(
    start_utc: datetime,
    end_utc: datetime,
    *,
    satellite_numbers: Sequence[int] | int | None = None,
    cache_dir: str | Path | None = None,
    refresh: bool = False,
    timeout_s: float = 30.0,
    retries: int = 2,
    progress_cb: Callable[[int | None, str], None] | None = None,
) -> GOESXRayData:
    """Fetch official science-quality one-minute XRS data from NCEI."""
    start = _ensure_utc(start_utc)
    end = _ensure_utc(end_utc)
    if end <= start:
        raise ValueError("end_utc must be later than start_utc")
    if timeout_s <= 0 or retries < 0:
        raise ValueError("timeout_s must be > 0 and retries must be >= 0")
    if satellite_numbers is None:
        satellites = preferred_goes_satellite_numbers(start)
    elif isinstance(satellite_numbers, int):
        satellites = (int(satellite_numbers),)
    else:
        satellites = tuple(dict.fromkeys(int(item) for item in satellite_numbers if int(item) > 0))
    if not satellites:
        raise ValueError("satellite_numbers must contain at least one positive number")
    try:
        import requests
    except ImportError as exc:
        raise ImportError(
            "Automatic GOES retrieval requires: pip install 'ecallistolib[goes]'. "
            "Restart Python or the Jupyter kernel after installation."
        ) from exc
    _import_netcdf4()

    cache_root = _cache_root(cache_dir)
    candidates: list[GOESXRayData] = []
    errors: list[str] = []
    connection_errors: list[str] = []
    with requests.Session() as session:
        for index, satellite in enumerate(satellites):
            if progress_cb is not None:
                progress_cb(
                    int(100 * index / max(1, len(satellites))),
                    f"Searching GOES-{satellite} science-quality XRS...",
                )
            try:
                paths = [
                    _download_day(
                        satellite,
                        day,
                        cache_root=cache_root,
                        refresh=refresh,
                        timeout_s=timeout_s,
                        retries=retries,
                        session=session,
                    )
                    for day in _days_inclusive(start, end)
                ]
                loaded = load_goes_xray(paths)
                _validate_requested_coverage(loaded, start, end)
                candidate = loaded.between(start, end)
                candidate = GOESXRayData(
                    candidate.time_utc,
                    candidate.xrsa_flux_wm2,
                    candidate.xrsb_flux_wm2,
                    satellite,
                    candidate.sources,
                    {
                        **candidate.meta,
                        "archive": "NCEI science-quality avg1m",
                        "requested_start_utc": start,
                        "requested_end_utc": end,
                        "cache_dir": str(cache_root),
                    },
                )
                candidates.append(candidate)
            except GOESConnectionError as exc:
                message = f"GOES-{satellite}: {exc}"
                errors.append(message)
                connection_errors.append(message)
            except (GOESDownloadError, GOESDataError) as exc:
                errors.append(f"GOES-{satellite}: {exc}")
    if not candidates:
        details = "; ".join(errors[:6])
        if connection_errors and len(connection_errors) == len(errors):
            raise GOESConnectionError(
                "Could not connect to the official NOAA/NCEI GOES XRS archive. "
                "An internet connection is required when the requested files are not "
                "already cached. Check the connection and try again."
            )
        raise GOESDownloadError(
            "No usable science-quality GOES XRS data were found for the requested interval. "
            + details
        )

    def score(item: GOESXRayData) -> tuple[int, int, int]:
        finite_by_sample = np.zeros(item.time_utc.size, dtype=bool)
        for channel in item.available_channels:
            finite_by_sample |= np.isfinite(item.flux(channel))
        valid = sum(
            int(np.count_nonzero(np.isfinite(item.flux(channel))))
            for channel in item.available_channels
        )
        return int(np.count_nonzero(finite_by_sample)), len(item.available_channels), valid

    result = max(candidates, key=score)
    if progress_cb is not None:
        progress_cb(100, f"Loaded GOES-{result.satellite_number} XRS.")
    return result


def fetch_goes_for_spectrum(ds: DynamicSpectrum, **kwargs: Any) -> GOESXRayData:
    """Fetch GOES XRS data for a spectrum's exact absolute time window."""
    if ds.start_datetime is None:
        raise GOESDataError("DynamicSpectrum has no absolute observation_start metadata.")
    if ds.time_s.size == 0:
        raise GOESDataError("DynamicSpectrum has an empty time axis.")
    start = ds.start_datetime + timedelta(seconds=float(np.nanmin(ds.time_s)))
    end = ds.start_datetime + timedelta(seconds=float(np.nanmax(ds.time_s)))
    return fetch_goes_xray(start, end, **kwargs)

"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping

import numpy as np

from .combine import _combine_frequency_impl, _frequency_step
from .exceptions import InvalidFilenameError, WorkflowError
from .io import parse_callisto_filename, read_fits
from .models import DynamicSpectrum


@dataclass(frozen=True, order=True)
class SpectrumGroupKey:
    """Stable key for one station on one UTC observation day."""

    station: str
    utc_date: date

    def __str__(self) -> str:
        return f"{self.station}/{self.utc_date.isoformat()}"


@dataclass(frozen=True)
class SpectrumCollection:
    """Immutable collection returned by :func:`load_spectra`."""

    groups: Mapping[SpectrumGroupKey, DynamicSpectrum]
    sources: tuple[Path, ...] = ()
    meta: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "groups", MappingProxyType(dict(self.groups)))
        object.__setattr__(self, "sources", tuple(Path(path) for path in self.sources))
        object.__setattr__(self, "meta", MappingProxyType(dict(self.meta)))

    def __len__(self) -> int:
        return len(self.groups)

    def __iter__(self):
        return iter(self.groups)

    def __getitem__(self, key: SpectrumGroupKey) -> DynamicSpectrum:
        return self.groups[key]

    def by_station(self, station: str) -> Mapping[SpectrumGroupKey, DynamicSpectrum]:
        """Return all station/day groups matching ``station``."""
        station_upper = str(station).upper()
        return MappingProxyType(
            {
                key: spectrum
                for key, spectrum in self.groups.items()
                if key.station.upper() == station_upper
            }
        )

    def single(self, station: str | None = None, utc_date: date | None = None) -> DynamicSpectrum:
        """Return one unambiguous spectrum or raise a helpful selection error."""
        matches = [
            spectrum
            for key, spectrum in self.groups.items()
            if (station is None or key.station.upper() == station.upper())
            and (utc_date is None or key.utc_date == utc_date)
        ]
        if len(matches) != 1:
            raise WorkflowError(
                f"Expected exactly one matching spectrum, found {len(matches)}; "
                "select a station and UTC date explicitly."
            )
        return matches[0]

    def apply(
        self,
        processor: Callable[..., DynamicSpectrum],
        /,
        **kwargs: Any,
    ) -> "SpectrumCollection":
        """Apply an immutable spectrum processor to every group."""
        processed: dict[SpectrumGroupKey, DynamicSpectrum] = {}
        for key, spectrum in self.groups.items():
            result = processor(spectrum, **kwargs)
            if not isinstance(result, DynamicSpectrum):
                raise TypeError("SpectrumCollection processors must return DynamicSpectrum objects.")
            processed[key] = result
        meta = dict(self.meta)
        meta["last_processor"] = getattr(processor, "__name__", processor.__class__.__name__)
        return SpectrumCollection(processed, sources=self.sources, meta=meta)

    def fetch_goes(self, key: SpectrumGroupKey, **kwargs: Any):
        """Explicitly fetch GOES data for one group without mutating the collection."""
        from .goes import fetch_goes_for_spectrum

        return fetch_goes_for_spectrum(self.groups[key], **kwargs)

    def plot(self, key: SpectrumGroupKey, *, goes: Any = None, **kwargs: Any):
        """Plot one group, optionally with already-loaded GOES data."""
        if goes is None:
            from .plotting import plot_dynamic_spectrum

            return plot_dynamic_spectrum(self.groups[key], **kwargs)
        from .plotting import plot_spectrum_with_goes

        return plot_spectrum_with_goes(self.groups[key], goes, **kwargs)

    def plot_with_goes(self, key: SpectrumGroupKey, *, goes: Any = None, **kwargs: Any):
        """Plot one group with supplied or automatically retrieved GOES XRS data."""
        from .plotting import plot_spectrum_with_goes

        return plot_spectrum_with_goes(self.groups[key], goes, **kwargs)


def _observation_date(ds: DynamicSpectrum, fallback: date) -> date:
    start = ds.start_datetime
    return start.date() if start is not None else fallback


def _regrid_spectrum(ds: DynamicSpectrum, target_desc: np.ndarray) -> np.ndarray:
    """Nearest-channel regrid with NaNs outside the spectrum's coverage."""
    target_asc = np.asarray(target_desc, dtype=float)[::-1]
    freqs = np.asarray(ds.freqs_mhz, dtype=float)
    data = np.asarray(ds.data, dtype=float)
    if freqs.size > 1 and float(np.nanmedian(np.diff(freqs))) < 0.0:
        freqs = freqs[::-1]
        data = data[::-1, :]
    output = np.full((target_asc.size, ds.n_time), np.nan, dtype=float)
    step = _frequency_step(target_asc, default=1.0)
    covered = (target_asc >= float(np.nanmin(freqs)) - 0.25 * step) & (
        target_asc <= float(np.nanmax(freqs)) + 0.25 * step
    )
    if np.any(covered):
        positions = (
            np.zeros(int(np.count_nonzero(covered)), dtype=int)
            if freqs.size == 1
            else np.searchsorted(0.5 * (freqs[:-1] + freqs[1:]), target_asc[covered], side="right")
        )
        output[covered, :] = data[positions, :]
    return output[::-1, :]


def _combine_station_day(
    entries: list[tuple[Path, Any, DynamicSpectrum]],
    *,
    gap_fill: str,
    overlap_policy: str,
    overlap_connection_mhz: float | None,
    time_atol: float,
) -> DynamicSpectrum:
    by_timestamp: dict[str, list[tuple[Path, Any, DynamicSpectrum]]] = {}
    all_focuses = {parts.focus for _path, parts, _ds in entries}
    for item in entries:
        by_timestamp.setdefault(item[1].time_hhmmss, []).append(item)

    segments: list[tuple[datetime, DynamicSpectrum, tuple[str, ...], tuple[str, ...]]] = []
    loaded = {path: ds for path, _parts, ds in entries}
    for timestamp, timestamp_entries in sorted(by_timestamp.items()):
        paths = [item[0] for item in timestamp_entries]
        present = tuple(sorted(item[1].focus for item in timestamp_entries))
        missing = tuple(sorted(all_focuses.difference(present)))
        if len(paths) > 1:
            spectrum = _combine_frequency_impl(
                paths,
                time_atol=time_atol,
                gap_fill=gap_fill,
                overlap_policy=overlap_policy,
                overlap_connection_mhz=overlap_connection_mhz,
                loaded=loaded,
            )
        else:
            spectrum = timestamp_entries[0][2]
        if spectrum.start_datetime is None:
            parts = timestamp_entries[0][1]
            observed_at = datetime.strptime(
                f"{parts.date_yyyymmdd}{timestamp}", "%Y%m%d%H%M%S"
            ).replace(tzinfo=timezone.utc)
        else:
            observed_at = spectrum.start_datetime
        segments.append((observed_at, spectrum, present, missing))

    min_freq = min(float(np.nanmin(item[1].freqs_mhz)) for item in segments)
    max_freq = max(float(np.nanmax(item[1].freqs_mhz)) for item in segments)
    step = min(_frequency_step(item[1].freqs_mhz, default=1.0) for item in segments)
    count = max(1, int(round((max_freq - min_freq) / step)))
    target_desc = np.linspace(min_freq, max_freq, count + 1, dtype=float)[::-1]

    segments.sort(key=lambda item: item[0])
    base_start = segments[0][0]
    data_parts: list[np.ndarray] = []
    time_parts: list[np.ndarray] = []
    missing_blocks: list[dict[str, Any]] = []
    segment_meta: list[dict[str, Any]] = []
    for observed_at, spectrum, present, missing in segments:
        offset = float((observed_at - base_start).total_seconds())
        regridded = _regrid_spectrum(spectrum, target_desc)
        data_parts.append(regridded)
        time_parts.append(np.asarray(spectrum.time_s, dtype=float) + offset)
        segment_meta.append(
            {
                "observation_start": observed_at,
                "sources": list(spectrum.meta.get("combined", {}).get("sources", [str(spectrum.source)])),
                "present_focuses": list(present),
                "missing_focuses": list(missing),
                "time_offset_s": offset,
            }
        )
        if missing:
            missing_blocks.append(
                {
                    "observation_start": observed_at,
                    "missing_focuses": list(missing),
                    "fill": "nan",
                }
            )

    combined_time = np.concatenate(time_parts)
    first = segments[0][1]
    meta = dict(first.meta)
    meta.update(
        {
            "observation_start": base_start,
            "observation_end": base_start + timedelta(seconds=float(np.nanmax(combined_time))),
            "ut_start_sec": (
                base_start.hour * 3600
                + base_start.minute * 60
                + base_start.second
                + base_start.microsecond / 1_000_000.0
            ),
            "combined": {
                "mode": "workflow",
                "timeline": "actual",
                "order": ["frequency", "time"],
                "sources": [str(item[0]) for item in entries],
                "frequency_step_mhz": float(target_desc[0] - target_desc[1]) if target_desc.size > 1 else step,
                "segments": segment_meta,
                "missing_focus_blocks": missing_blocks,
            },
        }
    )
    return DynamicSpectrum(
        data=np.concatenate(data_parts, axis=1),
        freqs_mhz=target_desc,
        time_s=combined_time,
        source=first.source,
        meta=meta,
    )


def load_spectra(
    paths: Iterable[str | Path],
    *,
    gap_fill: str = "background",
    overlap_policy: str = "split",
    overlap_connection_mhz: float | None = None,
    time_atol: float = 0.01,
) -> SpectrumCollection:
    """Read, group, frequency-combine, and time-combine FITS inputs once."""
    source_paths = tuple(Path(path) for path in paths)
    if not source_paths:
        raise WorkflowError("At least one FITS path is required.")

    grouped: dict[SpectrumGroupKey, list[tuple[Path, Any, DynamicSpectrum]]] = {}
    for path in source_paths:
        try:
            parts = parse_callisto_filename(path)
        except InvalidFilenameError as exc:
            raise WorkflowError(f"Cannot group {path}: {exc}") from exc
        spectrum = read_fits(path)
        fallback_date = datetime.strptime(parts.date_yyyymmdd, "%Y%m%d").date()
        key = SpectrumGroupKey(parts.station, _observation_date(spectrum, fallback_date))
        grouped.setdefault(key, []).append((path, parts, spectrum))

    results = {
        key: _combine_station_day(
            entries,
            gap_fill=gap_fill,
            overlap_policy=overlap_policy,
            overlap_connection_mhz=overlap_connection_mhz,
            time_atol=time_atol,
        )
        for key, entries in sorted(grouped.items())
    }
    return SpectrumCollection(
        results,
        sources=source_paths,
        meta={
            "grouping": "station_utc_day",
            "read_count": len(source_paths),
            "gap_fill": gap_fill,
            "overlap_policy": overlap_policy,
        },
    )

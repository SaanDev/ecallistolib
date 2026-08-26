"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import re
from typing import Any, Iterable, Literal, Mapping, Sequence

import numpy as np

from .exceptions import CombineError, InvalidFITSError, InvalidFilenameError
from .io import parse_callisto_filename, read_fits
from .models import DynamicSpectrum


FREQUENCY_ALIGN_ATOL_MHZ = 1e-3
HEADER_RANGE_TOL_FRACTION = 0.5
GRID_ALIGN_TOL_FRACTION = 0.25
GAP_FILL_EDGE_ROWS = 4
GAP_FILL_BACKGROUND_PERCENTILE = 25.0
GapFill = Literal["background", "hatched", "zero", "average"]
OverlapPolicy = Literal["split", "low", "high", "reject"]


@dataclass(frozen=True)
class FrequencyBand:
    """Description of one source band used in a frequency combination."""

    source: Path
    station: str
    date_yyyymmdd: str
    time_hhmmss: str
    focus: str
    freq_min_mhz: float
    freq_max_mhz: float
    frequency_step_mhz: float


@dataclass(frozen=True)
class FrequencySpan:
    """Gap or overlap between two frequency bands."""

    low_mhz: float
    high_mhz: float
    lower_source: Path
    higher_source: Path


@dataclass(frozen=True)
class FrequencyCombinationReport:
    """Preflight report for a prospective frequency combination."""

    bands: tuple[FrequencyBand, ...]
    gaps: tuple[FrequencySpan, ...]
    overlaps: tuple[FrequencySpan, ...]

    @property
    def has_gap(self) -> bool:
        return bool(self.gaps)

    @property
    def has_overlap(self) -> bool:
        return bool(self.overlaps)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly representation for provenance metadata."""
        return {
            "has_gap": self.has_gap,
            "has_overlap": self.has_overlap,
            "bands": [
                {
                    "source": str(item.source),
                    "station": item.station,
                    "date": item.date_yyyymmdd,
                    "time": item.time_hhmmss,
                    "focus": item.focus,
                    "freq_min_mhz": item.freq_min_mhz,
                    "freq_max_mhz": item.freq_max_mhz,
                    "frequency_step_mhz": item.frequency_step_mhz,
                }
                for item in self.bands
            ],
            "gaps": [
                {
                    "low_mhz": item.low_mhz,
                    "high_mhz": item.high_mhz,
                    "lower_source": str(item.lower_source),
                    "higher_source": str(item.higher_source),
                }
                for item in self.gaps
            ],
            "overlaps": [
                {
                    "low_mhz": item.low_mhz,
                    "high_mhz": item.high_mhz,
                    "lower_source": str(item.lower_source),
                    "higher_source": str(item.higher_source),
                }
                for item in self.overlaps
            ],
        }


def _require_observation_start(ds: DynamicSpectrum, path: str | Path) -> datetime:
    """Return the observation start datetime for actual-timeline combination."""
    observation_start = ds.start_datetime
    if observation_start is None:
        raise CombineError(
            "Actual timeline combination requires observation_start metadata "
            f"for every segment. Missing for: {path}"
        )
    return observation_start


def _normalize_frequency_paths(
    first: str | Path | Iterable[str | Path],
    second: str | Path | None,
    additional: Sequence[str | Path],
) -> list[Path]:
    if second is None and not isinstance(first, (str, Path)):
        paths = [Path(item) for item in first]
    else:
        paths = [Path(first)] if isinstance(first, (str, Path)) else [Path(item) for item in first]
        if second is not None:
            paths.append(Path(second))
        paths.extend(Path(item) for item in additional)
    return paths


def _frequency_step(freqs: np.ndarray, default: float = 0.0) -> float:
    arr = np.asarray(freqs, dtype=float).ravel()
    if arr.size < 2:
        return float(default)
    diffs = np.abs(np.diff(arr))
    diffs = diffs[np.isfinite(diffs) & (diffs > 1e-9)]
    return float(np.nanmedian(diffs)) if diffs.size else float(default)


def _orient_frequency_rows(data: np.ndarray, freqs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(data)
    freq_arr = np.asarray(freqs, dtype=float).ravel()
    if freq_arr.size > 1:
        diffs = np.diff(freq_arr)
        diffs = diffs[np.isfinite(diffs) & (np.abs(diffs) > 1e-9)]
        if diffs.size and float(np.nanmedian(diffs)) < 0.0:
            return arr[::-1, ...], freq_arr[::-1]
    return arr, freq_arr


def _normalize_focus_code(value: object) -> str:
    text = str(value or "").strip()
    tokens = re.findall(r"[A-Za-z0-9]+", text)
    ignore = {"FOCUS", "FOCUSCODE", "FOCUSID", "RECEIVER", "RECEIVERID", "RCVR", "RCVRID"}
    filtered = [token for token in tokens if token.upper() not in ignore]
    return (filtered[-1] if filtered else (tokens[-1] if tokens else text)).upper()


def _header_focus(meta: Mapping[str, Any]) -> str:
    header = meta.get("fits_header", {})
    if not isinstance(header, Mapping):
        return ""
    for key in ("FOCUS", "FOCUSID", "RECEIVER", "RECEIVERID", "RCVR", "RCVRID"):
        if key in header:
            normalized = _normalize_focus_code(header[key])
            if normalized:
                return normalized
    return ""


def _header_frequency_range(meta: Mapping[str, Any]) -> tuple[float, float] | None:
    header = meta.get("fits_header", {})
    if not isinstance(header, Mapping):
        return None
    try:
        lo = float(header["FREQMIN"])
        hi = float(header["FREQMAX"])
    except (KeyError, TypeError, ValueError):
        return None
    if not np.isfinite(lo) or not np.isfinite(hi):
        return None
    return min(lo, hi), max(lo, hi)


def _range_tolerance(step_mhz: float, fraction: float) -> float:
    return max(FREQUENCY_ALIGN_ATOL_MHZ, abs(float(step_mhz)) * fraction)


def _normalize_gap_fill(value: str) -> GapFill:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases: dict[str, GapFill] = {
        "background": "background",
        "interpolate": "background",
        "interpolated": "background",
        "synthetic": "background",
        "synthetic_background": "background",
        "hatched": "hatched",
        "hatch": "hatched",
        "blank": "hatched",
        "nan": "hatched",
        "gray_hatched": "hatched",
        "grey_hatched": "hatched",
        "zero": "zero",
        "zeros": "zero",
        "average": "average",
        "mean": "average",
        "edge_average": "average",
    }
    try:
        return aliases[text]
    except KeyError as exc:
        raise ValueError(f"Unsupported frequency gap fill mode: {value}") from exc


def _normalize_overlap_policy(value: str) -> OverlapPolicy:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases: dict[str, OverlapPolicy] = {
        "split": "split",
        "both": "split",
        "connection": "split",
        "connect": "split",
        "midpoint": "split",
        "low": "low",
        "low_band": "low",
        "prefer_low": "low",
        "keep_low": "low",
        "lower": "low",
        "high": "high",
        "high_band": "high",
        "prefer_high": "high",
        "keep_high": "high",
        "upper": "high",
        "reject": "reject",
        "none": "reject",
    }
    try:
        return aliases[text]
    except KeyError as exc:
        raise ValueError(f"Unsupported frequency overlap policy: {value}") from exc


def _frequency_report(blocks: Sequence[dict[str, Any]]) -> FrequencyCombinationReport:
    bands = tuple(
        FrequencyBand(
            source=block["path"],
            station=block["parts"].station,
            date_yyyymmdd=block["parts"].date_yyyymmdd,
            time_hhmmss=block["parts"].time_hhmmss,
            focus=block["parts"].focus,
            freq_min_mhz=float(block["freq_min"]),
            freq_max_mhz=float(block["freq_max"]),
            frequency_step_mhz=float(block["frequency_step_mhz"]),
        )
        for block in blocks
    )
    if not blocks:
        return FrequencyCombinationReport(bands=(), gaps=(), overlaps=())
    step = min(float(block["frequency_step_mhz"]) for block in blocks)
    tolerance = _range_tolerance(step, GRID_ALIGN_TOL_FRACTION)
    gaps: list[FrequencySpan] = []
    overlaps: list[FrequencySpan] = []
    active = blocks[0]
    active_high = float(active["freq_max"])
    for block in blocks[1:]:
        block_low = float(block["freq_min"])
        block_high = float(block["freq_max"])
        if block_low > active_high + tolerance:
            gaps.append(
                FrequencySpan(active_high, block_low, active["path"], block["path"])
            )
        else:
            overlap_low = max(float(active["freq_min"]), block_low)
            overlap_high = min(active_high, block_high)
            if overlap_high >= overlap_low - tolerance:
                overlaps.append(
                    FrequencySpan(overlap_low, overlap_high, active["path"], block["path"])
                )
        if block_high > active_high:
            active = block
            active_high = block_high
    return FrequencyCombinationReport(bands=bands, gaps=tuple(gaps), overlaps=tuple(overlaps))


def _load_frequency_blocks(
    paths: Sequence[Path],
    *,
    time_atol: float,
    loaded: Mapping[Path, DynamicSpectrum] | None = None,
) -> list[dict[str, Any]]:
    if len(paths) < 2:
        raise CombineError("Need at least 2 files to combine frequencies.")
    if time_atol < 0:
        raise ValueError("time_atol must be >= 0")

    blocks: list[dict[str, Any]] = []
    reference_context: tuple[str, str, str] | None = None
    reference_time: np.ndarray | None = None
    receiver_ids: set[str] = set()
    for path in paths:
        try:
            parts = parse_callisto_filename(path)
        except InvalidFilenameError as exc:
            raise CombineError(f"Invalid filename for frequency combination: {exc}") from exc
        context = (parts.station, parts.date_yyyymmdd, parts.time_hhmmss)
        if reference_context is None:
            reference_context = context
        elif context != reference_context:
            raise CombineError("Frequency combination requires same station/date/time.")

        focus = _normalize_focus_code(parts.focus)
        if focus in receiver_ids:
            raise CombineError("Frequency combination requires distinct focus values.")
        receiver_ids.add(focus)

        try:
            ds = loaded[path] if loaded is not None and path in loaded else read_fits(path)
        except (FileNotFoundError, InvalidFITSError) as exc:
            raise CombineError(f"Failed to read input FITS file: {exc}") from exc

        header_focus = _header_focus(ds.meta)
        if header_focus and header_focus != focus:
            raise CombineError(
                f"Focus code mismatch for {path.name}: filename='{focus}', header='{header_focus}'."
            )
        data, freqs = _orient_frequency_rows(ds.data, ds.freqs_mhz)
        time_s = np.asarray(ds.time_s, dtype=float).ravel()
        if freqs.size == 0 or time_s.size == 0:
            raise CombineError("Frequency and time axes cannot be empty.")
        if reference_time is None:
            reference_time = time_s
        elif reference_time.shape != time_s.shape or not np.allclose(
            reference_time, time_s, atol=time_atol, rtol=0.0
        ):
            raise CombineError("Cannot combine along frequency: time axes are not compatible.")

        step = _frequency_step(freqs)
        if not np.isfinite(step) or step <= 0.0:
            header = ds.meta.get("fits_header", {})
            try:
                step = abs(float(header.get("CDELT2", 0.0))) if isinstance(header, Mapping) else 0.0
            except (TypeError, ValueError):
                step = 0.0
        if not np.isfinite(step) or step <= 0.0:
            raise CombineError(f"Could not determine channel spacing for {path.name}.")

        axis_min, axis_max = float(np.nanmin(freqs)), float(np.nanmax(freqs))
        header_range = _header_frequency_range(ds.meta)
        if header_range is not None:
            tolerance = _range_tolerance(step, HEADER_RANGE_TOL_FRACTION)
            if abs(axis_min - header_range[0]) > tolerance or abs(axis_max - header_range[1]) > tolerance:
                raise CombineError(
                    f"Header frequency range does not match axis values for {path.name}."
                )
            freq_min, freq_max = header_range
        else:
            freq_min, freq_max = axis_min, axis_max

        blocks.append(
            {
                "path": path,
                "parts": parts,
                "ds": ds,
                "data": np.asarray(data, dtype=float),
                "freqs": np.asarray(freqs, dtype=float),
                "time": time_s,
                "freq_min": float(freq_min),
                "freq_max": float(freq_max),
                "frequency_step_mhz": float(step),
            }
        )
    blocks.sort(key=lambda item: (item["freq_min"], item["freq_max"]))
    return blocks


def describe_frequency_combination(
    first: str | Path | Iterable[str | Path],
    second: str | Path | None = None,
    *additional: str | Path,
    time_atol: float = 0.01,
) -> FrequencyCombinationReport:
    """Describe gaps, overlaps, and source bands without combining them."""
    paths = _normalize_frequency_paths(first, second, additional)
    blocks = _load_frequency_blocks(paths, time_atol=time_atol)
    return _frequency_report(blocks)


def can_combine_frequency(
    first: str | Path | Iterable[str | Path],
    second: str | Path | None = None,
    *additional: str | Path,
    time_atol: float = 0.01,
    gap_fill: str = "background",
    overlap_policy: str = "split",
    overlap_connection_mhz: float | None = None,
) -> bool:
    """Return whether all supplied bands can be frequency-combined."""
    try:
        _combine_frequency_impl(
            _normalize_frequency_paths(first, second, additional),
            time_atol=time_atol,
            gap_fill=gap_fill,
            overlap_policy=overlap_policy,
            overlap_connection_mhz=overlap_connection_mhz,
        )
    except (CombineError, FileNotFoundError, InvalidFITSError, ValueError):
        return False
    return True


def _neighbor_rows(
    data: np.ndarray,
    filled_mask: np.ndarray,
    anchor: int,
    *,
    direction: int,
    max_rows: int,
) -> np.ndarray | None:
    rows: list[np.ndarray] = []
    step = -1 if direction < 0 else 1
    idx = anchor - 1 if step < 0 else anchor
    while 0 <= idx < filled_mask.size and len(rows) < max_rows:
        if not bool(filled_mask[idx]):
            break
        rows.append(np.asarray(data[idx, :], dtype=float))
        idx += step
    if not rows:
        return None
    if step < 0:
        rows.reverse()
    return np.vstack(rows)


def _edge_background(rows: np.ndarray | None) -> np.ndarray | None:
    if rows is None:
        return None
    if rows.shape[0] == 1:
        return rows[0].astype(float, copy=True)
    return np.nanpercentile(rows, GAP_FILL_BACKGROUND_PERCENTILE, axis=0)


def _fill_frequency_gaps(
    data: np.ndarray,
    filled_mask: np.ndarray,
    freqs: np.ndarray,
    *,
    interpolate: bool,
) -> None:
    idx = 0
    while idx < filled_mask.size:
        if filled_mask[idx]:
            idx += 1
            continue
        start = idx
        while idx < filled_mask.size and not filled_mask[idx]:
            idx += 1
        end = idx
        left = _edge_background(
            _neighbor_rows(data, filled_mask, start, direction=-1, max_rows=GAP_FILL_EDGE_ROWS)
        )
        right = _edge_background(
            _neighbor_rows(data, filled_mask, end, direction=1, max_rows=GAP_FILL_EDGE_ROWS)
        )
        if left is None and right is None:
            continue
        if left is None:
            left = np.asarray(right, dtype=float).copy()
        if right is None:
            right = np.asarray(left, dtype=float).copy()
        if not interpolate:
            alphas = np.full(end - start, 0.5, dtype=float)
        elif start > 0 and end < filled_mask.size:
            span = float(freqs[end] - freqs[start - 1])
            alphas = (
                (freqs[start:end] - freqs[start - 1]) / span
                if abs(span) > 1e-12
                else np.full(end - start, 0.5, dtype=float)
            )
        else:
            count = end - start
            alphas = np.linspace(1.0 / (count + 1), count / (count + 1), count)
        data[start:end, :] = (1.0 - alphas)[:, None] * left[None, :] + alphas[:, None] * right[None, :]


def _overlap_replace_mask(
    freqs: np.ndarray,
    *,
    policy: OverlapPolicy,
    overlap_min: float,
    overlap_max: float,
    connection_mhz: float | None,
) -> np.ndarray:
    if policy == "low":
        return np.zeros(freqs.size, dtype=bool)
    if policy == "high":
        return np.ones(freqs.size, dtype=bool)
    if policy == "reject":
        raise CombineError("Frequency bands overlap or interleave; selected policy rejects overlap.")
    low, high = sorted((float(overlap_min), float(overlap_max)))
    connection = 0.5 * (low + high) if connection_mhz is None else float(connection_mhz)
    connection = min(max(connection, low), high)
    return np.asarray(freqs, dtype=float) > connection


def _combine_frequency_impl(
    paths: Sequence[Path],
    *,
    time_atol: float,
    gap_fill: str,
    overlap_policy: str,
    overlap_connection_mhz: float | None,
    loaded: Mapping[Path, DynamicSpectrum] | None = None,
) -> DynamicSpectrum:
    fill_mode = _normalize_gap_fill(gap_fill)
    overlap_mode = _normalize_overlap_policy(overlap_policy)
    if overlap_connection_mhz is not None and not np.isfinite(float(overlap_connection_mhz)):
        raise ValueError("overlap_connection_mhz must be finite")
    blocks = _load_frequency_blocks(paths, time_atol=time_atol, loaded=loaded)
    report = _frequency_report(blocks)
    if report.has_overlap and overlap_mode == "reject":
        raise CombineError("Frequency bands overlap or interleave; selected policy rejects overlap.")

    source_step = min(float(block["frequency_step_mhz"]) for block in blocks)
    overall_min = float(blocks[0]["freq_min"])
    overall_max = float(max(block["freq_max"] for block in blocks))
    span = overall_max - overall_min
    if span <= 0.0:
        raise CombineError("Combined frequency range must span more than one channel.")
    grid_count = max(1, int(round(span / source_step)))
    grid = np.linspace(overall_min, overall_max, grid_count + 1, dtype=float)
    grid_step = float(grid[1] - grid[0])
    n_time = int(blocks[0]["time"].size)
    combined = np.zeros((grid.size, n_time), dtype=float)
    filled = np.zeros(grid.size, dtype=bool)
    tolerance = _range_tolerance(grid_step, GRID_ALIGN_TOL_FRACTION)

    for block in blocks:
        freqs = np.asarray(block["freqs"], dtype=float)
        data = np.asarray(block["data"], dtype=float)
        covered = (grid >= float(block["freq_min"]) - tolerance) & (
            grid <= float(block["freq_max"]) + tolerance
        )
        if not np.any(covered):
            raise CombineError(f"Frequency channels in {block['path'].name} are outside the combined grid.")
        positions = (
            np.zeros(int(np.count_nonzero(covered)), dtype=int)
            if freqs.size == 1
            else np.searchsorted(0.5 * (freqs[:-1] + freqs[1:]), grid[covered], side="right")
        )
        target_rows = np.flatnonzero(covered)
        write = np.ones(target_rows.size, dtype=bool)
        overlapped = filled[target_rows]
        if np.any(overlapped):
            overlap_freqs = grid[target_rows[overlapped]]
            write[overlapped] = _overlap_replace_mask(
                overlap_freqs,
                policy=overlap_mode,
                overlap_min=max(float(block["freq_min"]), float(np.nanmin(overlap_freqs))),
                overlap_max=min(float(block["freq_max"]), float(np.nanmax(overlap_freqs))),
                connection_mhz=overlap_connection_mhz,
            )
        if np.any(write):
            targets = target_rows[write]
            combined[targets, :] = data[positions[write], :]
            filled[targets] = True

    gap_mask_asc = ~filled
    gap_count = int(np.count_nonzero(gap_mask_asc))
    if gap_count:
        if fill_mode == "background":
            _fill_frequency_gaps(combined, filled, grid, interpolate=True)
        elif fill_mode == "average":
            _fill_frequency_gaps(combined, filled, grid, interpolate=False)
        elif fill_mode == "hatched":
            combined[gap_mask_asc, :] = np.nan
        else:
            combined[gap_mask_asc, :] = 0.0

    first_ds = blocks[0]["ds"]
    gap_mask = gap_mask_asc[::-1] if fill_mode == "hatched" and gap_count else None
    meta = dict(first_ds.meta)
    meta["combined"] = {
        "mode": "frequency",
        "algorithm": "ecallisto_fits_analyzer_2.8.0",
        "sources": [str(block["path"]) for block in blocks],
        "frequency_step_mhz": grid_step,
        "gap_fill": fill_mode,
        "gap_row_count": gap_count,
        "gap_row_mask": gap_mask,
        "overlap_policy": overlap_mode,
        "overlap_connection_mhz": overlap_connection_mhz,
        "time_atol": float(time_atol),
        "report": report.to_dict(),
    }
    return DynamicSpectrum(
        data=combined[::-1, :],
        freqs_mhz=grid[::-1],
        time_s=np.asarray(blocks[0]["time"], dtype=float),
        source=first_ds.source,
        meta=meta,
    )


def combine_frequency(
    first: str | Path | Iterable[str | Path],
    second: str | Path | None = None,
    *additional: str | Path,
    gap_fill: str = "background",
    overlap_policy: str = "split",
    overlap_connection_mhz: float | None = None,
    time_atol: float = 0.01,
) -> DynamicSpectrum:
    """Combine two or more receiver bands on an Analyzer-compatible grid."""
    paths = _normalize_frequency_paths(first, second, additional)
    return _combine_frequency_impl(
        paths,
        time_atol=time_atol,
        gap_fill=gap_fill,
        overlap_policy=overlap_policy,
        overlap_connection_mhz=overlap_connection_mhz,
    )


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


def combine_time(
    paths: Iterable[str | Path],
    *,
    timeline: Literal["contiguous", "actual"] = "contiguous",
    normalize_segment_time: bool = False,
    freq_atol: float = 0.01,
) -> DynamicSpectrum:
    """
    Concatenate spectra along time axis (horizontal concatenation).
    Assumes all have identical frequency axis.

    Parameters
    ----------
    paths : Iterable[str | Path]
        Input FITS paths.
    timeline : {"contiguous", "actual"}
        - ``"contiguous"`` (default): place each segment immediately after the
          previous segment, ignoring gaps in observation start times.
        - ``"actual"``: preserve real offsets between segment start times using
          absolute observation timestamps from FITS headers or filenames.
    normalize_segment_time : bool
        Applies only when ``timeline="contiguous"``.
        If False (default), preserve legacy behavior by shifting each segment's
        full time axis by ``last_time + dt``. If True, normalize each segment to
        start at zero before shifting, which avoids over-shifting when a segment
        has a non-zero local start time.
    freq_atol : float
        Absolute tolerance for frequency axis compatibility checks.
    """
    paths = list(paths)
    if not paths:
        raise CombineError("At least one path is required to combine spectra in time.")
    if timeline not in {"contiguous", "actual"}:
        raise ValueError("timeline must be one of: 'contiguous', 'actual'")
    if freq_atol < 0:
        raise ValueError("freq_atol must be >= 0")
    if timeline == "actual" and normalize_segment_time:
        raise ValueError("normalize_segment_time cannot be used with timeline='actual'")

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

    data_list = [ds0.data]
    time_list = [ds0.time_s]
    freqs = ds0.freqs_mhz
    segment_offsets_s = [0.0]
    base_observation_start = ds0.start_datetime if timeline == "actual" else None
    if timeline == "actual":
        base_observation_start = _require_observation_start(ds0, paths[0])

    last_time = ds0.time_s[-1] if ds0.time_s.size > 0 else 0.0

    for p in paths[1:]:
        try:
            ds = read_fits(p)
        except (FileNotFoundError, InvalidFITSError) as e:
            raise CombineError(f"Failed to read input FITS file: {e}") from e

        if ds.time_s.size == 0:
            raise CombineError(f"Cannot combine spectrum with empty time axis: {p}")
        if ds.freqs_mhz.shape != freqs.shape or not np.allclose(ds.freqs_mhz, freqs, atol=freq_atol):
            raise CombineError("Cannot combine along time: frequency axes are not compatible.")

        if timeline == "actual":
            observation_start = _require_observation_start(ds, p)
            assert base_observation_start is not None
            start_offset_s = float((observation_start - base_observation_start).total_seconds())
            adjusted_time = ds.time_s + start_offset_s
            if adjusted_time.size > 0:
                last_time = adjusted_time[-1]
        else:
            if ds.time_s.size > 1:
                dt = float(ds.time_s[1] - ds.time_s[0])
            else:
                dt = 1.0

            shift = float(last_time + dt)
            if normalize_segment_time:
                adjusted_time = (ds.time_s - float(ds.time_s[0])) + shift
            else:
                adjusted_time = ds.time_s + shift
            start_offset_s = float(shift)
            if adjusted_time.size > 0:
                last_time = adjusted_time[-1]

        data_list.append(ds.data)
        time_list.append(adjusted_time)
        segment_offsets_s.append(start_offset_s)

    combined_data = np.concatenate(data_list, axis=1)
    combined_time = np.concatenate(time_list)

    meta = dict(ds0.meta)
    if ds0.start_datetime is not None:
        meta["observation_start"] = ds0.start_datetime
        meta["observation_end"] = ds0.start_datetime + timedelta(seconds=float(np.max(combined_time)))
        if ds0.meta.get("ut_start_sec") is not None:
            meta["ut_start_sec"] = float(ds0.meta["ut_start_sec"])
    meta["combined"] = {
        "mode": "time",
        "sources": [str(Path(p)) for p in paths],
        "timeline": timeline,
        "time_alignment": (
            "actual"
            if timeline == "actual"
            else ("normalized" if normalize_segment_time else "legacy")
        ),
        "freq_atol": float(freq_atol),
        "segment_offsets_s": segment_offsets_s,
    }
    return DynamicSpectrum(data=combined_data, freqs_mhz=freqs, time_s=combined_time, source=ds0.source, meta=meta)

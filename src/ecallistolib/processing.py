"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from .models import DynamicSpectrum


def noise_reduce_mean_clip(
    ds: DynamicSpectrum,
    clip_low: float,
    clip_high: float,
    scale: float | None = (2500.0 / 255.0 / 25.4),
) -> DynamicSpectrum:
    """
    Basic noise reduction used in your GUI:
    1) subtract mean over time for each frequency channel
    2) clip to [clip_low, clip_high]
    3) optional scaling
    """
    data = np.array(ds.data, copy=True, dtype=float)
    data = data - data.mean(axis=1, keepdims=True)
    data = np.clip(data, clip_low, clip_high)
    if scale is not None:
        data = data * float(scale)

    meta = dict(ds.meta)
    meta["noise_reduction"] = {
        "method": "mean_subtract_clip",
        "clip_low": clip_low,
        "clip_high": clip_high,
        "scale": scale,
    }
    return ds.copy_with(data=data, meta=meta)


def background_subtract(ds: DynamicSpectrum) -> DynamicSpectrum:
    """
    Subtract mean over time for each frequency channel (background subtraction only).

    This is the first step of noise reduction without clipping, useful for
    visualizing the intermediate result before applying clipping.

    Parameters
    ----------
    ds : DynamicSpectrum
        Input dynamic spectrum.

    Returns
    -------
    DynamicSpectrum
        New spectrum with background (mean per frequency) subtracted.

    Example
    -------
    >>> ds_bg = background_subtract(ds)
    >>> plot_dynamic_spectrum(ds_bg, title="Background Subtracted")
    """
    data = np.array(ds.data, copy=True, dtype=float)
    data = data - data.mean(axis=1, keepdims=True)

    meta = dict(ds.meta)
    meta["processing"] = {"method": "background_subtract"}
    return ds.copy_with(data=data, meta=meta)


def noise_reduce_median_clip(
    ds: DynamicSpectrum,
    clip_low: float,
    clip_high: float,
    scale: float | None = (2500.0 / 255.0 / 25.4),
) -> DynamicSpectrum:
    """
    Noise reduction using median subtraction and clipping.

    More robust to outliers than mean-based subtraction. Uses the same
    algorithm as noise_reduce_mean_clip but substitutes the median for
    the mean when computing the background level.

    Algorithm:
    1) Subtract median over time for each frequency channel
    2) Clip to [clip_low, clip_high]
    3) Apply optional scaling

    Parameters
    ----------
    ds : DynamicSpectrum
        Input dynamic spectrum.
    clip_low : float
        Lower clipping threshold.
    clip_high : float
        Upper clipping threshold.
    scale : float | None
        Scaling factor. Default is ~3.88 (2500/255/25.4).
        Set to None to disable scaling.

    Returns
    -------
    DynamicSpectrum
        New spectrum with noise reduced.
    """
    data = np.array(ds.data, copy=True, dtype=float)
    data = data - np.median(data, axis=1, keepdims=True)
    data = np.clip(data, clip_low, clip_high)
    if scale is not None:
        data = data * float(scale)

    meta = dict(ds.meta)
    meta["noise_reduction"] = {
        "method": "median_subtract_clip",
        "clip_low": clip_low,
        "clip_high": clip_high,
        "scale": scale,
    }
    return ds.copy_with(data=data, meta=meta)

<<<<<<< HEAD
def mitigate_rfi_mad(
    ds: DynamicSpectrum,
    threshold: float = 3.0,
) -> DynamicSpectrum:
    """
    Mitigate Radio Frequency Interference (RFI) using Median Absolute Deviation (MAD).

    Detects impulsive spikes by calculating the MAD across the time axis for each
    frequency channel. Values exceeding `threshold` times the MAD above the median
    are replaced with the median value.

    Parameters
    ----------
    ds : DynamicSpectrum
        Input dynamic spectrum.
    threshold : float
        The number of MADs above the median to consider a value an outlier.

    Returns
    -------
    DynamicSpectrum
        New spectrum with RFI mitigated.
    """
    data = np.array(ds.data, copy=True, dtype=float)

    # Calculate median along time axis for each frequency
    medians = np.median(data, axis=1, keepdims=True)

    # Calculate absolute deviation from the median
    abs_dev = np.abs(data - medians)

    # Calculate MAD (Median Absolute Deviation)
    # The factor 1.4826 makes MAD a consistent estimator of the standard deviation
    # for normally distributed data.
    mads = np.median(abs_dev, axis=1, keepdims=True) * 1.4826

    # Replace outliers with median
    # We only care about positive spikes (values much larger than median)
    # because RFI typically adds power.
    outlier_mask = (data - medians) > (threshold * mads)

    # Avoid zero division or zero MAD issues
    valid_mads = mads > 0
    # Create mask where MAD is valid AND data exceeds threshold
    final_mask = np.zeros_like(outlier_mask)
    for i in range(data.shape[0]):
        if valid_mads[i, 0]:
            final_mask[i, :] = outlier_mask[i, :]

    data[final_mask] = np.broadcast_to(medians, data.shape)[final_mask]

    meta = dict(ds.meta)
    meta["rfi_mitigation"] = {
        "method": "mad_clipping",
        "threshold": threshold,
    }
    return ds.copy_with(data=data, meta=meta)
=======

>>>>>>> origin/feature/improvements-rfi-cli-11159646905103801913


def background_subtract_frequency(ds: DynamicSpectrum) -> DynamicSpectrum:
    """
    Subtract mean over frequency for each time channel.

    This can help mitigate broad-band noise that occurs at a single time step
    across many frequencies.

    Parameters
    ----------
    ds : DynamicSpectrum
        Input dynamic spectrum.

    Returns
    -------
    DynamicSpectrum
        New spectrum with frequency-background subtracted.
    """
    data = np.array(ds.data, copy=True, dtype=float)
    data = data - data.mean(axis=0, keepdims=True)

    meta = dict(ds.meta)
    meta["processing"] = {"method": "background_subtract_frequency"}
    return ds.copy_with(data=data, meta=meta)
<<<<<<< HEAD
=======



try:
    from scipy.ndimage import median_filter as _median_filter
except Exception:  # pragma: no cover - scipy optional in isolated environments
    _median_filter = None

@dataclass(frozen=True)
class RFIResult:
    data: np.ndarray
    masked_channel_indices: list[int]

def _robust_z(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    med = np.nanmedian(arr)
    mad = np.nanmedian(np.abs(arr - med))
    if not np.isfinite(mad) or mad <= 0:
        std = np.nanstd(arr)
        if np.isfinite(std) and std > 0:
            return (arr - med) / std
        return np.where(np.abs(arr - med) > 0, np.inf, 0.0).astype(float)
    return 0.6745 * (arr - med) / mad

def _ensure_odd(v: int) -> int:
    out = max(1, int(v))
    if out % 2 == 0:
        out += 1
    return out

def _median2d(arr: np.ndarray, kernel_freq: int, kernel_time: int) -> np.ndarray:
    if _median_filter is None:
        return arr.copy()
    return _median_filter(arr, size=(_ensure_odd(kernel_freq), _ensure_odd(kernel_time)), mode="nearest")

def _mask_hot_channels(data: np.ndarray, z_thresh: float) -> list[int]:
    if data.ndim != 2 or data.shape[0] == 0:
        return []

    row_med = np.nanmedian(data, axis=1)
    row_centered = np.nanmedian(np.abs(data - row_med[:, None]), axis=1)
    score = np.abs(row_med) + row_centered
    z = _robust_z(score)
    idx = np.where(z > float(z_thresh))[0]
    return [int(i) for i in idx.tolist()]

def _repair_masked_channels(cleaned: np.ndarray, masked_indices: list[int]) -> np.ndarray:
    if cleaned.ndim != 2 or not masked_indices:
        return cleaned

    out = cleaned.copy()
    n_rows = out.shape[0]
    for idx in masked_indices:
        if idx <= 0:
            donor = 1 if n_rows > 1 else 0
        elif idx >= n_rows - 1:
            donor = n_rows - 2 if n_rows > 1 else 0
        else:
            out[idx] = 0.5 * (out[idx - 1] + out[idx + 1])
            continue

        out[idx] = out[donor]
    return out

def _percentile_clip_per_channel(data: np.ndarray, upper_percentile: float) -> np.ndarray:
    if data.ndim != 2:
        return data

    pct = float(upper_percentile)
    if pct <= 0 or pct >= 100:
        return data

    out = data.copy()
    highs = np.nanpercentile(out, pct, axis=1)
    for i in range(out.shape[0]):
        out[i] = np.minimum(out[i], highs[i])
    return out

def clean_rfi(
    data: np.ndarray,
    *,
    kernel_time: int = 3,
    kernel_freq: int = 3,
    channel_z_threshold: float = 6.0,
    percentile_clip: float = 99.5,
    enabled: bool = True,
) -> RFIResult:
    arr = np.asarray(data, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError("RFI cleaning expects 2D (freq, time) data.")
    if not enabled:
        return RFIResult(data=arr.copy(), masked_channel_indices=[])

    filtered = _median2d(arr, kernel_freq=kernel_freq, kernel_time=kernel_time)
    masked = _mask_hot_channels(arr, z_thresh=float(channel_z_threshold))
    repaired = _repair_masked_channels(filtered, masked)
    clipped = _percentile_clip_per_channel(repaired, upper_percentile=float(percentile_clip))

    return RFIResult(data=np.asarray(clipped, dtype=np.float32), masked_channel_indices=masked)

def mitigate_rfi(
    ds: DynamicSpectrum,
    kernel_time: int = 3,
    kernel_freq: int = 3,
    channel_z_threshold: float = 6.0,
    percentile_clip: float = 99.5,
) -> DynamicSpectrum:
    result = clean_rfi(
        ds.data,
        kernel_time=kernel_time,
        kernel_freq=kernel_freq,
        channel_z_threshold=channel_z_threshold,
        percentile_clip=percentile_clip,
        enabled=True
    )
    meta = dict(ds.meta)
    meta["rfi_mitigation"] = {
        "method": "clean_rfi",
        "kernel_time": kernel_time,
        "kernel_freq": kernel_freq,
        "channel_z_threshold": channel_z_threshold,
        "percentile_clip": percentile_clip,
        "masked_channel_indices": result.masked_channel_indices,
    }
    return ds.copy_with(data=result.data, meta=meta)
>>>>>>> origin/feature/improvements-rfi-cli-11159646905103801913

"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.3
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union

import numpy as np

from .exceptions import CropError
from .models import DynamicSpectrum


def crop_frequency(
    ds: DynamicSpectrum,
    freq_min: Optional[float] = None,
    freq_max: Optional[float] = None,
) -> DynamicSpectrum:
    """
    Crop a DynamicSpectrum to a frequency range.

    Parameters
    ----------
    ds : DynamicSpectrum
        Input spectrum to crop.
    freq_min : float, optional
        Minimum frequency in MHz (inclusive). If None, uses the minimum frequency in the data.
    freq_max : float, optional
        Maximum frequency in MHz (inclusive). If None, uses the maximum frequency in the data.

    Returns
    -------
    DynamicSpectrum
        Cropped spectrum containing only frequencies in [freq_min, freq_max].

    Raises
    ------
    CropError
        If the frequency range is invalid or results in empty data.
    """
    freqs = ds.freqs_mhz
    actual_min, actual_max = float(freqs.min()), float(freqs.max())

    if freq_min is None:
        freq_min = actual_min
    if freq_max is None:
        freq_max = actual_max

    if freq_min > freq_max:
        raise CropError(f"freq_min ({freq_min}) must be <= freq_max ({freq_max})")

    # Find indices within range
    mask = (freqs >= freq_min) & (freqs <= freq_max)

    if not mask.any():
        raise CropError(
            f"No frequencies in range [{freq_min}, {freq_max}] MHz. "
            f"Data range is [{actual_min}, {actual_max}] MHz."
        )

    indices = np.where(mask)[0]
    cropped_data = ds.data[indices, :]
    cropped_freqs = freqs[indices]

    meta = dict(ds.meta)
    meta["cropped"] = meta.get("cropped", {})
    meta["cropped"]["frequency"] = {"min": freq_min, "max": freq_max}

    return ds.copy_with(data=cropped_data, freqs_mhz=cropped_freqs, meta=meta)


def crop_time(
    ds: DynamicSpectrum,
    time_min: Optional[float] = None,
    time_max: Optional[float] = None,
) -> DynamicSpectrum:
    """
    Crop a DynamicSpectrum to a time range.

    Parameters
    ----------
    ds : DynamicSpectrum
        Input spectrum to crop.
    time_min : float, optional
        Minimum time in seconds (inclusive). If None, uses the minimum time in the data.
    time_max : float, optional
        Maximum time in seconds (inclusive). If None, uses the maximum time in the data.

    Returns
    -------
    DynamicSpectrum
        Cropped spectrum containing only times in [time_min, time_max].

    Raises
    ------
    CropError
        If the time range is invalid or results in empty data.
    """
    times = ds.time_s
    actual_min, actual_max = float(times.min()), float(times.max())

    if time_min is None:
        time_min = actual_min
    if time_max is None:
        time_max = actual_max

    if time_min > time_max:
        raise CropError(f"time_min ({time_min}) must be <= time_max ({time_max})")

    # Find indices within range
    mask = (times >= time_min) & (times <= time_max)

    if not mask.any():
        raise CropError(
            f"No times in range [{time_min}, {time_max}] s. "
            f"Data range is [{actual_min}, {actual_max}] s."
        )

    indices = np.where(mask)[0]
    cropped_data = ds.data[:, indices]
    cropped_times = times[indices]

    meta = dict(ds.meta)
    meta["cropped"] = meta.get("cropped", {})
    meta["cropped"]["time"] = {"min": time_min, "max": time_max}

    return ds.copy_with(data=cropped_data, time_s=cropped_times, meta=meta)


def crop(
    ds: DynamicSpectrum,
    freq_range: Optional[Tuple[Optional[float], Optional[float]]] = None,
    time_range: Optional[Tuple[Optional[float], Optional[float]]] = None,
) -> DynamicSpectrum:
    """
    Crop a DynamicSpectrum to specified frequency and/or time ranges.

    Parameters
    ----------
    ds : DynamicSpectrum
        Input spectrum to crop.
    freq_range : tuple of (min, max), optional
        Frequency range in MHz. Use None for either bound to keep original.
    time_range : tuple of (min, max), optional
        Time range in seconds. Use None for either bound to keep original.

    Returns
    -------
    DynamicSpectrum
        Cropped spectrum.

    Examples
    --------
    >>> # Crop to 100-200 MHz
    >>> cropped = crop(ds, freq_range=(100, 200))

    >>> # Crop to first 60 seconds
    >>> cropped = crop(ds, time_range=(0, 60))

    >>> # Crop both axes
    >>> cropped = crop(ds, freq_range=(100, 200), time_range=(0, 60))
    """
    result = ds

    if freq_range is not None:
        freq_min, freq_max = freq_range
        result = crop_frequency(result, freq_min, freq_max)

    if time_range is not None:
        time_min, time_max = time_range
        result = crop_time(result, time_min, time_max)

    return result


def slice_by_index(
    ds: DynamicSpectrum,
    freq_slice: Optional[slice] = None,
    time_slice: Optional[slice] = None,
) -> DynamicSpectrum:
    """
    Slice a DynamicSpectrum by array indices.

    Parameters
    ----------
    ds : DynamicSpectrum
        Input spectrum to slice.
    freq_slice : slice, optional
        Slice object for frequency axis. E.g., slice(0, 100) for first 100 channels.
    time_slice : slice, optional
        Slice object for time axis. E.g., slice(0, 500) for first 500 samples.

    Returns
    -------
    DynamicSpectrum
        Sliced spectrum.

    Examples
    --------
    >>> # Get first 100 frequency channels
    >>> sliced = slice_by_index(ds, freq_slice=slice(0, 100))

    >>> # Get every other time sample
    >>> sliced = slice_by_index(ds, time_slice=slice(None, None, 2))
    """
    if freq_slice is None:
        freq_slice = slice(None)
    if time_slice is None:
        time_slice = slice(None)

    sliced_data = ds.data[freq_slice, time_slice]
    sliced_freqs = ds.freqs_mhz[freq_slice]
    sliced_times = ds.time_s[time_slice]

    if sliced_data.size == 0:
        raise CropError("Slice resulted in empty data array")

    meta = dict(ds.meta)
    meta["sliced"] = {"freq_slice": str(freq_slice), "time_slice": str(time_slice)}

    return ds.copy_with(data=sliced_data, freqs_mhz=sliced_freqs, time_s=sliced_times, meta=meta)

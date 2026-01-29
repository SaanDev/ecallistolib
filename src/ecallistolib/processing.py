"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.3
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

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

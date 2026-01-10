from __future__ import annotations

import numpy as np

from .models import DynamicSpectrum


def noise_reduce_mean_clip(
    ds: DynamicSpectrum,
    clip_low: float = -5.0,
    clip_high: float = 20.0,
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

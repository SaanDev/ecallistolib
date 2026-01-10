from __future__ import annotations

from typing import Optional

import matplotlib.pyplot as plt

from .models import DynamicSpectrum


def plot_dynamic_spectrum(
    ds: DynamicSpectrum,
    title: str = "Dynamic Spectrum",
    cmap: str = "inferno",
    ax: Optional[plt.Axes] = None,
    show_colorbar: bool = True,
):
    """
    Plot a DynamicSpectrum using matplotlib.
    Returns (fig, ax, im).
    """
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    extent = [float(ds.time_s[0]), float(ds.time_s[-1]), float(ds.freqs_mhz[-1]), float(ds.freqs_mhz[0])]
    im = ax.imshow(ds.data, aspect="auto", extent=extent, cmap=cmap)
    ax.set_title(title)
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Frequency [MHz]")

    if show_colorbar:
        fig.colorbar(im, ax=ax)

    return fig, ax, im

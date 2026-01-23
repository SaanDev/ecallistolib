"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Optional

import matplotlib.pyplot as plt
import numpy as np

from .models import DynamicSpectrum

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.image import AxesImage


@dataclass
class TimeAxisConverter:
    """
    Convert between elapsed seconds and UT (Universal Time) strings.

    This class helps convert time values between the seconds-from-start format
    used internally by DynamicSpectrum and human-readable UT time strings.

    Parameters
    ----------
    ut_start_sec : float
        UT observation start time in seconds since midnight (00:00:00).

    Example
    -------
    >>> converter = TimeAxisConverter(ut_start_sec=43200.0)  # 12:00:00
    >>> converter.seconds_to_ut(100)
    '12:01:40'
    >>> converter.ut_to_seconds("12:01:40")
    100.0
    """

    ut_start_sec: float

    def seconds_to_ut(self, seconds: float) -> str:
        """
        Convert elapsed seconds to UT time string (HH:MM:SS).

        Parameters
        ----------
        seconds : float
            Elapsed seconds from observation start.

        Returns
        -------
        str
            UT time string in HH:MM:SS format.
        """
        total_sec = self.ut_start_sec + seconds
        hours = int(total_sec // 3600) % 24
        minutes = int((total_sec % 3600) // 60)
        secs = int(total_sec % 60)
        return f"{hours:02d}:{minutes:02d}"

    def ut_to_seconds(self, ut_str: str) -> float:
        """
        Convert UT time string (HH:MM:SS) to elapsed seconds.

        Parameters
        ----------
        ut_str : str
            UT time string in HH:MM:SS or HH:MM:SS.sss format.

        Returns
        -------
        float
            Elapsed seconds from observation start.
        """
        parts = ut_str.split(":")
        hh, mm = int(parts[0]), int(parts[1])
        ss = float(parts[2]) if len(parts) > 2 else 0.0
        total_sec = hh * 3600 + mm * 60 + ss
        return total_sec - self.ut_start_sec

    @classmethod
    def from_dynamic_spectrum(cls, ds: DynamicSpectrum) -> "TimeAxisConverter":
        """
        Create a TimeAxisConverter from a DynamicSpectrum's metadata.

        Parameters
        ----------
        ds : DynamicSpectrum
            The dynamic spectrum containing ut_start_sec in its metadata.

        Returns
        -------
        TimeAxisConverter
            Converter initialized with the spectrum's UT start time.

        Raises
        ------
        ValueError
            If ut_start_sec is not available in the spectrum's metadata.
        """
        ut_start = ds.meta.get("ut_start_sec")
        if ut_start is None:
            raise ValueError(
                "DynamicSpectrum does not have 'ut_start_sec' in metadata. "
                "This is typically read from the TIME-OBS header in FITS files."
            )
        return cls(ut_start_sec=float(ut_start))


def _compute_extent(
    ds: DynamicSpectrum,
    time_format: Literal["seconds", "ut"],
) -> tuple[list[float], Optional[TimeAxisConverter]]:
    """Compute imshow extent and optional time converter."""
    converter = None
    if time_format == "ut":
        converter = TimeAxisConverter.from_dynamic_spectrum(ds)
        t_start = ds.time_s[0] + converter.ut_start_sec
        t_end = ds.time_s[-1] + converter.ut_start_sec
    else:
        t_start = float(ds.time_s[0])
        t_end = float(ds.time_s[-1])

    extent = [t_start, t_end, float(ds.freqs_mhz[-1]), float(ds.freqs_mhz[0])]
    return extent, converter


def _format_time_axis(
    ax: Axes,
    converter: Optional[TimeAxisConverter],
    time_format: Literal["seconds", "ut"],
) -> None:
    """Format the time axis labels."""
    if time_format == "ut" and converter is not None:
        ax.set_xlabel("Time [UT]")
        # Format x-tick labels as UT times
        from matplotlib.ticker import FuncFormatter

        def fmt(x, pos):
            return converter.seconds_to_ut(x - converter.ut_start_sec)

        ax.xaxis.set_major_formatter(FuncFormatter(fmt))
    else:
        ax.set_xlabel("Time [s]")


def _get_filename_title(ds: DynamicSpectrum, suffix: str) -> str:
    """Generate plot title from DynamicSpectrum source filename."""
    if ds.source is not None:
        filename = ds.source.stem  # Get filename without extension
        return f"{filename}_{suffix}"
    return suffix


def plot_raw_spectrum(
    ds: DynamicSpectrum,
    title: str | None = None,
    cmap: str = "viridis",
    figsize: tuple[float, float] | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    ax: Optional[plt.Axes] = None,
    show_colorbar: bool = True,
    time_format: Literal["seconds", "ut"] = "seconds",
    **imshow_kwargs,
) -> tuple["Figure", "Axes", "AxesImage"]:
    """
    Plot a raw DynamicSpectrum without any processing.

    Parameters
    ----------
    ds : DynamicSpectrum
        The dynamic spectrum to plot.
    title : str
        Plot title.
    cmap : str
        Matplotlib colormap name.
    figsize : tuple[float, float] | None
        Figure size as (width, height) in inches. Ignored if ax is provided.
    vmin : float | None
        Minimum value for colormap normalization.
    vmax : float | None
        Maximum value for colormap normalization.
    ax : plt.Axes | None
        Existing axes to plot on. If None, creates a new figure.
    show_colorbar : bool
        Whether to show a colorbar.
    time_format : {"seconds", "ut"}
        Format for the time axis. "seconds" shows elapsed seconds,
        "ut" shows Universal Time (requires ut_start_sec in metadata).
    **imshow_kwargs
        Additional keyword arguments passed to matplotlib's imshow().

    Returns
    -------
    tuple[Figure, Axes, AxesImage]
        The figure, axes, and image objects.

    Example
    -------
    >>> ds = read_fits("spectrum.fit.gz")
    >>> fig, ax, im = plot_raw_spectrum(ds, figsize=(12, 6), cmap="plasma")
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    extent, converter = _compute_extent(ds, time_format)

    im = ax.imshow(
        ds.data,
        aspect="auto",
        extent=extent,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        **imshow_kwargs,
    )
    # Use filename-based title if not provided
    if title is None:
        title = _get_filename_title(ds, "raw")
    ax.set_title(title)
    _format_time_axis(ax, converter, time_format)
    ax.set_ylabel("Frequency [MHz]")

    if show_colorbar:
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Intensity [DN]")

    return fig, ax, im


def plot_dynamic_spectrum(
    ds: DynamicSpectrum,
    title: str | None = None,
    cmap: str = "inferno",
    figsize: tuple[float, float] | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    ax: Optional[plt.Axes] = None,
    show_colorbar: bool = True,
    time_format: Literal["seconds", "ut"] = "seconds",
    **imshow_kwargs,
) -> tuple["Figure", "Axes", "AxesImage"]:
    """
    Plot a DynamicSpectrum using matplotlib with full customization.

    This is the main plotting function with support for all matplotlib
    imshow parameters including colormap clipping (vmin/vmax), figure size,
    and custom time axis formats.

    Parameters
    ----------
    ds : DynamicSpectrum
        The dynamic spectrum to plot.
    title : str
        Plot title.
    cmap : str
        Matplotlib colormap name (e.g., "inferno", "viridis", "magma", "plasma").
    figsize : tuple[float, float] | None
        Figure size as (width, height) in inches. Ignored if ax is provided.
    vmin : float | None
        Minimum value for colormap normalization (clipping lower bound).
    vmax : float | None
        Maximum value for colormap normalization (clipping upper bound).
    ax : plt.Axes | None
        Existing axes to plot on. If None, creates a new figure.
    show_colorbar : bool
        Whether to show a colorbar.
    time_format : {"seconds", "ut"}
        Format for the time axis. "seconds" shows elapsed seconds,
        "ut" shows Universal Time (requires ut_start_sec in metadata).
    **imshow_kwargs
        Additional keyword arguments passed to matplotlib's imshow().
        Common options include:
        - interpolation: str ("nearest", "bilinear", "bicubic", etc.)
        - origin: str ("upper", "lower")
        - alpha: float (transparency)
        - norm: matplotlib.colors.Normalize (custom normalization)

    Returns
    -------
    tuple[Figure, Axes, AxesImage]
        The figure, axes, and image objects.

    Example
    -------
    >>> ds = read_fits("spectrum.fit.gz")
    >>> ds_reduced = noise_reduce_mean_clip(ds)
    >>> fig, ax, im = plot_dynamic_spectrum(
    ...     ds_reduced,
    ...     title="Noise Reduced",
    ...     vmin=-5, vmax=20,
    ...     figsize=(12, 6),
    ...     cmap="magma"
    ... )
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    extent, converter = _compute_extent(ds, time_format)

    im = ax.imshow(
        ds.data,
        aspect="auto",
        extent=extent,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        **imshow_kwargs,
    )
    # Use filename-based title if not provided
    if title is None:
        title = _get_filename_title(ds, "dynamic_spectrum")
    ax.set_title(title)
    _format_time_axis(ax, converter, time_format)
    ax.set_ylabel("Frequency [MHz]")

    if show_colorbar:
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Intensity [DN]")

    return fig, ax, im


def plot_background_subtracted(
    ds: DynamicSpectrum,
    title: str | None = None,
    cmap: str = "jet",
    figsize: tuple[float, float] | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
    ax: Optional[plt.Axes] = None,
    show_colorbar: bool = True,
    time_format: Literal["seconds", "ut"] = "seconds",
    **imshow_kwargs,
) -> tuple["Figure", "Axes", "AxesImage"]:
    """
    Plot a DynamicSpectrum after background subtraction (before clipping).

    This is a convenience function that applies background subtraction
    (mean removal per frequency channel) and plots the result. This shows
    the intermediate step before clipping is applied in noise reduction.

    Parameters
    ----------
    ds : DynamicSpectrum
        The raw dynamic spectrum (will be background-subtracted internally).
    title : str
        Plot title.
    cmap : str
        Matplotlib colormap name. Default is "RdBu_r" (diverging colormap)
        which works well for showing positive/negative deviations.
    figsize : tuple[float, float] | None
        Figure size as (width, height) in inches.
    vmin : float | None
        Minimum value for colormap normalization.
    vmax : float | None
        Maximum value for colormap normalization.
    ax : plt.Axes | None
        Existing axes to plot on. If None, creates a new figure.
    show_colorbar : bool
        Whether to show a colorbar.
    time_format : {"seconds", "ut"}
        Format for the time axis.
    **imshow_kwargs
        Additional keyword arguments passed to matplotlib's imshow().

    Returns
    -------
    tuple[Figure, Axes, AxesImage]
        The figure, axes, and image objects.

    Example
    -------
    >>> ds = read_fits("spectrum.fit.gz")
    >>> fig, ax, im = plot_background_subtracted(ds, vmin=-10, vmax=30)
    """
    from .processing import background_subtract

    ds_bg = background_subtract(ds)
    # Use filename-based title if not provided
    if title is None:
        title = _get_filename_title(ds, "background_subtracted")
    return plot_dynamic_spectrum(
        ds_bg,
        title=title,
        cmap=cmap,
        figsize=figsize,
        vmin=vmin,
        vmax=vmax,
        ax=ax,
        show_colorbar=show_colorbar,
        time_format=time_format,
        **imshow_kwargs,
    )

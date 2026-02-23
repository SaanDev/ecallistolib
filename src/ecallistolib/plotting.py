"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional, cast

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
    '12:01'
    >>> converter.seconds_to_ut(100, precision="second")
    '12:01:40'
    >>> converter.ut_to_seconds("12:01:40")
    100.0
    """

    ut_start_sec: float

    def seconds_to_ut(
        self,
        seconds: float,
        precision: Literal["minute", "second"] = "minute",
    ) -> str:
        """
        Convert elapsed seconds to a UT time string.

        Parameters
        ----------
        seconds : float
            Elapsed seconds from observation start.
        precision : {"minute", "second"}
            Output precision. "minute" returns HH:MM (default), "second"
            returns HH:MM:SS.

        Returns
        -------
        str
            UT time string.
        """
        total_sec = self.ut_start_sec + seconds
        hours = int(total_sec // 3600) % 24
        minutes = int((total_sec % 3600) // 60)
        secs = int(total_sec % 60)
        if precision == "minute":
            return f"{hours:02d}:{minutes:02d}"
        if precision == "second":
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        raise ValueError("precision must be one of: 'minute', 'second'")

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
) -> tuple[tuple[float, float, float, float], Optional[TimeAxisConverter]]:
    """Compute imshow extent and optional time converter."""
    converter = None
    if time_format == "ut":
        converter = TimeAxisConverter.from_dynamic_spectrum(ds)
        t_start = ds.time_s[0] + converter.ut_start_sec
        t_end = ds.time_s[-1] + converter.ut_start_sec
    else:
        t_start = float(ds.time_s[0])
        t_end = float(ds.time_s[-1])

    extent = (t_start, t_end, float(ds.freqs_mhz[-1]), float(ds.freqs_mhz[0]))
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
            return converter.seconds_to_ut(x - converter.ut_start_sec, precision="minute")

        ax.xaxis.set_major_formatter(FuncFormatter(fmt))
    else:
        ax.set_xlabel("Time [s]")


def _get_filename_title(ds: DynamicSpectrum, suffix: str) -> str:
    """Generate plot title from DynamicSpectrum source filename."""
    if ds.source is not None:
        filename = ds.source.stem  # Get filename without extension
        # Also strip .fit if it's a double extension like .fit.gz
        if filename.endswith(".fit"):
            filename = filename[:-4]
        return f"{filename}_{suffix}"
    return suffix


def _resolve_clip_limits(
    data: np.ndarray,
    clip_low: float | None,
    clip_high: float | None,
    clip_percentiles: tuple[float, float] | None,
) -> tuple[float | None, float | None]:
    """Resolve clipping limits from explicit values or percentiles."""
    has_low = clip_low is not None
    has_high = clip_high is not None
    if has_low != has_high:
        raise ValueError("clip_low and clip_high must be provided together.")

    if has_low and has_high:
        return float(clip_low), float(clip_high)

    if clip_percentiles is None:
        return None, None

    p_low, p_high = clip_percentiles
    if not (0 <= p_low <= 100 and 0 <= p_high <= 100):
        raise ValueError("clip_percentiles must be within [0, 100].")
    if p_low >= p_high:
        raise ValueError("clip_percentiles must satisfy low < high.")

    resolved_low, resolved_high = np.nanpercentile(data, [p_low, p_high])
    return float(resolved_low), float(resolved_high)


def _save_figure_if_requested(
    fig: Figure,
    save_path: str | Path | None,
    savefig_kwargs: dict[str, Any] | None,
) -> None:
    """Save figure when a target path is provided."""
    if save_path is None:
        return
    target = Path(save_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(target, **(savefig_kwargs or {}))


# Conversion factor for Digits to dB (pseudo-calibration)
# dB = Digits * 2500 / 256 / 25.4 = Digits * 0.384
DIGITS_TO_DB_FACTOR = 2500.0 / 256.0 / 25.4  # ~0.384


def plot_dynamic_spectrum(
    ds: DynamicSpectrum,
    process: Literal["raw", "background_subtracted", "noise_reduced"] = "raw",
    clip_low: float | None = None,
    clip_high: float | None = None,
    clip_percentiles: tuple[float, float] | None = None,
    title: str | None = None,
    cmap: str = "inferno",
    figsize: tuple[float, float] | None = None,
    ax: Optional[plt.Axes] = None,
    show_colorbar: bool = True,
    time_format: Literal["seconds", "ut"] = "seconds",
    intensity_units: Literal["digits", "dB"] = "digits",
    save_path: str | Path | None = None,
    savefig_kwargs: dict[str, Any] | None = None,
    **imshow_kwargs,
) -> tuple["Figure", "Axes", "AxesImage"]:
    """
    Plot a DynamicSpectrum with selectable processing mode.

    This is the main plotting function that supports raw, background-subtracted,
    and noise-reduced visualization modes with full matplotlib customization.

    Parameters
    ----------
    ds : DynamicSpectrum
        The dynamic spectrum to plot.
    process : {"raw", "background_subtracted", "noise_reduced"}
        Processing mode to apply before plotting:
        - "raw": Plot the original data without any processing.
        - "background_subtracted": Subtract mean over time for each frequency.
        - "noise_reduced": Apply background subtraction and clipping.
    clip_low : float | None
        Lower clipping threshold. Must be provided together with clip_high.
    clip_high : float | None
        Upper clipping threshold. Must be provided together with clip_low.
    clip_percentiles : tuple[float, float] | None
        Percentiles used to derive clipping limits when clip_low/clip_high are
        not provided. For process="noise_reduced", limits are derived from the
        background-subtracted data before clipping.
    title : str | None
        Plot title. If None, auto-generates from filename and process mode.
    cmap : str
        Matplotlib colormap name (e.g., "inferno", "viridis", "jet").
    figsize : tuple[float, float] | None
        Figure size as (width, height) in inches. Ignored if ax is provided.
    ax : plt.Axes | None
        Existing axes to plot on. If None, creates a new figure.
    show_colorbar : bool
        Whether to show a colorbar.
    time_format : {"seconds", "ut"}
        Format for the time axis. "seconds" shows elapsed seconds,
        "ut" shows Universal Time (requires ut_start_sec in metadata).
    intensity_units : {"digits", "dB"}
        Units for the intensity axis. "digits" shows raw ADU values,
        "dB" converts using dB = Digits * 0.384 (pseudo-calibration).
    save_path : str | Path | None
        Optional output path. If provided, the figure is saved before returning.
    savefig_kwargs : dict[str, Any] | None
        Optional kwargs passed to ``Figure.savefig`` when ``save_path`` is set.
    **imshow_kwargs
        Additional keyword arguments passed to matplotlib's imshow().
        Common options include:
        - interpolation: str ("nearest", "bilinear", "bicubic", etc.)
        - origin: str ("upper", "lower")
        - alpha: float (transparency)

    Returns
    -------
    tuple[Figure, Axes, AxesImage]
        The figure, axes, and image objects.

    Raises
    ------
    ValueError
        If clip bounds are invalid or process="noise_reduced" has no clip source.

    Example
    -------
    >>> ds = read_fits("spectrum.fit.gz")
    >>> # Plot raw spectrum
    >>> fig, ax, im = plot_dynamic_spectrum(ds, process="raw")
    >>> # Plot noise-reduced spectrum
    >>> fig, ax, im = plot_dynamic_spectrum(
    ...     ds, process="noise_reduced",
    ...     clip_low=-5, clip_high=20,
    ...     cmap="jet"
    ... )
    """
    from .processing import background_subtract, noise_reduce_mean_clip

    # Apply processing
    if process == "background_subtracted":
        ds_plot = background_subtract(ds)
        resolved_low, resolved_high = _resolve_clip_limits(
            ds_plot.data,
            clip_low=clip_low,
            clip_high=clip_high,
            clip_percentiles=clip_percentiles,
        )
        title_suffix = "background_subtracted"
    elif process == "noise_reduced":
        ds_background = background_subtract(ds)
        resolved_low, resolved_high = _resolve_clip_limits(
            ds_background.data,
            clip_low=clip_low,
            clip_high=clip_high,
            clip_percentiles=clip_percentiles,
        )
        if resolved_low is None or resolved_high is None:
            raise ValueError(
                "When process='noise_reduced', provide clip_low/clip_high or clip_percentiles."
            )
        ds_plot = noise_reduce_mean_clip(
            ds,
            clip_low=resolved_low,
            clip_high=resolved_high,
            scale=None,
        )
        title_suffix = "noise_clipped"
    else:  # raw
        ds_plot = ds
        resolved_low, resolved_high = _resolve_clip_limits(
            ds_plot.data,
            clip_low=clip_low,
            clip_high=clip_high,
            clip_percentiles=clip_percentiles,
        )
        title_suffix = "raw"

    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = cast("Figure", ax.figure)

    extent, converter = _compute_extent(ds, time_format)

    # Convert to dB if requested
    plot_data = ds_plot.data
    vmin, vmax = resolved_low, resolved_high
    if intensity_units == "dB":
        plot_data = plot_data * DIGITS_TO_DB_FACTOR
        if vmin is not None:
            vmin = vmin * DIGITS_TO_DB_FACTOR
        if vmax is not None:
            vmax = vmax * DIGITS_TO_DB_FACTOR

    im = ax.imshow(
        plot_data,
        aspect="auto",
        extent=extent,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        **imshow_kwargs,
    )
    # Use filename-based title if not provided
    if title is None:
        title = _get_filename_title(ds, title_suffix)
    ax.set_title(title)
    _format_time_axis(ax, converter, time_format)
    ax.set_ylabel("Frequency [MHz]")

    if show_colorbar:
        cbar = fig.colorbar(im, ax=ax)
        if intensity_units == "dB":
            cbar.set_label("Intensity [dB]")
        else:
            cbar.set_label("Intensity [Digits]")

    _save_figure_if_requested(fig, save_path, savefig_kwargs)

    return fig, ax, im


def plot_raw_spectrum(
    ds: DynamicSpectrum,
    title: str | None = None,
    cmap: str = "viridis",
    figsize: tuple[float, float] | None = None,
    clip_low: float | None = None,
    clip_high: float | None = None,
    clip_percentiles: tuple[float, float] | None = None,
    ax: Optional[plt.Axes] = None,
    show_colorbar: bool = True,
    time_format: Literal["seconds", "ut"] = "seconds",
    intensity_units: Literal["digits", "dB"] = "digits",
    save_path: str | Path | None = None,
    savefig_kwargs: dict[str, Any] | None = None,
    **imshow_kwargs,
) -> tuple["Figure", "Axes", "AxesImage"]:
    """
    Plot a raw DynamicSpectrum without any processing.

    This is a convenience function that calls plot_dynamic_spectrum with 
    process="raw" and a default colormap suitable for raw data.

    Parameters
    ----------
    ds : DynamicSpectrum
        The dynamic spectrum to plot.
    title : str | None
        Plot title.
    cmap : str
        Matplotlib colormap name. Default is "viridis".
    figsize : tuple[float, float] | None
        Figure size as (width, height) in inches.
    clip_low : float | None
        Minimum value for colormap normalization.
    clip_high : float | None
        Maximum value for colormap normalization.
    clip_percentiles : tuple[float, float] | None
        Percentile-based clipping limits when clip_low/clip_high are absent.
    ax : plt.Axes | None
        Existing axes to plot on. If None, creates a new figure.
    show_colorbar : bool
        Whether to show a colorbar.
    time_format : {"seconds", "ut"}
        Format for the time axis.
    intensity_units : {"digits", "dB"}
        Units for the intensity axis.
    save_path : str | Path | None
        Optional output path for saving the figure.
    savefig_kwargs : dict[str, Any] | None
        Optional kwargs passed to ``Figure.savefig``.
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
    return plot_dynamic_spectrum(
        ds,
        process="raw",
        clip_low=clip_low,
        clip_high=clip_high,
        clip_percentiles=clip_percentiles,
        title=title,
        cmap=cmap,
        figsize=figsize,
        ax=ax,
        show_colorbar=show_colorbar,
        time_format=time_format,
        intensity_units=intensity_units,
        save_path=save_path,
        savefig_kwargs=savefig_kwargs,
        **imshow_kwargs,
    )


def plot_background_subtracted(
    ds: DynamicSpectrum,
    title: str | None = None,
    cmap: str = "jet",
    figsize: tuple[float, float] | None = None,
    clip_low: float | None = None,
    clip_high: float | None = None,
    clip_percentiles: tuple[float, float] | None = None,
    ax: Optional[plt.Axes] = None,
    show_colorbar: bool = True,
    time_format: Literal["seconds", "ut"] = "seconds",
    intensity_units: Literal["digits", "dB"] = "digits",
    save_path: str | Path | None = None,
    savefig_kwargs: dict[str, Any] | None = None,
    **imshow_kwargs,
) -> tuple["Figure", "Axes", "AxesImage"]:
    """
    Plot a DynamicSpectrum after background subtraction (before clipping).

    This is a convenience function that calls plot_dynamic_spectrum with
    process="background_subtracted".

    Parameters
    ----------
    ds : DynamicSpectrum
        The raw dynamic spectrum (will be background-subtracted internally).
    title : str | None
        Plot title.
    cmap : str
        Matplotlib colormap name. Default is "jet" which works well for
        showing positive/negative deviations.
    figsize : tuple[float, float] | None
        Figure size as (width, height) in inches.
    clip_low : float | None
        Minimum value for colormap normalization.
    clip_high : float | None
        Maximum value for colormap normalization.
    clip_percentiles : tuple[float, float] | None
        Percentile-based clipping limits when clip_low/clip_high are absent.
    ax : plt.Axes | None
        Existing axes to plot on. If None, creates a new figure.
    show_colorbar : bool
        Whether to show a colorbar.
    time_format : {"seconds", "ut"}
        Format for the time axis.
    intensity_units : {"digits", "dB"}
        Units for the intensity axis.
    save_path : str | Path | None
        Optional output path for saving the figure.
    savefig_kwargs : dict[str, Any] | None
        Optional kwargs passed to ``Figure.savefig``.
    **imshow_kwargs
        Additional keyword arguments passed to matplotlib's imshow().

    Returns
    -------
    tuple[Figure, Axes, AxesImage]
        The figure, axes, and image objects.

    Example
    -------
    >>> ds = read_fits("spectrum.fit.gz")
    >>> fig, ax, im = plot_background_subtracted(ds, clip_low=-10, clip_high=30)
    """
    return plot_dynamic_spectrum(
        ds,
        process="background_subtracted",
        clip_low=clip_low,
        clip_high=clip_high,
        clip_percentiles=clip_percentiles,
        title=title,
        cmap=cmap,
        figsize=figsize,
        ax=ax,
        show_colorbar=show_colorbar,
        time_format=time_format,
        intensity_units=intensity_units,
        save_path=save_path,
        savefig_kwargs=savefig_kwargs,
        **imshow_kwargs,
    )


def plot_light_curve(
    ds: DynamicSpectrum,
    frequency_mhz: float,
    process: Literal["raw", "background_subtracted", "noise_reduced"] = "raw",
    title: str | None = None,
    figsize: tuple[float, float] | None = None,
    ax: Optional[plt.Axes] = None,
    time_format: Literal["seconds", "ut"] = "seconds",
    clip_low: float | None = None,
    clip_high: float | None = None,
    intensity_units: Literal["digits", "dB"] = "digits",
    **plot_kwargs,
) -> tuple["Figure", "Axes", "plt.Line2D"]:
    """
    Plot a light curve (intensity vs time) at a specific frequency.

    This function extracts the intensity values at the frequency channel closest
    to the specified frequency and plots them against time. The data can be
    plotted raw, after background subtraction, or after full noise reduction.

    Parameters
    ----------
    ds : DynamicSpectrum
        The dynamic spectrum to extract the light curve from.
    frequency_mhz : float
        The target frequency in MHz. The function will use the closest
        available frequency channel in the spectrum.
    process : {"raw", "background_subtracted", "noise_reduced"}
        Processing to apply before plotting:
        - "raw": Use the original data without any processing.
        - "background_subtracted": Subtract mean over time for each frequency.
        - "noise_reduced": Apply full noise reduction (requires clip_low/clip_high).
    title : str | None
        Plot title. If None, generates title from filename and frequency.
    figsize : tuple[float, float] | None
        Figure size as (width, height) in inches. Ignored if ax is provided.
    ax : plt.Axes | None
        Existing axes to plot on. If None, creates a new figure.
    time_format : {"seconds", "ut"}
        Format for the time axis. "seconds" shows elapsed seconds,
        "ut" shows Universal Time (requires ut_start_sec in metadata).
    clip_low : float | None
        Lower clipping threshold for noise reduction. Required if process="noise_reduced".
    clip_high : float | None
        Upper clipping threshold for noise reduction. Required if process="noise_reduced".
    intensity_units : {"digits", "dB"}
        Units for the intensity axis. "digits" shows raw ADU values,
        "dB" converts using dB = Digits * 0.384 (pseudo-calibration).
    **plot_kwargs
        Additional keyword arguments passed to matplotlib's plot().

    Returns
    -------
    tuple[Figure, Axes, Line2D]
        The figure, axes, and line objects.

    Raises
    ------
    FrequencyOutOfRangeError
        If the requested frequency is outside the spectrum's frequency range.
    ValueError
        If process="noise_reduced" but clip_low or clip_high is not provided.

    Example
    -------
    >>> ds = read_fits("spectrum.fit.gz")
    >>> # Plot raw light curve at 60 MHz
    >>> fig, ax, line = plot_light_curve(ds, frequency_mhz=60, process="raw")
    >>> # Plot noise-reduced light curve with custom clipping
    >>> fig, ax, line = plot_light_curve(
    ...     ds, frequency_mhz=60, process="noise_reduced",
    ...     clip_low=-5, clip_high=20
    ... )
    """
    from .exceptions import FrequencyOutOfRangeError
    from .processing import background_subtract, noise_reduce_mean_clip

    # Validate frequency is within range
    freq_min = float(ds.freqs_mhz.min())
    freq_max = float(ds.freqs_mhz.max())

    if frequency_mhz < freq_min or frequency_mhz > freq_max:
        raise FrequencyOutOfRangeError(
            f"Requested frequency {frequency_mhz} MHz is outside the spectrum's "
            f"frequency range [{freq_min:.2f}, {freq_max:.2f}] MHz."
        )

    # Validate clip parameters for noise_reduced
    if process == "noise_reduced":
        if clip_low is None or clip_high is None:
            raise ValueError(
                "When process='noise_reduced', both clip_low and clip_high must be provided."
            )
        assert clip_low is not None
        assert clip_high is not None

    # Find the closest frequency channel
    freq_idx = int(np.argmin(np.abs(ds.freqs_mhz - frequency_mhz)))
    actual_freq = float(ds.freqs_mhz[freq_idx])

    # Apply processing
    if process == "background_subtracted":
        ds_processed = background_subtract(ds)
    elif process == "noise_reduced":
        ds_processed = noise_reduce_mean_clip(
            ds,
            clip_low=cast(float, clip_low),
            clip_high=cast(float, clip_high),
            scale=None,
        )
    else:  # raw
        ds_processed = ds

    # Extract light curve data
    light_curve = ds_processed.data[freq_idx, :]

    # Convert to dB if requested
    if intensity_units == "dB":
        light_curve = light_curve * DIGITS_TO_DB_FACTOR

    # Create figure and axes
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = cast("Figure", ax.figure)

    # Prepare time axis
    if time_format == "ut":
        converter = TimeAxisConverter.from_dynamic_spectrum(ds)
        time_values = ds.time_s + converter.ut_start_sec
        ax.set_xlabel("Time [UT]")
        # Format x-tick labels as UT times
        from matplotlib.ticker import FuncFormatter

        def fmt(x, pos):
            return converter.seconds_to_ut(x - converter.ut_start_sec, precision="minute")

        ax.xaxis.set_major_formatter(FuncFormatter(fmt))
    else:
        time_values = ds.time_s
        ax.set_xlabel("Time [s]")

    # Plot the light curve
    (line,) = ax.plot(time_values, light_curve, **plot_kwargs)

    # Set title
    if title is None:
        # Map process name to title suffix
        title_suffix = "noise_clipped" if process == "noise_reduced" else process
        if ds.source is not None:
            filename = ds.source.stem
            # Strip .fit if it's a double extension like .fit.gz
            if filename.endswith(".fit"):
                filename = filename[:-4]
            title = f"{filename}_light_curve_{actual_freq:.1f}MHz_{title_suffix}"
        else:
            title = f"Light Curve @ {actual_freq:.1f} MHz ({title_suffix})"

    ax.set_title(title)

    if intensity_units == "dB":
        ax.set_ylabel("Intensity [dB]")
    else:
        ax.set_ylabel("Intensity [Digits]")

    return fig, ax, line


"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""


from importlib.metadata import PackageNotFoundError, version

from .exceptions import (
    CombineError,
    CropError,
    DownloadError,
    ECallistoError,
    FrequencyOutOfRangeError,
    InvalidFilenameError,
    InvalidFITSError,
    GOESDataError,
    GOESConnectionError,
    GOESDownloadError,
    GOESError,
    WorkflowError,
)
from .io import CallistoFileParts, parse_callisto_filename, read_fits
from .models import DynamicSpectrum
from .processing import (
    background_subtract_frequency,
    mitigate_rfi,
    mitigate_rfi_mad,
    noise_reduce_mean_clip,
    noise_reduce_median_clip,
)
from .crop import crop, crop_frequency, crop_time, slice_by_index

try:
    __version__ = version("ecallistolib")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    # Version
    "__version__",
    # Core
    "DynamicSpectrum",
    "CallistoFileParts",
    # I/O
    "parse_callisto_filename",
    "read_fits",
    # Processing
    "noise_reduce_mean_clip",
    "noise_reduce_median_clip",
    # Cropping
    "crop",
    "crop_frequency",
    "crop_time",
    "slice_by_index",
    # Exceptions
    "ECallistoError",
    "InvalidFITSError",
    "InvalidFilenameError",
    "DownloadError",
    "CombineError",
    "CropError",
    "FrequencyOutOfRangeError",
    "WorkflowError",
    "GOESError",
    "GOESConnectionError",
    "GOESDownloadError",
    "GOESDataError",
]


def __getattr__(name: str):
    """Lazy imports for optional dependencies."""
    if name in {
        "combine_time",
        "combine_frequency",
        "can_combine_time",
        "can_combine_frequency",
        "describe_frequency_combination",
        "FrequencyBand",
        "FrequencySpan",
        "FrequencyCombinationReport",
    }:
        from .combine import (
            FrequencyBand,
            FrequencyCombinationReport,
            FrequencySpan,
            can_combine_frequency,
            can_combine_time,
            combine_frequency,
            combine_time,
            describe_frequency_combination,
        )

        return {
            "can_combine_frequency": can_combine_frequency,
            "combine_frequency": combine_frequency,
            "can_combine_time": can_combine_time,
            "combine_time": combine_time,
            "describe_frequency_combination": describe_frequency_combination,
            "FrequencyBand": FrequencyBand,
            "FrequencySpan": FrequencySpan,
            "FrequencyCombinationReport": FrequencyCombinationReport,
        }[name]

    if name in {"list_remote_fits", "list_remote_fits_range", "download_files"}:
        from .download import download_files, list_remote_fits, list_remote_fits_range

        return {
            "list_remote_fits": list_remote_fits,
            "list_remote_fits_range": list_remote_fits_range,
            "download_files": download_files,
        }[name]

    if name in {
        "plot_dynamic_spectrum",
        "plot_raw_spectrum",
        "plot_background_subtracted",
        "plot_light_curve",
        "plot_spectrum_with_light_curves",
        "SpectrumLightCurvePlot",
        "TimeAxisConverter",
        "plot_spectrum_with_goes",
        "SpectrumGOESPlot",
    }:
        from .plotting import (
            SpectrumGOESPlot,
            SpectrumLightCurvePlot,
            TimeAxisConverter,
            plot_background_subtracted,
            plot_dynamic_spectrum,
            plot_light_curve,
            plot_raw_spectrum,
            plot_spectrum_with_goes,
            plot_spectrum_with_light_curves,
        )

        return {
            "plot_dynamic_spectrum": plot_dynamic_spectrum,
            "plot_raw_spectrum": plot_raw_spectrum,
            "plot_background_subtracted": plot_background_subtracted,
            "plot_light_curve": plot_light_curve,
            "plot_spectrum_with_light_curves": plot_spectrum_with_light_curves,
            "SpectrumLightCurvePlot": SpectrumLightCurvePlot,
            "TimeAxisConverter": TimeAxisConverter,
            "plot_spectrum_with_goes": plot_spectrum_with_goes,
            "SpectrumGOESPlot": SpectrumGOESPlot,
        }[name]

    if name in {"load_spectra", "SpectrumCollection", "SpectrumGroupKey"}:
        from .workflow import SpectrumCollection, SpectrumGroupKey, load_spectra

        return {
            "load_spectra": load_spectra,
            "SpectrumCollection": SpectrumCollection,
            "SpectrumGroupKey": SpectrumGroupKey,
        }[name]

    if name in {
        "GOESXRayData",
        "load_goes_xray",
        "fetch_goes_xray",
        "fetch_goes_for_spectrum",
        "preferred_goes_satellite_numbers",
    }:
        from .goes import (
            GOESXRayData,
            fetch_goes_for_spectrum,
            fetch_goes_xray,
            load_goes_xray,
            preferred_goes_satellite_numbers,
        )

        return {
            "GOESXRayData": GOESXRayData,
            "load_goes_xray": load_goes_xray,
            "fetch_goes_xray": fetch_goes_xray,
            "fetch_goes_for_spectrum": fetch_goes_for_spectrum,
            "preferred_goes_satellite_numbers": preferred_goes_satellite_numbers,
        }[name]

    if name == "background_subtract":
        from .processing import background_subtract

        return background_subtract

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = list(__all__) + [
    "background_subtract_frequency",
    "mitigate_rfi",
    "mitigate_rfi_mad",
    "combine_time",
    "combine_frequency",
    "can_combine_time",
    "can_combine_frequency",
    "describe_frequency_combination",
    "FrequencyBand",
    "FrequencySpan",
    "FrequencyCombinationReport",
    "load_spectra",
    "SpectrumCollection",
    "SpectrumGroupKey",
    "GOESXRayData",
    "load_goes_xray",
    "fetch_goes_xray",
    "fetch_goes_for_spectrum",
    "preferred_goes_satellite_numbers",
    "plot_spectrum_with_goes",
    "SpectrumGOESPlot",
    "plot_spectrum_with_light_curves",
    "SpectrumLightCurvePlot",
]

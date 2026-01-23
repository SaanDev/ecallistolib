
"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""


from importlib.metadata import PackageNotFoundError, version

from .exceptions import (
    CombineError,
    CropError,
    DownloadError,
    ECallistoError,
    InvalidFilenameError,
    InvalidFITSError,
)
from .io import CallistoFileParts, parse_callisto_filename, read_fits
from .models import DynamicSpectrum
from .processing import noise_reduce_mean_clip
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
]


def __getattr__(name: str):
    """Lazy imports for optional dependencies."""
    if name in {
        "combine_time",
        "combine_frequency",
        "can_combine_time",
        "can_combine_frequency",
    }:
        from .combine import (
            can_combine_frequency,
            can_combine_time,
            combine_frequency,
            combine_time,
        )

        return {
            "can_combine_frequency": can_combine_frequency,
            "combine_frequency": combine_frequency,
            "can_combine_time": can_combine_time,
            "combine_time": combine_time,
        }[name]

    if name in {"list_remote_fits", "download_files"}:
        from .download import download_files, list_remote_fits

        return {"list_remote_fits": list_remote_fits, "download_files": download_files}[
            name
        ]

    if name in {
        "plot_dynamic_spectrum",
        "plot_raw_spectrum",
        "plot_background_subtracted",
        "TimeAxisConverter",
    }:
        from .plotting import (
            TimeAxisConverter,
            plot_background_subtracted,
            plot_dynamic_spectrum,
            plot_raw_spectrum,
        )

        return {
            "plot_dynamic_spectrum": plot_dynamic_spectrum,
            "plot_raw_spectrum": plot_raw_spectrum,
            "plot_background_subtracted": plot_background_subtracted,
            "TimeAxisConverter": TimeAxisConverter,
        }[name]

    if name == "background_subtract":
        from .processing import background_subtract

        return background_subtract

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

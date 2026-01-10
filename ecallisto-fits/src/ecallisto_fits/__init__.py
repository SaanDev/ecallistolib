from importlib.metadata import PackageNotFoundError, version

from .io import parse_callisto_filename, read_fits
from .models import DynamicSpectrum
from .processing import noise_reduce_mean_clip

try:
    __version__ = version("ecallisto-fits")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "__version__",
    "DynamicSpectrum",
    "parse_callisto_filename",
    "read_fits",
    "noise_reduce_mean_clip",
]

def __getattr__(name: str):
    if name in {"combine_time", "combine_frequency", "can_combine_time", "can_combine_frequency"}:
        from .combine import can_combine_frequency, can_combine_time, combine_frequency, combine_time
        return {
            "can_combine_frequency": can_combine_frequency,
            "combine_frequency": combine_frequency,
            "can_combine_time": can_combine_time,
            "combine_time": combine_time,
        }[name]

    if name in {"list_remote_fits", "download_files"}:
        from .download import download_files, list_remote_fits
        return {"list_remote_fits": list_remote_fits, "download_files": download_files}[name]

    if name in {"plot_dynamic_spectrum"}:
        from .plotting import plot_dynamic_spectrum
        return plot_dynamic_spectrum

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Custom exceptions for ecallisto-fits library."""

from __future__ import annotations


class ECallistoError(Exception):
    """Base exception for all ecallisto-fits errors."""
    pass


class InvalidFITSError(ECallistoError):
    """Raised when a FITS file is invalid or cannot be read."""
    pass


class InvalidFilenameError(ECallistoError):
    """Raised when a filename doesn't match e-CALLISTO naming convention."""
    pass


class DownloadError(ECallistoError):
    """Raised when downloading files from the archive fails."""
    pass


class CombineError(ECallistoError):
    """Raised when spectra cannot be combined."""
    pass


class CropError(ECallistoError):
    """Raised when cropping parameters are invalid."""
    pass

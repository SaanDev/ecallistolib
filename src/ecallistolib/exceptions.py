"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations


class ECallistoError(Exception):
    """Base exception for all ecallistolib errors."""
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


class FrequencyOutOfRangeError(ECallistoError):
    """Raised when the requested frequency is outside the spectrum's frequency range."""
    pass


class WorkflowError(ECallistoError):
    """Raised when FITS inputs cannot be organized into an analysis workflow."""
    pass


class GOESError(ECallistoError):
    """Base exception for GOES XRS data operations."""
    pass


class GOESDownloadError(GOESError):
    """Raised when GOES XRS archive retrieval fails."""
    pass


class GOESConnectionError(GOESDownloadError):
    """Raised when the official GOES XRS archive cannot be reached."""
    pass


class GOESDataError(GOESError):
    """Raised when GOES XRS data are invalid or unsupported."""
    pass

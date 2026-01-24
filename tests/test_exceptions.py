"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import pytest

from ecallistolib.exceptions import (
    CombineError,
    CropError,
    DownloadError,
    ECallistoError,
    InvalidFilenameError,
    InvalidFITSError,
)


class TestExceptionHierarchy:
    """Test that all exceptions inherit from ECallistoError."""

    def test_ecallisto_error_is_base_exception(self):
        assert issubclass(ECallistoError, Exception)

    def test_invalid_fits_error_inherits_from_base(self):
        assert issubclass(InvalidFITSError, ECallistoError)

    def test_invalid_filename_error_inherits_from_base(self):
        assert issubclass(InvalidFilenameError, ECallistoError)

    def test_download_error_inherits_from_base(self):
        assert issubclass(DownloadError, ECallistoError)

    def test_combine_error_inherits_from_base(self):
        assert issubclass(CombineError, ECallistoError)

    def test_crop_error_inherits_from_base(self):
        assert issubclass(CropError, ECallistoError)


class TestExceptionMessages:
    """Test that exceptions can be raised with messages."""

    def test_ecallisto_error_with_message(self):
        with pytest.raises(ECallistoError, match="test message"):
            raise ECallistoError("test message")

    def test_invalid_fits_error_with_message(self):
        with pytest.raises(InvalidFITSError, match="bad fits file"):
            raise InvalidFITSError("bad fits file")

    def test_crop_error_with_message(self):
        with pytest.raises(CropError, match="invalid range"):
            raise CropError("invalid range")


class TestExceptionCatching:
    """Test that base exception can catch derived exceptions."""

    def test_catch_derived_with_base(self):
        try:
            raise InvalidFITSError("test")
        except ECallistoError as e:
            assert str(e) == "test"

    def test_catch_multiple_derived_with_base(self):
        exceptions = [
            InvalidFITSError("a"),
            InvalidFilenameError("b"),
            DownloadError("c"),
            CombineError("d"),
            CropError("e"),
        ]
        for exc in exceptions:
            try:
                raise exc
            except ECallistoError:
                pass  # Should catch all

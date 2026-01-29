"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.3
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import pytest
from pathlib import Path

from ecallistolib.io import parse_callisto_filename, CallistoFileParts
from ecallistolib.exceptions import InvalidFilenameError


class TestParseCallistoFilename:
    """Tests for parse_callisto_filename function."""

    def test_basic_filename(self):
        """Test parsing a standard filename."""
        p = parse_callisto_filename("ALASKA_20240101_123000_01.fit.gz")
        assert p.station == "ALASKA"
        assert p.date_yyyymmdd == "20240101"
        assert p.time_hhmmss == "123000"
        assert p.focus == "01"

    def test_station_with_hyphen(self):
        """Test station names with hyphens."""
        p = parse_callisto_filename("ALASKA-COHOE_20240101_123000_01.fit.gz")
        assert p.station == "ALASKA-COHOE"

    def test_different_focus(self):
        """Test different focus/channel numbers."""
        p = parse_callisto_filename("GLASGOW_20230615_080000_02.fit.gz")
        assert p.focus == "02"

    def test_path_object(self):
        """Test with Path object instead of string."""
        p = parse_callisto_filename(Path("/data/ALASKA_20240101_123000_01.fit.gz"))
        assert p.station == "ALASKA"

    def test_full_path(self):
        """Test with full path (should only parse basename)."""
        p = parse_callisto_filename("/long/path/to/ALASKA_20240101_123000_01.fit.gz")
        assert p.station == "ALASKA"

    def test_fit_extension(self):
        """Test .fit extension without .gz."""
        p = parse_callisto_filename("ALASKA_20240101_123000_01.fit")
        assert p.focus == "01"

    def test_invalid_format_too_few_parts(self):
        """Test invalid filename with too few underscores."""
        with pytest.raises(InvalidFilenameError, match="Invalid CALLISTO filename"):
            parse_callisto_filename("ALASKA_20240101.fit")

    def test_invalid_format_no_underscores(self):
        """Test filename with no underscores."""
        with pytest.raises(InvalidFilenameError):
            parse_callisto_filename("invalid.fit")

    def test_returns_callisto_file_parts(self):
        """Test return type is CallistoFileParts."""
        result = parse_callisto_filename("ALASKA_20240101_123000_01.fit.gz")
        assert isinstance(result, CallistoFileParts)


class TestCallistoFileParts:
    """Tests for CallistoFileParts dataclass."""

    def test_is_frozen(self):
        """Test that CallistoFileParts is immutable."""
        parts = CallistoFileParts("ALASKA", "20240101", "123000", "01")
        with pytest.raises(Exception):  # FrozenInstanceError
            parts.station = "NEW"

    def test_equality(self):
        """Test equality comparison."""
        p1 = CallistoFileParts("ALASKA", "20240101", "123000", "01")
        p2 = CallistoFileParts("ALASKA", "20240101", "123000", "01")
        assert p1 == p2

    def test_inequality(self):
        """Test inequality comparison."""
        p1 = CallistoFileParts("ALASKA", "20240101", "123000", "01")
        p2 = CallistoFileParts("GLASGOW", "20240101", "123000", "01")
        assert p1 != p2

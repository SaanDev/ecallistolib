"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from conftest import create_sample_fits

import ecallistolib as ecl
from ecallistolib.exceptions import InvalidFITSError


@pytest.fixture
def sample_fits_file(tmp_path):
    """Create a temporary sample FITS file."""
    output = tmp_path / "SAMPLE_20240101_120000_01.fit"
    create_sample_fits(output, n_freq=50, n_time=100, add_burst=True)
    return output


@pytest.fixture
def sample_fits_pair(tmp_path):
    """Create a pair of FITS files for combining tests."""
    f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
    f2 = tmp_path / "SAMPLE_20240101_120000_02.fit"

    create_sample_fits(f1, n_freq=50, n_time=100, freq_start=100, freq_end=200)
    create_sample_fits(f2, n_freq=50, n_time=100, freq_start=200, freq_end=300)

    return f1, f2


class TestReadFitsIntegration:
    """Integration tests for reading FITS files."""

    def test_read_sample_fits(self, sample_fits_file):
        """Test reading a sample FITS file."""
        ds = ecl.read_fits(sample_fits_file)

        assert ds.data.shape == (50, 100)
        assert len(ds.freqs_mhz) == 50
        assert len(ds.time_s) == 100
        assert ds.source == sample_fits_file

    def test_read_fits_metadata(self, sample_fits_file):
        """Test that metadata is extracted correctly."""
        ds = ecl.read_fits(sample_fits_file)

        assert ds.meta.get("station") == "SAMPLE"
        assert ds.meta.get("date") == "20240101"
        assert ds.meta.get("time") == "120000"
        assert ds.meta.get("focus") == "01"

    def test_read_fits_file_not_found(self):
        """Test reading non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ecl.read_fits("/nonexistent/path/file.fit")


class TestProcessingIntegration:
    """Integration tests for processing functions."""

    def test_noise_reduce_integration(self, sample_fits_file):
        """Test noise reduction on real data."""
        ds = ecl.read_fits(sample_fits_file)
        processed = ecl.noise_reduce_mean_clip(ds)

        # Should have same shape
        assert processed.shape == ds.shape

        # Should have processing metadata
        assert "noise_reduction" in processed.meta

        # Original should be unchanged
        assert "noise_reduction" not in ds.meta


class TestCroppingIntegration:
    """Integration tests for cropping functions."""

    def test_crop_frequency_integration(self, sample_fits_file):
        """Test cropping frequency on real data."""
        ds = ecl.read_fits(sample_fits_file)
        original_shape = ds.shape

        # Crop to middle frequencies
        cropped = ecl.crop_frequency(ds, 100, 400)

        assert cropped.shape[0] < original_shape[0]
        assert cropped.shape[1] == original_shape[1]

    def test_crop_time_integration(self, sample_fits_file):
        """Test cropping time on real data."""
        ds = ecl.read_fits(sample_fits_file)
        original_shape = ds.shape

        # Crop to first half of time
        cropped = ecl.crop_time(ds, 0, 450)

        assert cropped.shape[0] == original_shape[0]
        assert cropped.shape[1] < original_shape[1]

    def test_full_workflow(self, sample_fits_file):
        """Test complete workflow: read -> crop -> process."""
        # Read
        ds = ecl.read_fits(sample_fits_file)

        # Crop
        cropped = ecl.crop(ds, freq_range=(100, 400), time_range=(0, 450))

        # Process
        processed = ecl.noise_reduce_mean_clip(cropped)

        # Verify
        assert processed.shape[0] <= ds.shape[0]
        assert processed.shape[1] <= ds.shape[1]
        assert "cropped" in processed.meta
        assert "noise_reduction" in processed.meta


class TestCombineIntegration:
    """Integration tests for combining functions."""

    def test_combine_time_integration(self, tmp_path):
        """Test combining files along time axis."""
        # Create two files with same frequency range
        f1 = tmp_path / "SAMPLE_20240101_120000_01.fit"
        f2 = tmp_path / "SAMPLE_20240101_121500_01.fit"

        create_sample_fits(f1, n_freq=50, n_time=100)
        create_sample_fits(f2, n_freq=50, n_time=100)

        # Combine
        combined = ecl.combine_time([f1, f2])

        # Should have double the time samples
        assert combined.shape[1] == 200
        assert combined.shape[0] == 50


class TestExceptionIntegration:
    """Integration tests for exception handling."""

    def test_invalid_fits_raises(self, tmp_path):
        """Test that invalid FITS file raises InvalidFITSError."""
        bad_file = tmp_path / "bad.fit"
        bad_file.write_text("not a fits file")

        with pytest.raises(InvalidFITSError):
            ecl.read_fits(bad_file)

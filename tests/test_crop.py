"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import numpy as np
import pytest

from ecallistolib.crop import crop, crop_frequency, crop_time, slice_by_index
from ecallistolib.exceptions import CropError
from ecallistolib.models import DynamicSpectrum


@pytest.fixture
def sample_spectrum():
    """Create a sample DynamicSpectrum for testing."""
    data = np.arange(200).reshape(10, 20).astype(float)  # 10 freqs, 20 times
    freqs = np.linspace(100, 200, 10)  # 100 to 200 MHz
    times = np.linspace(0, 60, 20)  # 0 to 60 seconds
    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=times)


class TestCropFrequency:
    """Tests for crop_frequency function."""

    def test_crop_frequency_full_range(self, sample_spectrum):
        """Cropping with full range should return equivalent data."""
        result = crop_frequency(sample_spectrum, 100, 200)
        assert result.shape == sample_spectrum.shape

    def test_crop_frequency_subset(self, sample_spectrum):
        """Cropping should reduce frequency channels."""
        result = crop_frequency(sample_spectrum, 120, 180)
        assert result.shape[0] < sample_spectrum.shape[0]
        assert result.shape[1] == sample_spectrum.shape[1]  # Time unchanged
        assert result.freqs_mhz.min() >= 120
        assert result.freqs_mhz.max() <= 180

    def test_crop_frequency_none_bounds(self, sample_spectrum):
        """None bounds should use data limits."""
        result = crop_frequency(sample_spectrum, None, None)
        assert result.shape == sample_spectrum.shape

    def test_crop_frequency_only_min(self, sample_spectrum):
        """Only specifying min should work."""
        result = crop_frequency(sample_spectrum, freq_min=150)
        assert result.freqs_mhz.min() >= 150

    def test_crop_frequency_only_max(self, sample_spectrum):
        """Only specifying max should work."""
        result = crop_frequency(sample_spectrum, freq_max=150)
        assert result.freqs_mhz.max() <= 150

    def test_crop_frequency_invalid_range(self, sample_spectrum):
        """min > max should raise CropError."""
        with pytest.raises(CropError, match="must be <="):
            crop_frequency(sample_spectrum, 180, 120)

    def test_crop_frequency_out_of_range(self, sample_spectrum):
        """Range outside data should raise CropError."""
        with pytest.raises(CropError, match="No frequencies in range"):
            crop_frequency(sample_spectrum, 300, 400)

    def test_crop_frequency_metadata(self, sample_spectrum):
        """Cropping should record operation in metadata."""
        result = crop_frequency(sample_spectrum, 120, 180)
        assert "cropped" in result.meta
        assert result.meta["cropped"]["frequency"]["min"] == 120
        assert result.meta["cropped"]["frequency"]["max"] == 180


class TestCropTime:
    """Tests for crop_time function."""

    def test_crop_time_full_range(self, sample_spectrum):
        """Cropping with full range should return equivalent data."""
        result = crop_time(sample_spectrum, 0, 60)
        assert result.shape == sample_spectrum.shape

    def test_crop_time_subset(self, sample_spectrum):
        """Cropping should reduce time samples."""
        result = crop_time(sample_spectrum, 10, 40)
        assert result.shape[1] < sample_spectrum.shape[1]
        assert result.shape[0] == sample_spectrum.shape[0]  # Frequency unchanged
        assert result.time_s.min() >= 10
        assert result.time_s.max() <= 40

    def test_crop_time_none_bounds(self, sample_spectrum):
        """None bounds should use data limits."""
        result = crop_time(sample_spectrum, None, None)
        assert result.shape == sample_spectrum.shape

    def test_crop_time_invalid_range(self, sample_spectrum):
        """min > max should raise CropError."""
        with pytest.raises(CropError, match="must be <="):
            crop_time(sample_spectrum, 50, 10)

    def test_crop_time_out_of_range(self, sample_spectrum):
        """Range outside data should raise CropError."""
        with pytest.raises(CropError, match="No times in range"):
            crop_time(sample_spectrum, 100, 200)

    def test_crop_time_metadata(self, sample_spectrum):
        """Cropping should record operation in metadata."""
        result = crop_time(sample_spectrum, 10, 40)
        assert "cropped" in result.meta
        assert result.meta["cropped"]["time"]["min"] == 10
        assert result.meta["cropped"]["time"]["max"] == 40


class TestCrop:
    """Tests for combined crop function."""

    def test_crop_frequency_only(self, sample_spectrum):
        """Crop with only freq_range should work."""
        result = crop(sample_spectrum, freq_range=(120, 180))
        assert result.freqs_mhz.min() >= 120
        assert result.freqs_mhz.max() <= 180

    def test_crop_time_only(self, sample_spectrum):
        """Crop with only time_range should work."""
        result = crop(sample_spectrum, time_range=(10, 40))
        assert result.time_s.min() >= 10
        assert result.time_s.max() <= 40

    def test_crop_both_axes(self, sample_spectrum):
        """Crop both axes at once."""
        result = crop(sample_spectrum, freq_range=(120, 180), time_range=(10, 40))
        assert result.freqs_mhz.min() >= 120
        assert result.freqs_mhz.max() <= 180
        assert result.time_s.min() >= 10
        assert result.time_s.max() <= 40

    def test_crop_no_arguments(self, sample_spectrum):
        """Crop with no arguments should return equivalent data."""
        result = crop(sample_spectrum)
        assert result.shape == sample_spectrum.shape


class TestSliceByIndex:
    """Tests for slice_by_index function."""

    def test_slice_frequency(self, sample_spectrum):
        """Slice frequency axis by index."""
        result = slice_by_index(sample_spectrum, freq_slice=slice(0, 5))
        assert result.shape[0] == 5
        assert result.shape[1] == sample_spectrum.shape[1]

    def test_slice_time(self, sample_spectrum):
        """Slice time axis by index."""
        result = slice_by_index(sample_spectrum, time_slice=slice(0, 10))
        assert result.shape[0] == sample_spectrum.shape[0]
        assert result.shape[1] == 10

    def test_slice_both(self, sample_spectrum):
        """Slice both axes by index."""
        result = slice_by_index(sample_spectrum, freq_slice=slice(2, 8), time_slice=slice(5, 15))
        assert result.shape == (6, 10)

    def test_slice_with_step(self, sample_spectrum):
        """Slice with step (every other sample)."""
        result = slice_by_index(sample_spectrum, time_slice=slice(None, None, 2))
        assert result.shape[1] == 10  # Half of 20

    def test_slice_empty_raises(self, sample_spectrum):
        """Empty slice should raise CropError."""
        with pytest.raises(CropError, match="empty data"):
            slice_by_index(sample_spectrum, freq_slice=slice(5, 5))

    def test_slice_metadata(self, sample_spectrum):
        """Slicing should record operation in metadata."""
        result = slice_by_index(sample_spectrum, freq_slice=slice(0, 5))
        assert "sliced" in result.meta

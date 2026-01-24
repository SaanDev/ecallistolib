"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import numpy as np
import pytest
from pathlib import Path

from ecallistolib.models import DynamicSpectrum


@pytest.fixture
def sample_spectrum():
    """Create a sample DynamicSpectrum for testing."""
    data = np.array([[1, 2, 3], [4, 5, 6]], dtype=float)
    freqs = np.array([100.0, 200.0])
    times = np.array([0.0, 1.0, 2.0])
    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=times)


class TestDynamicSpectrumCreation:
    """Tests for DynamicSpectrum creation and properties."""

    def test_create_basic(self):
        """Test basic creation with required fields."""
        data = np.zeros((5, 10))
        freqs = np.arange(5, dtype=float)
        times = np.arange(10, dtype=float)
        ds = DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=times)

        assert ds.data.shape == (5, 10)
        assert len(ds.freqs_mhz) == 5
        assert len(ds.time_s) == 10

    def test_create_with_source(self):
        """Test creation with source path."""
        data = np.zeros((5, 10))
        freqs = np.arange(5, dtype=float)
        times = np.arange(10, dtype=float)
        source = Path("/path/to/file.fit")
        ds = DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=times, source=source)

        assert ds.source == source

    def test_create_with_meta(self):
        """Test creation with metadata."""
        data = np.zeros((5, 10))
        freqs = np.arange(5, dtype=float)
        times = np.arange(10, dtype=float)
        meta = {"station": "TEST", "date": "20230101"}
        ds = DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=times, meta=meta)

        assert ds.meta["station"] == "TEST"
        assert ds.meta["date"] == "20230101"

    def test_default_source_is_none(self):
        """Test that source defaults to None."""
        data = np.zeros((5, 10))
        freqs = np.arange(5, dtype=float)
        times = np.arange(10, dtype=float)
        ds = DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=times)

        assert ds.source is None

    def test_default_meta_is_empty(self):
        """Test that meta defaults to empty dict."""
        data = np.zeros((5, 10))
        freqs = np.arange(5, dtype=float)
        times = np.arange(10, dtype=float)
        ds = DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=times)

        assert len(ds.meta) == 0


class TestDynamicSpectrumShape:
    """Tests for shape property."""

    def test_shape_property(self, sample_spectrum):
        """Test shape returns correct dimensions."""
        assert sample_spectrum.shape == (2, 3)

    def test_shape_type(self, sample_spectrum):
        """Test shape returns tuple of ints."""
        shape = sample_spectrum.shape
        assert isinstance(shape, tuple)
        assert all(isinstance(x, int) for x in shape)


class TestDynamicSpectrumCopyWith:
    """Tests for copy_with method."""

    def test_copy_with_no_changes(self, sample_spectrum):
        """Copy with no changes should return equivalent object."""
        copy = sample_spectrum.copy_with()
        assert np.array_equal(copy.data, sample_spectrum.data)
        assert np.array_equal(copy.freqs_mhz, sample_spectrum.freqs_mhz)
        assert np.array_equal(copy.time_s, sample_spectrum.time_s)

    def test_copy_with_new_data(self, sample_spectrum):
        """Copy with new data should update data only."""
        new_data = np.zeros_like(sample_spectrum.data)
        copy = sample_spectrum.copy_with(data=new_data)

        assert np.array_equal(copy.data, new_data)
        assert np.array_equal(copy.freqs_mhz, sample_spectrum.freqs_mhz)

    def test_copy_with_new_freqs(self, sample_spectrum):
        """Copy with new freqs should update freqs only."""
        new_freqs = np.array([150.0, 250.0])
        copy = sample_spectrum.copy_with(freqs_mhz=new_freqs)

        assert np.array_equal(copy.freqs_mhz, new_freqs)
        assert np.array_equal(copy.data, sample_spectrum.data)

    def test_copy_with_new_time(self, sample_spectrum):
        """Copy with new time should update time only."""
        new_time = np.array([10.0, 11.0, 12.0])
        copy = sample_spectrum.copy_with(time_s=new_time)

        assert np.array_equal(copy.time_s, new_time)

    def test_copy_with_new_meta(self, sample_spectrum):
        """Copy with new meta should update meta."""
        new_meta = {"new_key": "new_value"}
        copy = sample_spectrum.copy_with(meta=new_meta)

        assert copy.meta["new_key"] == "new_value"

    def test_copy_with_multiple_changes(self, sample_spectrum):
        """Copy with multiple changes should update all specified fields."""
        new_data = np.ones((2, 3))
        new_source = Path("/new/path.fit")
        copy = sample_spectrum.copy_with(data=new_data, source=new_source)

        assert np.array_equal(copy.data, new_data)
        assert copy.source == new_source

    def test_copy_with_returns_new_object(self, sample_spectrum):
        """Copy should return a new object, not modify original."""
        copy = sample_spectrum.copy_with(data=np.zeros_like(sample_spectrum.data))

        assert copy is not sample_spectrum
        assert not np.array_equal(copy.data, sample_spectrum.data)


class TestDynamicSpectrumImmutability:
    """Tests for frozen dataclass behavior."""

    def test_cannot_modify_data(self, sample_spectrum):
        """Should not be able to assign new data."""
        with pytest.raises(Exception):  # FrozenInstanceError
            sample_spectrum.data = np.zeros((2, 3))

    def test_cannot_modify_freqs(self, sample_spectrum):
        """Should not be able to assign new freqs."""
        with pytest.raises(Exception):
            sample_spectrum.freqs_mhz = np.zeros(2)

    def test_cannot_modify_time(self, sample_spectrum):
        """Should not be able to assign new time."""
        with pytest.raises(Exception):
            sample_spectrum.time_s = np.zeros(3)

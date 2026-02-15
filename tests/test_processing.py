"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import numpy as np
from ecallistolib.models import DynamicSpectrum
from ecallistolib.processing import noise_reduce_mean_clip, background_subtract

def test_noise_reduce_mean_clip_basic():
    data = np.array([[1, 2, 3], [10, 10, 10]], dtype=float)  # (freq, time)
    ds = DynamicSpectrum(data=data, freqs_mhz=np.array([100, 200.0]), time_s=np.array([0, 1, 2]))

    out = noise_reduce_mean_clip(ds, clip_low=-1, clip_high=1, scale=None)

    # first row mean is 2 -> [-1, 0, 1] after subtraction
    assert np.allclose(out.data[0], [-1, 0, 1])
    # second row becomes [0, 0, 0]
    assert np.allclose(out.data[1], [0, 0, 0])


def test_background_subtract_basic():
    data = np.array([[1, 2, 3], [10, 10, 10]], dtype=float)  # (freq, time)
    ds = DynamicSpectrum(data=data, freqs_mhz=np.array([100, 200.0]), time_s=np.array([0, 1, 2]))

    out = background_subtract(ds)

    # first row mean is 2 -> [-1, 0, 1] after subtraction (no clipping)
    assert np.allclose(out.data[0], [-1, 0, 1])
    # second row becomes [0, 0, 0]
    assert np.allclose(out.data[1], [0, 0, 0])
    # Metadata should indicate the processing
    assert out.meta.get("processing", {}).get("method") == "background_subtract"


def test_background_subtract_preserves_shape():
    data = np.random.rand(50, 100)
    ds = DynamicSpectrum(data=data, freqs_mhz=np.linspace(100, 200, 50), time_s=np.linspace(0, 100, 100))

    out = background_subtract(ds)

    assert out.shape == ds.shape
    # Check that each row has mean ~0
    assert np.allclose(out.data.mean(axis=1), 0, atol=1e-10)


def test_noise_reduce_median_clip_basic():
    """Test median-based noise reduction."""
    from ecallistolib.processing import noise_reduce_median_clip

    data = np.array([[1, 2, 3], [10, 10, 10]], dtype=float)
    ds = DynamicSpectrum(data=data, freqs_mhz=np.array([100, 200.0]), time_s=np.array([0, 1, 2]))

    out = noise_reduce_median_clip(ds, clip_low=-1, clip_high=1, scale=None)

    # first row median is 2 -> [-1, 0, 1] after subtraction
    assert np.allclose(out.data[0], [-1, 0, 1])
    # second row becomes [0, 0, 0]
    assert np.allclose(out.data[1], [0, 0, 0])
    # Check metadata
    assert out.meta["noise_reduction"]["method"] == "median_subtract_clip"


def test_median_more_robust_to_outliers():
    """Test that median-based method is more robust to outliers than mean."""
    from ecallistolib.processing import noise_reduce_median_clip

    # Data with outlier at the end
    data = np.array([[1, 2, 3, 100]], dtype=float)  # Outlier: 100
    ds = DynamicSpectrum(data=data, freqs_mhz=np.array([100.0]), time_s=np.array([0, 1, 2, 3]))

    # Mean is (1+2+3+100)/4 = 26.5, so non-outliers become very negative
    mean_result = noise_reduce_mean_clip(ds, clip_low=-50, clip_high=100, scale=None)
    # Median is 2.5, so non-outliers stay closer to 0
    median_result = noise_reduce_median_clip(ds, clip_low=-50, clip_high=100, scale=None)

    # For median: values are [-1.5, -0.5, 0.5, 97.5]
    # For mean: values are [-25.5, -24.5, -23.5, 73.5]
    # Median method keeps non-outlier values closer to 0
    assert abs(median_result.data[0, 0]) < abs(mean_result.data[0, 0])


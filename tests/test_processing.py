"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.3
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

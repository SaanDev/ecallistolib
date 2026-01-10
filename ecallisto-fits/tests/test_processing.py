import numpy as np
from ecallisto_fits.models import DynamicSpectrum
from ecallisto_fits.processing import noise_reduce_mean_clip

def test_noise_reduce_mean_clip_basic():
    data = np.array([[1, 2, 3], [10, 10, 10]], dtype=float)  # (freq, time)
    ds = DynamicSpectrum(data=data, freqs_mhz=np.array([100, 200.0]), time_s=np.array([0, 1, 2]))

    out = noise_reduce_mean_clip(ds, clip_low=-1, clip_high=1, scale=None)

    # first row mean is 2 -> [-1, 0, 1] after subtraction
    assert np.allclose(out.data[0], [-1, 0, 1])
    # second row becomes [0, 0, 0]
    assert np.allclose(out.data[1], [0, 0, 0])

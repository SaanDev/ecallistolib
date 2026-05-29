import numpy as np
from ecallistolib.models import DynamicSpectrum
<<<<<<< HEAD
from ecallistolib.processing import mitigate_rfi_mad

def test_mitigate_rfi_mad():
=======
from ecallistolib.processing import mitigate_rfi

def test_mitigate_rfi():
>>>>>>> origin/feature/improvements-rfi-cli-11159646905103801913
    data = np.zeros((2, 100))
    # Add some noise
    np.random.seed(42)
    data += np.random.normal(0, 1, size=(2, 100))

    # Add a huge spike at index 50
    data[0, 50] = 1000.0
    data[1, 50] = 500.0

    ds = DynamicSpectrum(
        data=data,
        freqs_mhz=np.array([100.0, 200.0]),
        time_s=np.arange(100, dtype=float),
        source=None,
        meta={}
    )

<<<<<<< HEAD
    processed = mitigate_rfi_mad(ds, threshold=5.0)
=======
    processed = mitigate_rfi(ds)
>>>>>>> origin/feature/improvements-rfi-cli-11159646905103801913

    # Spike should be gone, replaced by something close to 0 (median)
    assert processed.data[0, 50] < 5.0
    assert processed.data[1, 50] < 5.0

    # Metadata should be recorded
    assert "rfi_mitigation" in processed.meta
<<<<<<< HEAD
    assert processed.meta["rfi_mitigation"]["method"] == "mad_clipping"
=======
    assert processed.meta["rfi_mitigation"]["method"] == "clean_rfi"
>>>>>>> origin/feature/improvements-rfi-cli-11159646905103801913

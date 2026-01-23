"""Utility to generate sample FITS data for testing."""

from pathlib import Path

import numpy as np
from astropy.io import fits


def create_sample_fits(
    output_path: str | Path,
    n_freq: int = 200,
    n_time: int = 3600,
    freq_start: float = 45.0,
    freq_end: float = 870.0,
    time_duration_s: float = 900.0,
    station: str = "SAMPLE",
    add_burst: bool = True,
) -> Path:
    """
    Create a sample e-CALLISTO FITS file for testing.

    Parameters
    ----------
    output_path : str or Path
        Output file path.
    n_freq : int
        Number of frequency channels.
    n_time : int
        Number of time samples.
    freq_start : float
        Start frequency in MHz.
    freq_end : float
        End frequency in MHz.
    time_duration_s : float
        Duration of observation in seconds.
    station : str
        Station name for metadata.
    add_burst : bool
        If True, add a simulated solar burst to the data.

    Returns
    -------
    Path
        Path to the created file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate frequency and time axes
    freqs = np.linspace(freq_start, freq_end, n_freq).astype(np.float64)
    times = np.linspace(0, time_duration_s, n_time).astype(np.float64)

    # Generate base noise data (resembling real callisto data)
    np.random.seed(42)  # For reproducibility
    data = np.random.normal(50, 5, (n_freq, n_time)).astype(np.float32)

    # Add frequency-dependent background
    freq_background = np.linspace(5, 15, n_freq)[:, np.newaxis]
    data += freq_background

    # Optionally add a simulated solar burst
    if add_burst:
        # Type III burst: drifting from high to low frequency
        t_center = n_time // 2
        for i, f in enumerate(freqs):
            # Drift rate: higher frequencies arrive first
            drift_delay = int((freq_end - f) / (freq_end - freq_start) * 100)
            t_burst = t_center + drift_delay
            if 0 <= t_burst < n_time:
                # Gaussian burst profile
                burst_width = 20
                burst = 30 * np.exp(-0.5 * ((np.arange(n_time) - t_burst) / burst_width) ** 2)
                data[i] += burst

    # Clip to valid range
    data = np.clip(data, 0, 255)

    # Create primary HDU with image data
    primary_hdu = fits.PrimaryHDU(data)
    primary_hdu.header["SIMPLE"] = True
    primary_hdu.header["BITPIX"] = -32
    primary_hdu.header["NAXIS"] = 2
    primary_hdu.header["NAXIS1"] = n_time
    primary_hdu.header["NAXIS2"] = n_freq
    primary_hdu.header["TELESCOP"] = station
    primary_hdu.header["INSTRUME"] = "e-CALLISTO"
    primary_hdu.header["DATE-OBS"] = "2024-01-01"
    primary_hdu.header["TIME-OBS"] = "12:00:00"
    primary_hdu.header["CONTENT"] = "Radio Spectrum"

    # Create binary table extension with frequency and time axes
    # e-CALLISTO format stores these as 2D arrays (1 row, n columns)
    col_freq = fits.Column(name="frequency", format=f"{n_freq}D", array=[freqs])
    col_time = fits.Column(name="time", format=f"{n_time}D", array=[times])
    table_hdu = fits.BinTableHDU.from_columns([col_freq, col_time])

    # Create HDU list and write
    hdul = fits.HDUList([primary_hdu, table_hdu])
    hdul.writeto(output_path, overwrite=True)

    return output_path


def create_test_data_set(output_dir: str | Path = "data") -> list[Path]:
    """
    Create a set of sample FITS files for testing.

    Returns a list of created file paths.
    """
    output_dir = Path(output_dir)
    created = []

    # Single file with burst
    created.append(create_sample_fits(
        output_dir / "SAMPLE_20240101_120000_01.fit.gz",
        add_burst=True,
    ))

    # File without burst (quiet sun)
    created.append(create_sample_fits(
        output_dir / "SAMPLE_20240101_121500_01.fit.gz",
        add_burst=False,
    ))

    # Different focus (for frequency combining)
    created.append(create_sample_fits(
        output_dir / "SAMPLE_20240101_120000_02.fit.gz",
        freq_start=20.0,
        freq_end=90.0,
        add_burst=True,
    ))

    return created


if __name__ == "__main__":
    import sys

    output_dir = sys.argv[1] if len(sys.argv) > 1 else "data"
    files = create_test_data_set(output_dir)
    print(f"Created {len(files)} sample FITS files:")
    for f in files:
        print(f"  - {f}")

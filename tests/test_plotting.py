"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend for testing

import numpy as np
import pytest
import matplotlib.pyplot as plt

from ecallistolib.models import DynamicSpectrum
from ecallistolib.plotting import (
    TimeAxisConverter,
    plot_dynamic_spectrum,
    plot_raw_spectrum,
    plot_background_subtracted,
)


@pytest.fixture
def sample_ds():
    """Create a simple dynamic spectrum for testing."""
    data = np.random.rand(10, 20).astype(float) * 100
    freqs = np.linspace(100, 200, 10)
    time_s = np.linspace(0, 100, 20)
    meta = {"ut_start_sec": 43200.0}  # 12:00:00
    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=time_s, meta=meta)


@pytest.fixture
def sample_ds_no_ut():
    """Create a simple dynamic spectrum without UT metadata."""
    data = np.random.rand(10, 20).astype(float) * 100
    freqs = np.linspace(100, 200, 10)
    time_s = np.linspace(0, 100, 20)
    return DynamicSpectrum(data=data, freqs_mhz=freqs, time_s=time_s, meta={})


class TestTimeAxisConverter:
    """Tests for TimeAxisConverter class."""

    def test_seconds_to_ut_basic(self):
        converter = TimeAxisConverter(ut_start_sec=43200.0)  # 12:00:00
        assert converter.seconds_to_ut(0) == "12:00"
        assert converter.seconds_to_ut(100) == "12:01"
        assert converter.seconds_to_ut(3661) == "13:01"

    def test_seconds_to_ut_wrap_around(self):
        converter = TimeAxisConverter(ut_start_sec=86000.0)  # 23:53:20
        result = converter.seconds_to_ut(1000)  # Should wrap around midnight
        assert result == "00:10"

    def test_ut_to_seconds_basic(self):
        converter = TimeAxisConverter(ut_start_sec=43200.0)  # 12:00:00
        assert converter.ut_to_seconds("12:00:00") == 0.0
        assert converter.ut_to_seconds("12:01:40") == 100.0
        assert converter.ut_to_seconds("13:01:01") == 3661.0

    def test_ut_to_seconds_fractional(self):
        converter = TimeAxisConverter(ut_start_sec=43200.0)
        assert converter.ut_to_seconds("12:00:30.5") == 30.5

    def test_from_dynamic_spectrum(self, sample_ds):
        converter = TimeAxisConverter.from_dynamic_spectrum(sample_ds)
        assert converter.ut_start_sec == 43200.0

    def test_from_dynamic_spectrum_missing_metadata(self, sample_ds_no_ut):
        with pytest.raises(ValueError, match="ut_start_sec"):
            TimeAxisConverter.from_dynamic_spectrum(sample_ds_no_ut)


class TestPlotDynamicSpectrum:
    """Tests for plot_dynamic_spectrum function."""

    def test_basic_plot(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds)
        assert fig is not None
        assert ax is not None
        assert im is not None
        plt.close(fig)

    def test_custom_figsize(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds, figsize=(12, 6))
        assert fig.get_figwidth() == 12
        assert fig.get_figheight() == 6
        plt.close(fig)

    def test_custom_vmin_vmax(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds, vmin=10, vmax=90)
        assert im.get_clim() == (10, 90)
        plt.close(fig)

    def test_custom_cmap(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds, cmap="magma")
        assert im.get_cmap().name == "magma"
        plt.close(fig)

    def test_no_colorbar(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds, show_colorbar=False)
        # Just ensure no exception
        assert fig is not None
        plt.close(fig)

    def test_custom_title(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds, title="Custom Title")
        assert ax.get_title() == "Custom Title"
        plt.close(fig)

    def test_time_format_seconds(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds, time_format="seconds")
        assert "s" in ax.get_xlabel().lower()
        plt.close(fig)

    def test_time_format_ut(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(sample_ds, time_format="ut")
        assert "ut" in ax.get_xlabel().lower()
        plt.close(fig)

    def test_existing_axes(self, sample_ds):
        fig, ax = plt.subplots()
        fig2, ax2, im = plot_dynamic_spectrum(sample_ds, ax=ax)
        assert ax2 is ax
        assert fig2 is fig
        plt.close(fig)

    def test_imshow_kwargs(self, sample_ds):
        fig, ax, im = plot_dynamic_spectrum(
            sample_ds, interpolation="bilinear", alpha=0.8
        )
        assert fig is not None
        plt.close(fig)


class TestPlotRawSpectrum:
    """Tests for plot_raw_spectrum function."""

    def test_basic_plot(self, sample_ds):
        fig, ax, im = plot_raw_spectrum(sample_ds)
        assert fig is not None
        assert ax.get_title() == "raw"  # No source file, uses suffix only
        plt.close(fig)

    def test_default_cmap(self, sample_ds):
        fig, ax, im = plot_raw_spectrum(sample_ds)
        assert im.get_cmap().name == "viridis"
        plt.close(fig)

    def test_custom_params(self, sample_ds):
        fig, ax, im = plot_raw_spectrum(
            sample_ds,
            title="My Raw",
            cmap="plasma",
            figsize=(10, 5),
            vmin=0,
            vmax=50,
        )
        assert ax.get_title() == "My Raw"
        assert im.get_cmap().name == "plasma"
        assert im.get_clim() == (0, 50)
        plt.close(fig)


class TestPlotBackgroundSubtracted:
    """Tests for plot_background_subtracted function."""

    def test_basic_plot(self, sample_ds):
        fig, ax, im = plot_background_subtracted(sample_ds)
        assert fig is not None
        assert ax.get_title() == "background_subtracted"  # No source file
        plt.close(fig)

    def test_default_cmap(self, sample_ds):
        fig, ax, im = plot_background_subtracted(sample_ds)
        # Default is diverging colormap
        assert im.get_cmap().name == "jet"
        plt.close(fig)

    def test_custom_params(self, sample_ds):
        fig, ax, im = plot_background_subtracted(
            sample_ds, vmin=-20, vmax=20, figsize=(8, 4)
        )
        assert im.get_clim() == (-20, 20)
        plt.close(fig)

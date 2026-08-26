from datetime import date, datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pytest

import ecallistolib.goes as goes_module
from ecallistolib.exceptions import GOESConnectionError, GOESDataError
from ecallistolib.goes import (
    GOESXRayData,
    fetch_goes_xray,
    load_goes_xray,
    preferred_goes_satellite_numbers,
)
from ecallistolib.models import DynamicSpectrum
from ecallistolib.plotting import plot_spectrum_with_goes


def _goes_data():
    return GOESXRayData.from_arrays(
        np.array(["2024-01-01T12:00", "2024-01-01T12:01", "2024-01-01T12:02"]),
        xrsa_flux_wm2=[2e-8, 4e-8, 3e-8],
        xrsb_flux_wm2=[2e-7, 3e-6, 4e-7],
        satellite_number=18,
    )


def _spectrum():
    return DynamicSpectrum(
        data=np.arange(12, dtype=float).reshape(3, 4),
        freqs_mhz=np.array([40.0, 30.0, 20.0]),
        time_s=np.array([0.0, 40.0, 80.0, 120.0]),
        meta={
            "observation_start": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            "ut_start_sec": 43200.0,
        },
    )


def test_goes_arrays_validate_and_slice():
    data = _goes_data()
    sliced = data.between(
        datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 12, 2, tzinfo=timezone.utc),
    )

    assert data.available_channels == ("xrsa", "xrsb")
    assert sliced.time_utc.size == 2
    assert np.nanmax(sliced.xrsb_flux_wm2) == pytest.approx(3e-6)


def test_dataframe_duck_adapter_without_pandas():
    class Frame:
        columns = ["xrsa_flux", "xrsb_flux"]
        index = np.array(["2024-01-01T12:00", "2024-01-01T12:01"])

        def __getitem__(self, key):
            return {
                "xrsa_flux": np.array([1e-8, 2e-8]),
                "xrsb_flux": np.array([1e-7, 2e-7]),
            }[key]

    data = load_goes_xray(Frame())

    assert data.available_channels == ("xrsa", "xrsb")
    assert data.meta["adapter"] == "dataframe"


def test_local_netcdf_adapter(tmp_path):
    netcdf4 = pytest.importorskip("netCDF4")
    path = tmp_path / "goes18.nc"
    with netcdf4.Dataset(path, "w") as dataset:
        dataset.createDimension("time", 3)
        time_var = dataset.createVariable("time", "f8", ("time",))
        time_var.units = "seconds since 2024-01-01 12:00:00 UTC"
        time_var[:] = [0, 60, 120]
        dataset.createVariable("xrsa_flux", "f8", ("time",))[:] = [1e-8, 2e-8, 3e-8]
        dataset.createVariable("xrsb_flux", "f8", ("time",))[:] = [1e-7, 2e-7, 3e-7]
        dataset.platform = "GOES-18"

    data = load_goes_xray(path)

    assert data.satellite_number == 18
    assert data.time_utc.size == 3
    assert data.xrsb_flux_wm2[-1] == pytest.approx(3e-7)


def test_preferred_satellites_are_era_aware():
    assert preferred_goes_satellite_numbers(datetime(2026, 1, 1))[:2] == (19, 18)
    assert preferred_goes_satellite_numbers(datetime(2015, 1, 1))[:3] == (15, 14, 13)
    assert preferred_goes_satellite_numbers(datetime(1998, 1, 1)) == (10, 9, 8)


def test_goes_overlay_and_stacked_plots():
    overlay = plot_spectrum_with_goes(
        _spectrum(), _goes_data(), layout="overlay", dpi=210
    )
    stacked = plot_spectrum_with_goes(
        _spectrum(), _goes_data(), layout="stacked", dpi=220
    )

    assert overlay.layout == "overlay"
    assert overlay.goes_axes["xrsa"] is overlay.goes_axes["xrsb"]
    assert overlay.goes_axes["xrsb"].get_yscale() == "log"
    assert stacked.layout == "stacked"
    assert stacked.goes_axes["xrsa"] is not stacked.goes_axes["xrsb"]
    assert len(stacked.figure.axes) >= 3
    assert overlay.figure.dpi == pytest.approx(210)
    assert stacked.figure.dpi == pytest.approx(220)
    plt.close(overlay.figure)
    plt.close(stacked.figure)


def test_stacked_plot_accepts_one_available_channel():
    goes = GOESXRayData.from_arrays(
        np.array(["2024-01-01T12:00", "2024-01-01T12:01"]),
        xrsb_flux_wm2=[1e-7, 2e-6],
    )
    result = plot_spectrum_with_goes(_spectrum(), goes, layout="stacked")

    assert tuple(result.goes_axes) == ("xrsb",)
    assert result.goes_axes["xrsb"].get_yscale() == "log"
    plt.close(result.figure)


def test_plotting_with_supplied_data_does_not_fetch(monkeypatch):
    monkeypatch.setattr(
        goes_module,
        "fetch_goes_for_spectrum",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network fetch invoked")),
    )
    result = plot_spectrum_with_goes(_spectrum(), _goes_data())
    plt.close(result.figure)


def test_plotting_fetches_matching_archive_data_when_omitted(monkeypatch):
    calls = []
    spectrum = _spectrum()

    def fake_fetch(spectrum, **kwargs):
        calls.append((spectrum, kwargs))
        return _goes_data()

    monkeypatch.setattr(goes_module, "fetch_goes_for_spectrum", fake_fetch)
    result = plot_spectrum_with_goes(
        spectrum,
        layout="overlay",
        fetch_kwargs={"retries": 1},
    )

    assert calls == [(spectrum, {"retries": 1})]
    assert result.goes_axes["xrsb"].get_yscale() == "log"
    plt.close(result.figure)


def test_plotting_propagates_clear_connection_error(monkeypatch):
    def offline(*_args, **_kwargs):
        raise GOESConnectionError(
            "Could not connect to the official NOAA/NCEI GOES XRS archive. "
            "Check the internet connection and try again."
        )

    monkeypatch.setattr(goes_module, "fetch_goes_for_spectrum", offline)

    with pytest.raises(GOESConnectionError, match="internet connection"):
        plot_spectrum_with_goes(_spectrum())


def test_fetch_selects_best_satellite_without_live_network(monkeypatch, tmp_path):
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    monkeypatch.setattr("requests.Session", FakeSession)
    monkeypatch.setattr(goes_module, "_import_netcdf4", lambda: object())
    monkeypatch.setattr(
        goes_module,
        "_download_day",
        lambda satellite, day, **kwargs: tmp_path / f"goes{satellite}.nc",
    )

    def fake_load(paths):
        satellite = int(paths[0].stem.replace("goes", ""))
        samples = 3 if satellite == 18 else 2
        return GOESXRayData.from_arrays(
            np.arange(samples).astype("timedelta64[m]") + np.datetime64("2024-01-01T12:00"),
            xrsa_flux_wm2=np.full(samples, 1e-7),
            xrsb_flux_wm2=np.full(samples, 1e-6),
            satellite_number=satellite,
        )

    monkeypatch.setattr(goes_module, "load_goes_xray", fake_load)
    result = fetch_goes_xray(
        datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 1, 12, 2, tzinfo=timezone.utc),
        satellite_numbers=[17, 18],
        cache_dir=tmp_path,
    )

    assert result.satellite_number == 18
    assert result.time_utc.size == 3


def test_fetch_cross_midnight_uses_both_days_and_explicit_satellite(monkeypatch, tmp_path):
    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    requested: list[tuple[int, date]] = []
    monkeypatch.setattr("requests.Session", FakeSession)
    monkeypatch.setattr(goes_module, "_import_netcdf4", lambda: object())

    def fake_download(satellite, day, **kwargs):
        requested.append((satellite, day))
        return tmp_path / f"goes{satellite}-{day}.nc"

    monkeypatch.setattr(goes_module, "_download_day", fake_download)
    monkeypatch.setattr(
        goes_module,
        "load_goes_xray",
        lambda paths: GOESXRayData.from_arrays(
            np.array(["2024-01-01T23:59", "2024-01-02T00:00", "2024-01-02T00:01"]),
            xrsb_flux_wm2=[1e-7, 2e-7, 3e-7],
        ),
    )

    result = fetch_goes_xray(
        datetime(2024, 1, 1, 23, 59, tzinfo=timezone.utc),
        datetime(2024, 1, 2, 0, 1, tzinfo=timezone.utc),
        satellite_numbers=17,
        cache_dir=tmp_path,
    )

    assert requested == [(17, date(2024, 1, 1)), (17, date(2024, 1, 2))]
    assert result.satellite_number == 17


def test_request_retries_then_succeeds():
    class Response:
        def raise_for_status(self):
            return None

    class Session:
        calls = 0

        def get(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls < 3:
                raise OSError("temporary")
            return Response()

    session = Session()
    response = goes_module._request_with_retries(
        session,
        "https://example.invalid/data.nc",
        timeout_s=1,
        retries=2,
    )

    assert isinstance(response, Response)
    assert session.calls == 3


def test_request_reports_unavailable_internet_connection():
    class Session:
        def get(self, *_args, **_kwargs):
            raise OSError("network unreachable")

    with pytest.raises(GOESConnectionError, match="official NOAA/NCEI"):
        goes_module._request_with_retries(
            Session(),
            "https://www.ncei.noaa.gov/data.nc",
            timeout_s=1,
            retries=1,
        )


def test_fetch_reports_unavailable_internet_connection(monkeypatch, tmp_path):
    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, *_args, **_kwargs):
            raise OSError("network unreachable")

    monkeypatch.setattr("requests.Session", Session)
    monkeypatch.setattr(goes_module, "_import_netcdf4", lambda: object())

    with pytest.raises(GOESConnectionError, match="internet connection is required"):
        fetch_goes_xray(
            datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 12, 2, tzinfo=timezone.utc),
            satellite_numbers=18,
            cache_dir=tmp_path,
            retries=0,
        )


def test_fetch_checks_netcdf_dependency_before_network(monkeypatch):
    def missing_netcdf():
        raise ImportError("Install ecallistolib[goes]")

    monkeypatch.setattr(goes_module, "_import_netcdf4", missing_netcdf)
    monkeypatch.setattr(
        "requests.Session",
        lambda: (_ for _ in ()).throw(AssertionError("network request started")),
    )

    with pytest.raises(ImportError, match=r"ecallistolib\[goes\]"):
        fetch_goes_xray(
            datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 12, 2, tzinfo=timezone.utc),
            satellite_numbers=18,
        )


@pytest.mark.parametrize("refresh", [False, True])
def test_download_replaces_corrupt_cache_and_honors_refresh(monkeypatch, tmp_path, refresh):
    satellite = 18
    day = date(2024, 1, 2)
    filename = "sci_xrsf-l2-avg1m_g18_d20240102_v2-2-1.nc"
    target = tmp_path / "goes18" / "2024" / "01" / filename
    target.parent.mkdir(parents=True)
    target.write_bytes(b"valid" if refresh else b"corrupt")

    class Response:
        text = filename

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            assert chunk_size > 0
            yield b"downloaded"

    class Session:
        calls = 0

        def get(self, *_args, **_kwargs):
            self.calls += 1
            return Response()

    def validate(path):
        if Path(path).read_bytes() == b"corrupt":
            raise GOESDataError("corrupt cache")
        return _goes_data()

    monkeypatch.setattr(goes_module, "_load_netcdf_path", validate)
    session = Session()
    result = goes_module._download_day(
        satellite,
        day,
        cache_root=tmp_path,
        refresh=refresh,
        timeout_s=1,
        retries=0,
        session=session,
    )

    assert result == target
    assert target.read_bytes() == b"downloaded"
    assert session.calls == 2


def test_ncei_legacy_archive_uses_science_xrsf_product():
    day = date(2019, 1, 2)
    directory = goes_module._archive_directory(15, day)
    pattern = goes_module._filename_pattern(15, day)

    assert "xrsf-l2-avg1m_science/2019/01" in directory
    assert pattern.fullmatch("sci_xrsf-l2-avg1m_g15_d20190102_v2-2-1.nc")


def test_coverage_validation_rejects_partial_interval():
    data = GOESXRayData.from_arrays(
        np.array(["2024-01-01T12:05", "2024-01-01T12:06"]),
        xrsb_flux_wm2=[1e-7, 2e-7],
    )

    with pytest.raises(GOESDataError, match="do not cover"):
        goes_module._validate_requested_coverage(
            data,
            datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            datetime(2024, 1, 1, 12, 10, tzinfo=timezone.utc),
        )

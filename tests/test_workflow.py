from datetime import date

import numpy as np

from conftest import create_sample_fits

import ecallistolib.workflow as workflow_module
from ecallistolib.processing import background_subtract
from ecallistolib.goes import GOESXRayData
from ecallistolib.workflow import SpectrumGroupKey, load_spectra


def test_load_spectra_groups_station_and_day(tmp_path):
    a = tmp_path / "ALPHA_20240101_120000_01.fit"
    b = tmp_path / "BETA_20240101_120000_01.fit"
    c = tmp_path / "ALPHA_20240102_120000_01.fit"
    for path in (a, b, c):
        create_sample_fits(path, n_freq=3, n_time=4, add_burst=False)

    collection = load_spectra([a, b, c])

    assert len(collection) == 3
    assert SpectrumGroupKey("ALPHA", date(2024, 1, 1)) in collection.groups
    assert len(collection.by_station("alpha")) == 2


def test_workflow_frequency_then_time_and_missing_focus_nan(tmp_path):
    paths = [
        tmp_path / "STAT_20240101_120000_01.fit",
        tmp_path / "STAT_20240101_120000_02.fit",
        tmp_path / "STAT_20240101_121500_01.fit",
    ]
    create_sample_fits(paths[0], n_freq=2, n_time=3, freq_start=10, freq_end=20, add_burst=False)
    create_sample_fits(paths[1], n_freq=2, n_time=3, freq_start=30, freq_end=40, add_burst=False)
    create_sample_fits(paths[2], n_freq=2, n_time=3, freq_start=10, freq_end=20, add_burst=False)

    spectrum = load_spectra(paths).single()

    assert spectrum.shape == (4, 6)
    assert np.all(np.isfinite(spectrum.data[:, :3]))
    assert np.all(np.isnan(spectrum.data[:2, 3:]))
    assert spectrum.time_s[3] == 900.0
    assert spectrum.meta["combined"]["order"] == ["frequency", "time"]
    assert spectrum.meta["combined"]["missing_focus_blocks"][0]["missing_focuses"] == ["02"]


def test_workflow_reads_each_source_once(monkeypatch, tmp_path):
    paths = [
        tmp_path / "STAT_20240101_120000_01.fit",
        tmp_path / "STAT_20240101_120000_02.fit",
    ]
    for index, path in enumerate(paths):
        create_sample_fits(
            path,
            n_freq=2,
            n_time=3,
            freq_start=10 + 20 * index,
            freq_end=20 + 20 * index,
            add_burst=False,
        )
    original = workflow_module.read_fits
    reads = []

    def counting_read(path):
        reads.append(path)
        return original(path)

    monkeypatch.setattr(workflow_module, "read_fits", counting_read)
    collection = load_spectra(paths)

    assert len(reads) == len(paths)
    processed = collection.apply(background_subtract)
    assert "processing" in processed.single().meta
    assert "processing" not in collection.single().meta


def test_collection_plot_with_goes_can_fetch(monkeypatch, tmp_path):
    path = tmp_path / "STAT_20240101_120000_01.fit"
    create_sample_fits(path, n_freq=3, n_time=4, add_burst=False)
    collection = load_spectra([path])
    key = next(iter(collection))
    spectrum = collection[key]
    start = np.datetime64(spectrum.start_datetime.replace(tzinfo=None), "ns")

    monkeypatch.setattr(
        "ecallistolib.goes.fetch_goes_for_spectrum",
        lambda *_args, **_kwargs: GOESXRayData.from_arrays(
            start + np.arange(3).astype("timedelta64[m]"),
            xrsa_flux_wm2=[1e-8, 2e-8, 3e-8],
            xrsb_flux_wm2=[1e-7, 2e-7, 3e-7],
        ),
    )

    result = collection.plot_with_goes(key, layout="overlay")
    assert result.layout == "overlay"
    result.figure.clear()

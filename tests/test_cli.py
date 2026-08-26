from types import SimpleNamespace

import pytest

from ecallistolib import cli
import ecallistolib.io as io_module
import ecallistolib.plotting as plotting_module
import ecallistolib.processing as processing_module


@pytest.mark.parametrize(
    ("mode", "processor_name"),
    [("mean", "noise_reduce_mean_clip"), ("median", "noise_reduce_median_clip")],
)
def test_cli_reduction_is_applied_once(monkeypatch, mode, processor_name):
    raw = object()
    reduced = object()
    calls = {"processor": 0, "plot": 0}

    monkeypatch.setattr(io_module, "read_fits", lambda _path: raw)

    def processor(value, *, clip_low, clip_high):
        assert value is raw
        assert (clip_low, clip_high) == (-5.0, 20.0)
        calls["processor"] += 1
        return reduced

    monkeypatch.setattr(processing_module, processor_name, processor)

    def plot(value, **kwargs):
        assert value is reduced
        assert kwargs["process"] == "raw"
        assert kwargs["dpi"] == 200
        calls["plot"] += 1
        return object(), object(), object()

    monkeypatch.setattr(plotting_module, "plot_dynamic_spectrum", plot)
    monkeypatch.setattr("matplotlib.pyplot.show", lambda: None)

    cli.cmd_plot(
        SimpleNamespace(
            file="observation.fit.gz",
            rfi=False,
            process=mode,
            clip_low=-5.0,
            clip_high=20.0,
            cmap="inferno",
            dpi=200,
            save=None,
        )
    )

    assert calls == {"processor": 1, "plot": 1}

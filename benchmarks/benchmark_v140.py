"""Repeatable v1.4 performance checks.

Run from the repository root with::

    python benchmarks/benchmark_v140.py

The reference implementation reproduces the v1.3 NumPy fallback. The check is
deliberately independent of SciPy so local and CI measurements are comparable.
"""

from __future__ import annotations

from dataclasses import dataclass
import statistics
import time
import tracemalloc

import numpy as np

import ecallistolib.processing as processing


@dataclass(frozen=True)
class Measurement:
    runtime_s: float
    peak_mib: float


def _measure(function, data: np.ndarray, repeats: int = 7) -> Measurement:
    function(data)
    runtimes: list[float] = []
    peaks: list[float] = []
    for _ in range(repeats):
        tracemalloc.start()
        started = time.perf_counter()
        function(data)
        runtimes.append(time.perf_counter() - started)
        _current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks.append(peak / (1024 * 1024))
    return Measurement(statistics.median(runtimes), max(peaks))


def _v13_numpy_rfi(data: np.ndarray) -> np.ndarray:
    """The allocation behavior of the v1.3 RFI NumPy fallback."""
    array = np.asarray(data, dtype=np.float32)
    padded = np.pad(array, ((1, 1), (1, 1)), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, (3, 3))
    filtered = np.nanmedian(windows, axis=(-2, -1))
    masked = processing._mask_hot_channels(array, 6.0)

    repaired = filtered.copy()
    for index in masked:
        if index <= 0:
            repaired[index] = repaired[1 if repaired.shape[0] > 1 else 0]
        elif index >= repaired.shape[0] - 1:
            repaired[index] = repaired[repaired.shape[0] - 2 if repaired.shape[0] > 1 else 0]
        else:
            repaired[index] = 0.5 * (repaired[index - 1] + repaired[index + 1])

    clipped = repaired.copy()
    highs = np.nanpercentile(clipped, 99.5, axis=1)
    for index in range(clipped.shape[0]):
        clipped[index] = np.minimum(clipped[index], highs[index])
    return np.asarray(clipped, dtype=np.float32)


def _v14_numpy_rfi(data: np.ndarray) -> np.ndarray:
    previous = processing._median_filter
    previous_checked = processing._median_filter_checked
    processing._median_filter = None
    processing._median_filter_checked = True
    try:
        return processing.clean_rfi(data).data
    finally:
        processing._median_filter = previous
        processing._median_filter_checked = previous_checked


def main() -> None:
    rng = np.random.default_rng(42)
    data = rng.normal(100.0, 3.0, size=(200, 3600)).astype(np.float32)
    data[37, ::17] += 120.0

    reference = _measure(_v13_numpy_rfi, data)
    current = _measure(_v14_numpy_rfi, data)
    memory_reduction = 1.0 - current.peak_mib / reference.peak_mib
    runtime_ratio = current.runtime_s / reference.runtime_s

    print(f"v1.3 reference: {reference.runtime_s:.4f}s, {reference.peak_mib:.1f} MiB")
    print(f"v1.4 current:   {current.runtime_s:.4f}s, {current.peak_mib:.1f} MiB")
    print(f"memory reduction: {memory_reduction:.1%}")
    print(f"runtime ratio:    {runtime_ratio:.3f}x")

    if memory_reduction < 0.25:
        raise SystemExit("Peak allocation did not improve by the required 25%.")
    if runtime_ratio > 1.10:
        raise SystemExit("Median runtime was more than 10% slower than v1.3.")


if __name__ == "__main__":
    main()

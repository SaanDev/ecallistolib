# ecallistolib

[![Python 3.10–3.14](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`ecallistolib` downloads, reads, combines, processes, and plots
[e-CALLISTO](http://www.e-callisto.org/) solar-radio FITS dynamic spectra.

Version 1.4.0 adds Analyzer-equivalent multi-band frequency combination,
station/day workflows, and GOES XRS retrieval and plotting while preserving the
v1.3 APIs and their return values.

## What is new in v1.4.0

- Frequency-combine two or more receiver bands with the e-CALLISTO FITS
  Analyzer 2.8.0 regularization and nearest-channel mapping algorithm.
- Inspect bands, gaps, overlaps, ranges, focus codes, and source files before
  combining with `describe_frequency_combination()`.
- Select `background`, `average`, `hatched`, or `zero` gap handling and `split`,
  `low`, `high`, or `reject` overlap handling.
- Read every FITS source once with `load_spectra()`, then group by station and
  UTC day, frequency-combine each timestamp, and time-combine on the true UTC
  timeline.
- Fetch matching science-quality one-minute GOES XRS data from the official
  NOAA/NCEI archive, with a clear error when the archive cannot be reached.
- Plot XRS-A and XRS-B over a spectrum or in three shared-UTC panels. Omitting
  the GOES argument retrieves the relevant interval automatically.
- Overlay one or more selected frequency-channel light curves directly on a
  dynamic spectrum.
- Set `dpi` consistently for notebook figures, saved plots, and CLI output.
- Lower NumPy RFI fallback peak allocation through chunked median reduction,
  in-place repair/clipping, and vectorized MAD replacement. The CLI now applies
  mean/median reduction exactly once.

See [CHANGELOG.md](CHANGELOG.md), [ROADMAP.md](ROADMAP.md), and the executable
[complete tutorial](notebooks/complete_tutorial.ipynb).

## Installation

Python 3.10 through 3.14 are supported.

```bash
pip install ecallistolib
```

Install only the extras needed by your workflow:

```bash
pip install "ecallistolib[download]"  # e-CALLISTO archive downloads
pip install "ecallistolib[plot]"      # Matplotlib plots
pip install "ecallistolib[rfi]"       # SciPy-accelerated RFI filtering
pip install "ecallistolib[goes]"      # NCEI GOES retrieval and netCDF
pip install "ecallistolib[all]"       # every optional feature
```

For an editable source install:

```bash
git clone https://github.com/saandev/ecallistolib.git
cd ecallistolib
pip install -e ".[all]"
```

The `[goes]` extra installs Requests, Beautiful Soup, netCDF4, and
platformdirs. Pandas and SunPy remain optional because their objects are
accepted through duck-typed adapters. Restart Python or the Jupyter kernel
after installing an extra into an already-running environment.

## Quick start

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("data/Arecibo-Observatory_20220302_173000_62.fit.gz")
fig, ax, image = ecl.plot_dynamic_spectrum(
    spectrum,
    process="noise_reduced",
    clip_percentiles=(5, 99),
    time_format="ut",
    dpi=200,
)
```

`DynamicSpectrum.data` has shape `(frequency, time)`. Its frequency axis is in
MHz, time axis is elapsed seconds, and absolute UTC timestamps are available as
`start_datetime` and `end_datetime` when present in the FITS header or filename.

## Analyzer-compatible frequency combination

The legacy two-path call still works:

```python
combined = ecl.combine_frequency("band_01.fit.gz", "band_02.fit.gz")
```

Version 1.4 also accepts an iterable or variadic set of two or more bands:

```python
bands = [
    "ALASKA-COHOE_20230615_140000_62.fit.gz",
    "ALASKA-COHOE_20230615_140000_63.fit.gz",
]

report = ecl.describe_frequency_combination(bands)
print(report.bands)
print(report.gaps, report.overlaps)

combined = ecl.combine_frequency(
    bands,
    gap_fill="background",
    overlap_policy="split",
    overlap_connection_mhz=None,
    time_atol=0.01,
)
```

Or pass extra paths positionally:

```python
combined = ecl.combine_frequency(path_1, path_2, path_3)
```

The combiner validates station/date/time, distinct focus codes, compatible FITS
headers, and matching time axes. It orients every band consistently, chooses
the finest source channel spacing, builds a descending regular frequency grid,
and maps each source by the Analyzer's nearest-channel method.

### Gap policies

| Policy | Result |
| --- | --- |
| `background` | Default. Interpolate between 25th-percentile traces from up to four neighboring rows on each side. |
| `average` | Fill every row in a gap with the average of the two neighboring background traces. |
| `hatched` | Leave gap rows as NaN, store a row mask, and hatch them in spectrum plots. |
| `zero` | Fill gap rows with zero. |

The `background` policy interpolates only internal missing frequency rows that
are bounded by measured source bands on both sides.

### Overlap policies

| Policy | Result |
| --- | --- |
| `split` | Default. Switch bands at the overlap midpoint or `overlap_connection_mhz`. |
| `low` | Prefer the lower-frequency band in the overlap. |
| `high` | Prefer the higher-frequency band in the overlap. |
| `reject` | Raise `CombineError` if any overlap is present. |

Every result records the algorithm version, source paths, regularized grid
spacing, report, gaps, fill policy, overlap policy, tolerance, and connection
frequency in `combined.meta["combined"]`.

The supplied Analyzer parity pair produces the expected 193×3600 result:

```python
pair = [
    "ALASKA-COHOE_20230615_140000_62.fit.gz",
    "ALASKA-COHOE_20230615_140000_63.fit.gz",
]
combined = ecl.combine_frequency(pair)
assert combined.shape == (193, 3600)
```

## Grouped station/day workflow

`load_spectra()` is the high-level entry point for mixed paths. Each source is
read once. Files are grouped by station and UTC day, receiver bands are combined
per timestamp, and timestamps are combined on their actual UTC offsets.

```python
from pathlib import Path
import ecallistolib as ecl

paths = sorted(Path("observations").glob("*.fit.gz"))
collection = ecl.load_spectra(
    paths,
    gap_fill="hatched",
    overlap_policy="split",
)

for key in collection:
    spectrum = collection[key]
    print(key.station, key.utc_date, spectrum.shape)

cohoe = collection.by_station("ALASKA-COHOE")
one_day = collection.single(station="ALASKA-COHOE")
print(one_day.meta["combined"]["segments"])
```

If one timestamp is missing a focus band seen elsewhere that day, the
corresponding time-frequency block stays NaN. The missing focus, timestamp, and
source history are recorded under `meta["combined"]["missing_focus_blocks"]`.
Unreadable or ungroupable inputs raise an error; paths are never silently
skipped.

Collections are immutable containers. Processing returns a new collection:

```python
cleaned = collection.apply(
    ecl.mitigate_rfi,
    kernel_time=3,
    kernel_freq=3,
    percentile_clip=99.5,
)
assert cleaned is not collection
```

## GOES XRS data

[NCEI recommends science-quality Level-2 data](https://www.ncei.noaa.gov/products/goes-1-15/space-weather-instruments)
where available. The retriever uses the one-minute XRS products for GOES-8
through GOES-15 and the corresponding
[GOES-R EXIS/XRS products](https://www.ncei.noaa.gov/products/goes-r-extreme-ultraviolet-xray-irradiance)
for GOES-16 through GOES-19, selects era-appropriate satellite candidates,
validates coverage, and returns the candidate with the best usable coverage.

Fetch the archive data explicitly when you want to inspect or reuse it:

```python
goes = ecl.fetch_goes_for_spectrum(
    one_day,
    cache_dir="~/.cache/my-solar-project",  # optional override
    refresh=False,
    retries=2,
)

# Force a satellite or provide fallback order.
goes_18 = ecl.fetch_goes_for_spectrum(one_day, satellite_numbers=18)
goes_fallback = ecl.fetch_goes_for_spectrum(one_day, satellite_numbers=[18, 17, 16])
```

`fetch_goes_xray(start_utc, end_utc, ...)` supports arbitrary UTC intervals,
including cross-midnight windows. The default persistent cache uses the
platform's user cache directory. Cached netCDF files are validated before use;
`refresh=True` redownloads them. A corrupt cache is replaced after a successful
download.

If the requested files are not already cached, an internet connection is
required. Connection failures raise `GOESConnectionError`, while missing or
invalid archive products raise `GOESDownloadError`:

```python
try:
    goes = ecl.fetch_goes_for_spectrum(one_day)
except ecl.GOESConnectionError as error:
    print(f"GOES archive unavailable: {error}")
```

### Previously downloaded GOES data

Official netCDF files downloaded earlier can be loaded directly. Array,
DataFrame, and SunPy adapters remain available for advanced workflows, but the
tutorial plots use data retrieved from the NOAA/NCEI archive.

```python
from datetime import datetime, timezone
import ecallistolib as ecl

goes = ecl.GOESXRayData.from_arrays(
    [
        datetime(2023, 6, 15, 14, 0, tzinfo=timezone.utc),
        datetime(2023, 6, 15, 14, 1, tzinfo=timezone.utc),
    ],
    xrsa_flux_wm2=[2.0e-8, 4.0e-8],
    xrsb_flux_wm2=[2.0e-7, 3.0e-6],
    satellite_number=18,
)

local = ecl.load_goes_xray("cached_goes_file.nc")
many_days = ecl.load_goes_xray(["day1.nc", "day2.nc"])
from_dataframe = ecl.load_goes_xray(dataframe)
from_sunpy = ecl.load_goes_xray(timeseries)
```

Times are normalized to `datetime64[ns]`; positive XRS-A and XRS-B fluxes use
W/m². Either channel may be absent, but at least one valid channel is required.

## GOES plots

Omit the GOES argument to fetch the spectrum's matching UTC interval from the
official archive automatically. A cache hit is reused; otherwise this requires
an internet connection.

```python
try:
    overlay = ecl.plot_spectrum_with_goes(
        one_day,
        layout="overlay",
        process="background_subtracted",
        time_format="ut",
        dpi=200,
        save_path="spectrum_goes_overlay.png",
    )
except ecl.GOESConnectionError as error:
    print(f"Connect to the internet and try again: {error}")
```

The overlay uses a logarithmic right axis for both XRS channels. For a spectrum
plus separate XRS-A and XRS-B panels:

```python
try:
    stacked = ecl.plot_spectrum_with_goes(
        one_day,
        layout="stacked",
        clip_percentiles=(2, 99),
        dpi=200,
        save_path="spectrum_goes_stacked.png",
        fetch_kwargs={"retries": 2},
    )
except ecl.GOESConnectionError as error:
    print(f"Connect to the internet and try again: {error}")
```

The stacked layout shares the UTC axis, places each available XRS channel on its
own logarithmic panel, and adds A/B/C/M/X flare-class references to XRS-B. The
typed `SpectrumGOESPlot` result exposes `figure`, `spectrum_ax`, `goes_axes`,
`image`, and `layout`.

Collections provide matching fetch and plotting helpers:

```python
key = next(iter(collection))
goes = collection.fetch_goes(key)
plot = collection.plot_with_goes(key, layout="stacked")
```

## Processing

All processors return a new `DynamicSpectrum` and extend its metadata.

```python
mean_clean = ecl.noise_reduce_mean_clip(spectrum, clip_low=-5, clip_high=20)
median_clean = ecl.noise_reduce_median_clip(spectrum, clip_low=-5, clip_high=20)
background = ecl.background_subtract(spectrum)
frequency_background = ecl.background_subtract_frequency(spectrum)

rfi_clean = ecl.mitigate_rfi(
    spectrum,
    kernel_time=3,
    kernel_freq=3,
    channel_z_threshold=6,
    percentile_clip=99.5,
)
mad_clean = ecl.mitigate_rfi_mad(spectrum, threshold=3)
```

SciPy is loaded lazily when installed. Without it, the memory-bounded NumPy RFI
fallback is used automatically.

## Cropping and time combination

```python
frequency_slice = ecl.crop_frequency(spectrum, freq_min=45, freq_max=90)
time_slice = ecl.crop_time(spectrum, time_min=10, time_max=120)
both = ecl.crop(spectrum, freq_range=(45, 90), time_range=(10, 120))
indexed = ecl.slice_by_index(spectrum, freq_slice=slice(20, 80))

segments = [
    "data/Arecibo-Observatory_20220302_173000_62.fit.gz",
    "data/Arecibo-Observatory_20220302_174500_62.fit.gz",
]
timeline = ecl.combine_time(segments, timeline="actual")
```

`combine_time()` retains its backward-compatible contiguous default. Use
`timeline="actual"` to preserve real gaps, or `normalize_segment_time=True`
with the contiguous timeline when local time axes do not begin at zero.

## Downloading e-CALLISTO FITS files

```python
from datetime import date
import ecallistolib as ecl

remote = ecl.list_remote_fits(
    day=date(2023, 6, 15),
    hour=14,
    station_substring="alaska",
)
paths = ecl.download_files(
    remote,
    out_dir="observations",
    workers=4,
    retries=2,
    overwrite="skip",
)
```

For multi-day queries use `list_remote_fits_range(start_date, end_date,
hours=..., station_substring=..., error_policy="skip"|"raise")`.

## Plotting existing APIs

The v1.3 plotting signatures and tuple returns are unchanged:

```python
fig, ax, image = ecl.plot_dynamic_spectrum(spectrum, process="raw")
fig, ax, image = ecl.plot_raw_spectrum(spectrum)
fig, ax, image = ecl.plot_background_subtracted(spectrum)
fig, ax, line = ecl.plot_light_curve(spectrum, frequency_mhz=60)
```

Plots support `time_format="seconds"|"ut"`, `intensity_units="digits"|"dB"`,
explicit or percentile clip limits, custom axes, `save_path`, and `dpi`. The
same DPI controls both notebook display quality and saved-image resolution:

```python
fig, ax, image = ecl.plot_dynamic_spectrum(
    spectrum,
    dpi=240,
    save_path="high_quality_spectrum.png",
)
```

The dB option is a pseudo-calibration using
`Digits × 2500 / 256 / 25.4`; it is not a physical flux calibration.

### Light curves over a dynamic spectrum

Overlay one or more frequency-channel light curves on a right-hand intensity
axis. Dashed guides mark the selected channels on the spectrum:

```python
light_curve_plot = ecl.plot_spectrum_with_light_curves(
    spectrum,
    frequencies_mhz=[45, 60, 75],
    process="background_subtracted",
    time_format="ut",
    dpi=240,
    save_path="spectrum_with_light_curves.png",
)
print(light_curve_plot.frequencies_mhz)
```

## CLI

```bash
ecallisto download --date 2023-06-15 --hour 14 --station alaska --out-dir ./data
ecallisto plot spectrum.fit.gz --process mean --rfi --dpi 240 --save spectrum.png
ecallisto plot spectrum.fit.gz --process median --clip-low -3 --clip-high 15
```

The plot command supports `raw`, `mean`, `median`, and
`background_subtracted`. Mean and median reduction are performed once before
the result is rendered.

## API summary

| Area | Public APIs |
| --- | --- |
| Models and I/O | `DynamicSpectrum`, `CallistoFileParts`, `read_fits`, `parse_callisto_filename` |
| Frequency combination | `combine_frequency`, `can_combine_frequency`, `describe_frequency_combination`, `FrequencyBand`, `FrequencySpan`, `FrequencyCombinationReport` |
| Time and grouped workflow | `combine_time`, `can_combine_time`, `load_spectra`, `SpectrumCollection`, `SpectrumGroupKey` |
| GOES | `GOESXRayData`, `load_goes_xray`, `fetch_goes_xray`, `fetch_goes_for_spectrum`, `preferred_goes_satellite_numbers` |
| Plotting | `plot_dynamic_spectrum`, `plot_raw_spectrum`, `plot_background_subtracted`, `plot_light_curve`, `plot_spectrum_with_light_curves`, `SpectrumLightCurvePlot`, `plot_spectrum_with_goes`, `SpectrumGOESPlot`, `TimeAxisConverter` |
| Processing | `noise_reduce_mean_clip`, `noise_reduce_median_clip`, `background_subtract`, `background_subtract_frequency`, `mitigate_rfi`, `mitigate_rfi_mad` |
| Cropping | `crop`, `crop_frequency`, `crop_time`, `slice_by_index` |
| Download | `list_remote_fits`, `list_remote_fits_range`, `download_files` |

The exception hierarchy starts at `ECallistoError` and includes
`InvalidFITSError`, `InvalidFilenameError`, `DownloadError`, `CombineError`,
`CropError`, `WorkflowError`, `GOESError`, `GOESConnectionError`,
`GOESDownloadError`, and `GOESDataError`.

## Development and verification

```bash
python -m pytest -q
ruff check src tests
mypy src/ecallistolib --ignore-missing-imports --disable-error-code=import-untyped
python benchmarks/benchmark_v140.py
```

CI covers Python 3.10–3.14 and includes an offline `[goes]` job with netCDF4.
No live-network test is required.

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgments

- The [e-CALLISTO network](http://www.e-callisto.org/) and its station operators.
- NOAA/NCEI for the GOES XRS science-quality data products.
- The e-CALLISTO FITS Analyzer 2.8.0 implementation used as the v1.4 frequency-combination parity reference.

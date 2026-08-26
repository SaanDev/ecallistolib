# ecallistolib

[![Python 3.10-3.14](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library to **download**, **read**, **process**, and **plot** e-CALLISTO FITS dynamic spectra.

[e-CALLISTO](http://www.e-callisto.org/) (Compact Astronomical Low-frequency Low-cost Instrument for Spectroscopy and Transportable Observatory) is an international network of solar radio spectrometers that monitor solar radio emissions in the frequency range of approximately 45–870 MHz.

---

## What's new in v1.4.0

- **Analyzer-compatible multi-band frequency combination** — Combine two or more focus bands on a regular descending frequency grid, with configurable gap filling and overlap handling.
- **Combination reports and provenance** — Inspect bands, gaps, overlaps, source ranges, and channel spacing before combining with `describe_frequency_combination()`.
- **Grouped workflows** — `load_spectra()` reads each FITS file once, groups observations by station and UTC day, frequency-combines each timestamp, and then time-combines the results on the real UTC timeline.
- **GOES XRS integration** — Retrieve official science-quality one-minute XRS data from NOAA/NCEI, use a persistent local cache, or load compatible local/array/Pandas/SunPy data.
- **GOES plotting** — Display XRS-A and XRS-B over a dynamic spectrum or in separate shared-time panels.
- **Light-curve overlays** — Plot one or more frequency-channel light curves on the same figure as the dynamic spectrum.
- **Plot quality control** — All plotting helpers accept `dpi`, including saved figures and the command-line plot workflow.
- **Performance improvements** — Grouped workflows avoid repeated FITS reads, frequency operations reuse in-memory spectra, RFI operations are vectorized, and the CLI no longer applies mean/median reduction twice.
- **Backward compatibility** — Existing v1.3 reading, processing, combining, plotting, downloading, and CLI calls continue to work.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
  - [Reading FITS Files](#reading-fits-files)
  - [Downloading Data](#downloading-data)
  - [Processing Data](#processing-data)
  - [RFI Mitigation](#rfi-mitigation)
  - [Cropping & Slicing](#cropping--slicing)
  - [Combining Spectra](#combining-spectra)
  - [Grouped Station/Day Workflow](#grouped-stationday-workflow)
  - [GOES X-Ray Data](#goes-x-ray-data)
  - [Plotting](#plotting)
- [CLI](#cli)
- [API Reference](#api-reference)
  - [DynamicSpectrum](#dynamicspectrum)
  - [I/O Functions](#io-functions)
  - [Download Functions](#download-functions)
  - [Processing Functions](#processing-functions)
  - [RFI Mitigation Functions](#rfi-mitigation-functions)
  - [Cropping Functions](#cropping-functions)
  - [Combine Functions](#combine-functions)
  - [Workflow API](#workflow-api)
  - [GOES API](#goes-api)
  - [Plotting Functions](#plotting-functions)
  - [Exceptions](#exceptions)
- [Examples](#examples)
- [Data Format](#data-format)
- [Complete Tutorial](#complete-tutorial)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- 📥 **Download** – List and download FITS files directly from the e-CALLISTO data archive
- 📖 **Read** – Parse e-CALLISTO FITS files (`.fit`, `.fit.gz`) into structured Python objects
- 🕓 **Observation Datetimes** – Preserve absolute start/end timestamps when FITS headers or filenames provide them
- 🔧 **Process** – Apply noise reduction techniques (mean subtraction, clipping, scaling)
- 📡 **RFI Mitigation** – Remove Radio Frequency Interference with MAD-based and median-filter pipelines
- ✂️ **Crop** – Extract frequency and time ranges from spectra
- 🔗 **Combine** – Merge two or more focus bands with explicit gap and overlap policies, or concatenate timestamped observations along time
- 🗂️ **Organize** – Group many FITS files by station and UTC day with immutable processing and complete provenance
- ☀️ **GOES XRS** – Retrieve, cache, adapt, and plot official NOAA/NCEI X-ray flux data
- 📊 **Plot** – Generate publication-ready dynamic spectrum visualizations
- 📈 **Light Curves** – Plot individual light curves or overlay multiple selected frequencies on a dynamic spectrum
- 🖨️ **Output Quality** – Set figure DPI consistently across every plotting helper and the CLI
- 🕒 **Time Precision Control** – Convert seconds to UT in `HH:MM` or `HH:MM:SS`
- ⚡ **Efficient I/O** – Stream downloads and optimize multi-day remote listing queries
- 🛡️ **Reliability Enhancements** – Stricter parsing, typed combine failures, and safer metadata copying
- 💻 **CLI** – `ecallisto` command-line tool for downloading and plotting without writing Python
- ⚠️ **Error Handling** – Custom exceptions for robust error management

---

## Installation

Supported Python versions: **3.10-3.14**.


### From PyPI (Stable)

```bash
pip install ecallistolib
```

### Optional Dependencies

Install optional features as needed:

```bash
pip install "ecallistolib[download,plot]"

# For RFI mitigation (requires SciPy)
pip install "ecallistolib[rfi]"

# For official GOES XRS retrieval and local netCDF files
pip install "ecallistolib[goes]"

# For GOES retrieval and plotting together
pip install "ecallistolib[goes,plot]"

# Install all optional dependencies
pip install "ecallistolib[all]"
```
### From Source (Development)

```bash
git clone https://github.com/saandev/ecallistolib.git
cd ecallistolib
pip install -e .
```

### Development Extras

Install optional features as needed:

```bash
# For downloading data from the e-CALLISTO archive
pip install -e ".[download]"

# For plotting
pip install -e ".[plot]"

# For RFI mitigation (requires SciPy)
pip install -e ".[rfi]"

# For official GOES XRS retrieval and local netCDF files
pip install -e ".[goes]"

# Install all optional dependencies
pip install -e ".[all]"
```

---

## Quick Start

```python
import ecallistolib as ecl

# Read a FITS file. Replace the example name with your downloaded file.
spectrum = ecl.read_fits("STATION_20230101_120000_01.fit.gz")

# Plot with different processing modes
fig, ax, im = ecl.plot_dynamic_spectrum(
    spectrum,
    process="noise_reduced",
    clip_low=-5,
    clip_high=20,
    title="Solar Radio Observation",
    dpi=180,
)
```

---

## Usage Guide

### Reading FITS Files

The library can read standard e-CALLISTO FITS files:

```python
import ecallistolib as ecl

# Read a single FITS file
spectrum = ecl.read_fits("path/to/STATION_YYYYMMDD_HHMMSS_NN.fit.gz")

# Access the data
print(f"Data shape: {spectrum.shape}")          # (n_freq, n_time)
print(f"Frequencies: {spectrum.freqs_mhz}")     # Frequency axis in MHz
print(f"Time samples: {spectrum.time_s}")       # Time axis in seconds
print(f"Source file: {spectrum.source}")        # Original file path
print(f"Metadata: {spectrum.meta}")             # Station, date, etc.

# New in v1.0.0: Convenience properties
print(f"Num frequencies: {spectrum.n_freq}")    # Number of frequency channels
print(f"Num time samples: {spectrum.n_time}")   # Number of time samples
print(f"Duration: {spectrum.duration_s} s")     # Total observation duration
print(f"Freq range: {spectrum.freq_range_mhz}") # (min, max) frequency in MHz

# New in v1.2.0: Absolute observation datetimes when available
print(f"Observation start: {spectrum.start_datetime}")
print(f"Observation end: {spectrum.end_datetime}")
```

#### Parsing Filenames

Extract metadata from e-CALLISTO filenames:

```python
parts = ecl.parse_callisto_filename("STATION_20230615_143000_01.fit.gz")

print(parts.station)        # "STATION"
print(parts.date_yyyymmdd)  # "20230615"
print(parts.time_hhmmss)    # "143000"
print(parts.focus)          # "01"
```

---

### Downloading Data

Download FITS files directly from the e-CALLISTO archive:

```python
from datetime import date
import ecallistolib as ecl

# List available files for a specific day, hour, and station
remote_files = ecl.list_remote_fits(
    day=date(2023, 6, 15),
    hour=14,                    # UTC hour (0-23)
    station_substring="station-name"  # Case-insensitive station filter
)

print(f"Found {len(remote_files)} files:")
for rf in remote_files:
    print(f"  - {rf.name}: {rf.url}")

# Download the files
saved_paths = ecl.download_files(remote_files, out_dir="./data")

for path in saved_paths:
    print(f"Downloaded: {path}")
```

You can also enable retries, parallel workers, and overwrite behavior:

```python
saved_paths = ecl.download_files(
    remote_files,
    out_dir="./data",
    workers=4,               # Parallel downloads
    retries=2,               # Retry transient failures
    retry_backoff_s=0.5,     # Exponential backoff base
    overwrite="skip",        # "replace" (default), "skip", or "error"
)
```

#### Querying Multiple Days

List files over a date range with `list_remote_fits_range` (new in v1.0.0):

```python
from datetime import date
import ecallistolib as ecl

# List files from June 1-3, 2023, during hours 12-14 UTC
remote_files = ecl.list_remote_fits_range(
    start_date=date(2023, 6, 1),
    end_date=date(2023, 6, 3),
    hours=[12, 13, 14],          # Optional: specific UTC hours
    station_substring="station-name",
    error_policy="skip"          # "skip" (default) or "raise"
)

print(f"Found {len(remote_files)} files across 3 days")
```

Error handling behavior can be configured:

```python
# Raise immediately if any day listing fails:
remote_files = ecl.list_remote_fits_range(
    start_date=date(2023, 6, 1),
    end_date=date(2023, 6, 3),
    error_policy="raise",
)
```

---

### Processing Data

#### Noise Reduction

Apply mean-subtraction and clipping to enhance signal visibility:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Apply noise reduction with required clipping values
cleaned = ecl.noise_reduce_mean_clip(
    spectrum,
    clip_low=-5.0,              # Lower clipping threshold (required)
    clip_high=20.0,             # Upper clipping threshold (required)
    scale=2500.0 / 255.0 / 25.4 # Scaling factor (None to disable)
)

# Processing metadata is recorded
print(cleaned.meta["noise_reduction"])
# {'method': 'mean_subtract_clip', 'clip_low': -5.0, 'clip_high': 20.0, 'scale': 0.38598...}
```

**Algorithm Details:**
1. Subtract the mean intensity over time for each frequency channel (removes baseline)
2. Clip values to the specified range
3. Apply optional scaling factor

#### Background Subtraction Only

If you want to visualize the result before clipping is applied:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Apply only background subtraction (no clipping)
bg_subtracted = ecl.background_subtract(spectrum)

# This is equivalent to the first step of noise_reduce_mean_clip
# Each frequency channel now has zero mean
```

#### Median-Based Noise Reduction (v1.0.0)

For data with outliers, use median-based subtraction which is more robust:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Use median instead of mean (more robust to outliers)
cleaned = ecl.noise_reduce_median_clip(
    spectrum,
    clip_low=-5.0,
    clip_high=20.0
)

# Metadata shows the method used
print(cleaned.meta["noise_reduction"]["method"])  # 'median_subtract_clip'
```

---

### RFI Mitigation

Remove Radio Frequency Interference (RFI) from dynamic spectra. Two approaches are available:

#### Median-Filter Pipeline (Recommended)

A multi-step pipeline that applies 2D median filtering, detects and repairs hot channels, and clips residual outliers:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Apply full RFI mitigation pipeline
cleaned = ecl.mitigate_rfi(
    spectrum,
    kernel_time=3,             # Median filter kernel size (time axis)
    kernel_freq=3,             # Median filter kernel size (frequency axis)
    channel_z_threshold=6.0,   # Z-score threshold for hot-channel detection
    percentile_clip=99.5,      # Upper percentile clip per channel
)

# Check which channels were flagged
print(cleaned.meta["rfi_mitigation"]["masked_channel_indices"])
```

> **Note:** For best performance, install the `[rfi]` optional dependency (`pip install ecallistolib[rfi]`) which provides SciPy's optimized `median_filter`. A pure-NumPy fallback is used automatically when SciPy is not available.

#### MAD-Based Outlier Replacement

A simpler approach that uses the Median Absolute Deviation (MAD) to detect and replace impulsive spikes per frequency channel:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Replace outlier spikes with channel medians
cleaned = ecl.mitigate_rfi_mad(spectrum, threshold=3.0)

print(cleaned.meta["rfi_mitigation"])
# {'method': 'mad_clipping', 'threshold': 3.0}
```

#### Frequency-Axis Background Subtraction

Remove broad-band noise that affects all frequencies at a single time step:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Subtract mean over frequency for each time column
cleaned = ecl.background_subtract_frequency(spectrum)
```

#### Combining RFI Mitigation with Noise Reduction

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Step 1: Remove RFI
cleaned = ecl.mitigate_rfi(spectrum)

# Step 2: Apply noise reduction
processed = ecl.noise_reduce_mean_clip(cleaned, clip_low=-5.0, clip_high=20.0)

# Step 3: Plot
fig, ax, im = ecl.plot_dynamic_spectrum(processed, cmap="inferno")
```

---

### Cropping & Slicing

Extract specific frequency or time ranges from a spectrum:

#### Crop by Physical Values

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Crop to specific frequency range (in MHz)
cropped = ecl.crop_frequency(spectrum, freq_min=100, freq_max=300)

# Crop to specific time range (in seconds)
cropped = ecl.crop_time(spectrum, time_min=10, time_max=60)

# Crop both axes at once
cropped = ecl.crop(spectrum, freq_range=(100, 300), time_range=(10, 60))
```

#### Slice by Array Index

```python
# Get first 100 frequency channels
sliced = ecl.slice_by_index(spectrum, freq_slice=slice(0, 100))

# Get every other time sample (downsampling)
sliced = ecl.slice_by_index(spectrum, time_slice=slice(None, None, 2))

# Combine slices
sliced = ecl.slice_by_index(spectrum, freq_slice=slice(50, 150), time_slice=slice(0, 500))
```

#### Cropping Preserves Metadata

```python
cropped = ecl.crop(spectrum, freq_range=(100, 200))

# Check what was cropped
print(cropped.meta["cropped"])
# {'frequency': {'min': 100, 'max': 200}}
```

---

### Combining Spectra

#### Combine Along Frequency (Analyzer-Compatible)

`combine_frequency()` accepts the original two-file call, an iterable of two or
more paths, or variadic paths. The combiner validates station/date/time identity,
distinct focus codes, FITS frequency headers, and compatible time axes. It then
orients every band consistently, uses the finest input channel spacing, maps
channels by nearest neighbor, and produces one regular descending frequency grid.

```python
import ecallistolib as ecl

frequency_files = [
    "STATION_20230615_143000_01.fit.gz",
    "STATION_20230615_143000_02.fit.gz",
    "STATION_20230615_143000_03.fit.gz",
]

# Inspect the proposed combination without creating the combined spectrum.
report = ecl.describe_frequency_combination(frequency_files)
print(report.bands)
print(report.gaps)
print(report.overlaps)

if ecl.can_combine_frequency(
    frequency_files,
    gap_fill="background",
    overlap_policy="split",
):
    combined = ecl.combine_frequency(
        frequency_files,
        gap_fill="background",
        overlap_policy="split",
        time_atol=0.01,
    )
    print(f"Combined shape: {combined.shape}")
    print(combined.meta["combined"])
```

The existing two-path form remains valid:

```python
combined = ecl.combine_frequency("band_01.fit.gz", "band_02.fit.gz")
```

Gap policies:

| `gap_fill` | Result |
|------------|--------|
| `"background"` | Default. Builds 25th-percentile background traces from up to four neighboring rows on each side and interpolates between them across the missing frequencies. |
| `"average"` | Uses the average of the two neighboring background traces throughout the gap. |
| `"hatched"` | Leaves gap rows as `NaN` and records a row mask so plotting can hatch the missing region. |
| `"zero"` | Fills gap rows with zero. |

Overlap policies:

| `overlap_policy` | Result |
|------------------|--------|
| `"split"` | Default. Uses the lower band below the overlap midpoint and the higher band above it. Set `overlap_connection_mhz` to choose a custom split frequency. |
| `"low"` | Keeps the lower-frequency band's samples throughout the overlap. |
| `"high"` | Keeps the higher-frequency band's samples throughout the overlap. |
| `"reject"` | Raises `CombineError` if any bands overlap. |

`background` is an **interpolation** method for background traces; it does not
model burst features. Combination metadata records the algorithm identifier, source files,
grid spacing, gap mask/count, gap policy, overlap policy, connection frequency,
time tolerance, and the complete preflight report.

**Requirements for frequency combination:**

- At least two readable FITS files
- Same station, UTC date, and observation start time
- Distinct focus codes that agree with relevant FITS headers
- Matching time-axis shapes and values within `time_atol`
- Valid and consistent FITS frequency-range headers

#### Combine Along Time (Horizontal Concatenation)

Concatenate multiple spectra recorded consecutively:

```python
import ecallistolib as ecl

files = [
    "STATION_20230615_140000_01.fit.gz",
    "STATION_20230615_141500_01.fit.gz",
    "STATION_20230615_143000_01.fit.gz",
]

# Check compatibility
if ecl.can_combine_time(files):
    combined = ecl.combine_time(files, timeline="actual")
    print(f"Combined shape: {combined.shape}")
    print(f"Total duration: {combined.time_s[-1] - combined.time_s[0]:.1f} seconds")
    print(f"Timeline mode: {combined.meta['combined']['timeline']}")
```

Use `timeline="actual"` to preserve the real offsets between segment start times
from FITS headers or e-CALLISTO filenames:

```python
combined = ecl.combine_time(files, timeline="actual")
print(combined.meta["combined"]["segment_offsets_s"])
# [0.0, 900.0, 1800.0] for 15-minute segment spacing
```

If you prefer a gap-free synthetic timeline, `combine_time()` still defaults to
contiguous behavior. For edge cases where segment-local time axes do not start at
zero, use normalized alignment to avoid over-shifting:

```python
combined = ecl.combine_time(
    files,
    timeline="contiguous",
    normalize_segment_time=True,  # Opt-in corrected segment alignment
    freq_atol=0.02,               # Frequency compatibility tolerance
)
```

**Requirements for time combination:**
- Same station, date, and focus
- Matching frequency axes

---

### Grouped Station/Day Workflow

For a directory or list containing several focuses, timestamps, stations, or
UTC days, use `load_spectra()`. Each source is read once. Files are grouped by
station and UTC day; focus bands are frequency-combined at each timestamp before
the timestamps are combined on their actual UTC timeline.

```python
from pathlib import Path
import ecallistolib as ecl

paths = sorted(Path("data").glob("*.fit*"))
collection = ecl.load_spectra(
    paths,
    gap_fill="background",
    overlap_policy="split",
)

print(f"Groups: {len(collection)}")
for key in collection:
    grouped_spectrum = collection[key]
    print(key.station, key.utc_date, grouped_spectrum.shape)
    print(grouped_spectrum.meta["combined"])
```

Select an unambiguous group with `single()` or use a typed
`SpectrumGroupKey`:

```python
from datetime import date

key = ecl.SpectrumGroupKey("STATION", date(2023, 6, 15))
grouped_spectrum = collection[key]

# This is convenient when the collection contains exactly one matching group.
grouped_spectrum = collection.single(station="STATION", utc_date=date(2023, 6, 15))
```

`SpectrumCollection` is immutable. `apply()` returns a new collection and keeps
the original unchanged:

```python
processed_collection = collection.apply(
    ecl.noise_reduce_mean_clip,
    clip_low=-5.0,
    clip_high=20.0,
)
processed_spectrum = processed_collection[key]
```

If a timestamp is missing a focus band that is present elsewhere in the same
station/day group, its missing time-frequency block remains `NaN`. The block,
present/missing focuses, real time offsets, source paths, and processing order
are recorded under `spectrum.meta["combined"]`.

The collection also provides `by_station()`, `fetch_goes()`, `plot()`, and
`plot_with_goes()` helpers. GOES retrieval is always explicit when using
`fetch_goes()`; `plot_with_goes()` can accept supplied GOES data or retrieve it
automatically.

---

### GOES X-Ray Data

Install the GOES extra before using archive retrieval or local netCDF files:

```bash
pip install "ecallistolib[goes,plot]"
```

`fetch_goes_xray()` retrieves official science-quality one-minute XRS data from
the original NOAA/NCEI archive. It chooses era-appropriate GOES-8 through
GOES-19 candidates, validates coverage and channels, and returns the candidate
with the best usable coverage. The historical and GOES-R products are described
by [NOAA/NCEI GOES 1–15 XRS](https://www.ncei.noaa.gov/products/goes-1-15/space-weather-instruments)
and [NOAA/NCEI GOES-R EXIS/XRS](https://www.ncei.noaa.gov/products/goes-r-extreme-ultraviolet-xray-irradiance).

Fetch the exact observation interval of a spectrum:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("STATION_20230615_143000_01.fit.gz")

try:
    goes_data = ecl.fetch_goes_for_spectrum(spectrum, retries=2)
except ecl.GOESConnectionError as exc:
    print("GOES data could not be downloaded. Check the internet connection.")
    print(exc)
except ecl.GOESDownloadError as exc:
    print(f"No usable archive product was found: {exc}")
```

An internet connection is required when valid files for the interval are not
already cached. Connection, timeout, proxy, and SSL failures are reported as
`GOESConnectionError` with a clear message. Archive/product failures use
`GOESDownloadError`, while invalid or unsupported data use `GOESDataError`.

Fetch an explicit UTC interval or override the satellite candidates:

```python
from datetime import datetime, timezone
import ecallistolib as ecl

goes_data = ecl.fetch_goes_xray(
    datetime(2023, 6, 15, 14, 30, tzinfo=timezone.utc),
    datetime(2023, 6, 15, 15, 30, tzinfo=timezone.utc),
    satellite_numbers=(18, 17, 16),  # Or one integer, such as 18
    retries=2,
    timeout_s=30.0,
)

print(goes_data.satellite_number)
print(goes_data.available_channels)
print(goes_data.time_utc)
print(goes_data.xrsa_flux_wm2)
print(goes_data.xrsb_flux_wm2)
```

Downloaded files use a persistent platform-specific user cache. Configure it
with `cache_dir=...`, or use `refresh=True` to revalidate by downloading the
archive product again:

```python
goes_data = ecl.fetch_goes_for_spectrum(
    spectrum,
    cache_dir="data/goes-cache",
    refresh=False,
)
```

Load data without a network request from a previously downloaded netCDF file,
multiple netCDF files, a Pandas `DataFrame`, or a SunPy `TimeSeries`-like object:

```python
local_goes = ecl.load_goes_xray("data/goes_xrs.nc")
many_days = ecl.load_goes_xray(["day1.nc", "day2.nc"])
adapted = ecl.load_goes_xray(dataframe_or_timeseries)
```

Pandas and SunPy are accepted through duck-typed adapters and are not required
dependencies. For direct arrays, construct `GOESXRayData`:

```python
goes_data = ecl.GOESXRayData.from_arrays(
    time_utc=timestamps,
    xrsa_flux_wm2=xrsa_flux,
    xrsb_flux_wm2=xrsb_flux,
    satellite_number=18,
)
```

---

### Plotting

Create dynamic spectrum visualizations with selectable processing modes:

```python
import ecallistolib as ecl
import matplotlib.pyplot as plt

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Plot raw spectrum
fig, ax, im = ecl.plot_dynamic_spectrum(spectrum, process="raw")
plt.show()

# Plot noise-reduced spectrum with required clipping values
fig, ax, im = ecl.plot_dynamic_spectrum(
    spectrum,
    process="noise_reduced",     # Apply noise reduction
    clip_low=-5,                  # Lower clipping bound (required)
    clip_high=20,                 # Upper clipping bound (required)
    title="Type III Solar Burst",
    cmap="magma",
    figsize=(12, 6),
    dpi=200,
    interpolation="bilinear",
    save_path="spectrum.png",
    savefig_kwargs={"bbox_inches": "tight"},
)
plt.show()
```

You can also derive clip bounds from percentiles and save directly:

```python
fig, ax, im = ecl.plot_dynamic_spectrum(
    spectrum,
    process="noise_reduced",
    clip_percentiles=(5, 99),     # Used when clip_low/high are not provided
    dpi=180,
    save_path="plots/spectrum.png",
    savefig_kwargs={"bbox_inches": "tight"},
)
```

#### Plot Quality and Saving

Every library plotting helper accepts `dpi`. It controls the figure's display
resolution and becomes the default saved-image resolution when `save_path` is
used. A `dpi` inside `savefig_kwargs` overrides it for the saved file only.

```python
fig, ax, im = ecl.plot_raw_spectrum(
    spectrum,
    figsize=(12, 6),
    dpi=300,
    save_path="plots/high_quality_spectrum.png",
    savefig_kwargs={"bbox_inches": "tight"},
)
```

The same `dpi` parameter is available on `plot_dynamic_spectrum()`,
`plot_raw_spectrum()`, `plot_background_subtracted()`, `plot_light_curve()`,
`plot_spectrum_with_light_curves()`, and `plot_spectrum_with_goes()`.

#### Plotting Raw Data

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Plot raw spectrum without any processing
fig, ax, im = ecl.plot_raw_spectrum(
    spectrum,
    title="Raw Spectrum",
    cmap="viridis",
    figsize=(10, 5)
)
```

#### Plotting Background Subtracted (Before Clipping)

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Plot after background subtraction but before clipping
fig, ax, im = ecl.plot_background_subtracted(
    spectrum,
    clip_low=-10,
    clip_high=30,
    cmap="RdBu_r"  # Diverging colormap for +/- values
)
```

#### Time Axis Formats

Display time in seconds or Universal Time (UT):

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Default: time in seconds
ecl.plot_dynamic_spectrum(spectrum, time_format="seconds")

# Time in UT format (HH:MM)
ecl.plot_dynamic_spectrum(spectrum, time_format="ut")
```

#### Intensity Units

Choose between raw digital values (Digits/ADU) or pseudo-calibrated dB:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Default: intensity in Digits (raw ADU values)
ecl.plot_dynamic_spectrum(spectrum, intensity_units="digits")

# Convert to dB using: dB = Digits * 0.384 (pseudo-calibration)
ecl.plot_dynamic_spectrum(spectrum, intensity_units="dB")
```

> **Note:** The dB conversion uses the formula: dB = Digits × 2500 / 256 / 25.4 ≈ Digits × 0.384

#### Time Axis Converter

Convert between elapsed seconds and UT time programmatically:

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Create converter from spectrum metadata
converter = ecl.TimeAxisConverter.from_dynamic_spectrum(spectrum)

# Convert seconds to UT (default minute precision)
print(converter.seconds_to_ut(100))    # "12:01"
print(converter.seconds_to_ut(3661))   # "13:01"

# Request second precision when needed
print(converter.seconds_to_ut(100, precision="second"))   # "12:01:40"
print(converter.seconds_to_ut(3661, precision="second"))  # "13:01:01"

# Convert UT to seconds
print(converter.ut_to_seconds("12:01:40"))  # 100.0
print(converter.ut_to_seconds("13:00:00"))  # 3600.0
```

#### Using a Custom Axes

```python
import matplotlib.pyplot as plt
import ecallistolib as ecl

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

spectrum1 = ecl.read_fits("file1.fit.gz")
spectrum2 = ecl.read_fits("file2.fit.gz")

ecl.plot_dynamic_spectrum(spectrum1, process="raw", ax=axes[0], title="Raw")
ecl.plot_dynamic_spectrum(
    spectrum2,
    process="noise_reduced",
    ax=axes[1],
    title="Noise Reduced",
    clip_low=-5, clip_high=20
)

plt.tight_layout()
plt.show()
```

#### Light Curve Plotting

Plot intensity vs time at a specific frequency:

```python
import ecallistolib as ecl
import matplotlib.pyplot as plt

spectrum = ecl.read_fits("my_spectrum.fit.gz")

# Plot raw light curve at 60 MHz
fig, ax, line = ecl.plot_light_curve(spectrum, frequency_mhz=60, process="raw")
plt.show()

# Plot background-subtracted light curve
fig, ax, line = ecl.plot_light_curve(
    spectrum, frequency_mhz=60, process="background_subtracted"
)
plt.show()

# Plot noise-reduced light curve (must provide clip values)
fig, ax, line = ecl.plot_light_curve(
    spectrum,
    frequency_mhz=60,
    process="noise_reduced",
    clip_low=-5,
    clip_high=20,
    dpi=180,
)
plt.show()
```

Compare all three processing modes:

```python
import ecallistolib as ecl
import matplotlib.pyplot as plt

spectrum = ecl.read_fits("my_spectrum.fit.gz")

fig, axes = plt.subplots(3, 1, figsize=(12, 10))

ecl.plot_light_curve(spectrum, 60, process="raw", ax=axes[0], title="Raw")
ecl.plot_light_curve(spectrum, 60, process="background_subtracted", ax=axes[1], title="BG Sub")
ecl.plot_light_curve(
    spectrum, 60, process="noise_reduced", ax=axes[2], title="Noise Reduced",
    clip_low=-5, clip_high=20
)

plt.tight_layout()
plt.show()
```

#### Light Curves Over a Dynamic Spectrum

Overlay one or more frequency-channel light curves on a dynamic spectrum. The
frequency axis stays on the left, light-curve intensity uses a right axis, and
optional dashed guides identify the selected channels.

```python
result = ecl.plot_spectrum_with_light_curves(
    spectrum,
    frequencies_mhz=[60.0, 75.0, 90.0],
    process="background_subtracted",
    time_format="ut",
    cmap="inferno",
    dpi=220,
    show_frequency_guides=True,
    line_kwargs={"linewidth": 1.1, "alpha": 0.9},
    save_path="plots/spectrum_with_light_curves.png",
    savefig_kwargs={"bbox_inches": "tight"},
)

print(result.frequencies_mhz)  # Actual nearest channel frequencies used
print(result.figure)
print(result.spectrum_ax)
print(result.light_curve_ax)
print(result.lines)
```

Pass one float for a single curve. Noise-reduced overlays require `clip_low`
and `clip_high`, just like `plot_light_curve()`.

#### Dynamic Spectrum with GOES XRS

If `goes` is omitted, `plot_spectrum_with_goes()` fetches the matching official
NOAA/NCEI data. This requires internet access unless valid cached data already
cover the spectrum. Use `fetch_kwargs` to configure automatic retrieval.

```python
try:
    overlay = ecl.plot_spectrum_with_goes(
        spectrum,
        layout="overlay",
        dpi=220,
        fetch_kwargs={"retries": 2, "timeout_s": 30.0},
        save_path="plots/spectrum_goes_overlay.png",
    )
except ecl.GOESConnectionError as exc:
    print(f"Internet connection is unavailable: {exc}")
```

The `overlay` layout draws XRS-A and XRS-B on one logarithmic right axis over
the spectrum. The `stacked` layout uses separate spectrum, XRS-A, and XRS-B
panels sharing the same UTC axis; XRS-B includes A/B/C/M/X flare-class reference
levels.

```python
# Reuse already fetched data: this call performs no network request.
stacked = ecl.plot_spectrum_with_goes(
    spectrum,
    goes_data,
    layout="stacked",
    channels=("xrsa", "xrsb"),
    time_format="ut",
    dpi=220,
    save_path="plots/spectrum_goes_stacked.png",
    savefig_kwargs={"bbox_inches": "tight"},
)

print(stacked.layout)
print(stacked.spectrum_ax)
print(stacked.goes_axes)
```

`goes` may also be a local netCDF path, a list of paths, a compatible Pandas or
SunPy object, or a `GOESXRayData` instance. Both layouts return a typed
`SpectrumGOESPlot` containing the figure, spectrum axis, GOES axes, image, and
layout name. Hatched frequency gaps created with `gap_fill="hatched"` are drawn
automatically by the spectrum plotting layer.

---

## CLI

The `ecallisto` command-line tool provides quick access to downloading and plotting without writing Python scripts.

### Installation

The CLI is available automatically when you install ecallistolib:

```bash
pip install "ecallistolib[download,plot]"
```

### Download Files

```bash
# Download FITS files for a specific station, date, and hour
ecallisto download --date 2023-06-15 --hour 14 --station station-name --out-dir ./data
```

| Argument | Description |
|----------|-------------|
| `--date` | Date in `YYYY-MM-DD` format (required) |
| `--hour` | UTC hour 0–23 (required) |
| `--station` | Case-insensitive station substring (required) |
| `--out-dir` | Output directory (default: `./data`) |

### Plot a FITS File

```bash
# Plot raw spectrum
ecallisto plot my_spectrum.fit.gz

# Plot with noise reduction and RFI mitigation
ecallisto plot my_spectrum.fit.gz --process mean --rfi --save output.png

# Plot with median-based noise reduction and custom colormap
ecallisto plot my_spectrum.fit.gz --process median --clip-low -3 --clip-high 15 --cmap plasma --dpi 220
```

| Argument | Description |
|----------|-------------|
| `file` | Path to FITS file (required) |
| `--process` | Processing mode: `raw`, `mean`, `median`, or `background_subtracted` (default: `raw`) |
| `--rfi` | Apply RFI mitigation before processing |
| `--clip-low` | Lower clipping threshold (default: `-5.0`) |
| `--clip-high` | Upper clipping threshold (default: `20.0`) |
| `--cmap` | Matplotlib colormap (default: `inferno`) |
| `--dpi` | Display and saved-image resolution (default: `150`) |
| `--save` | Save plot to file instead of displaying interactively |

---

## API Reference

### DynamicSpectrum

The core data structure representing an e-CALLISTO dynamic spectrum.

```python
@dataclass(frozen=True)
class DynamicSpectrum:
    data: np.ndarray           # Intensity data, shape (n_freq, n_time)
    freqs_mhz: np.ndarray      # Frequency axis in MHz, shape (n_freq,)
    time_s: np.ndarray         # Time axis in seconds, shape (n_time,)
    source: Optional[Path]     # Original file path
    meta: Mapping[str, Any]    # Metadata dictionary
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `shape` | `tuple[int, int]` | Returns `(n_freq, n_time)` |
| `n_freq` | `int` | Number of frequency channels |
| `n_time` | `int` | Number of time samples |
| `duration_s` | `float` | Total observation duration in seconds |
| `start_datetime` | `datetime \| None` | Absolute observation start time in UTC when available |
| `end_datetime` | `datetime \| None` | Absolute observation end time in UTC when available |
| `freq_range_mhz` | `tuple[float, float]` | Frequency range as `(min, max)` in MHz |

#### Methods

| Method | Description |
|--------|-------------|
| `copy_with(**changes)` | Returns a new `DynamicSpectrum` with specified fields replaced |

---

### I/O Functions

#### `read_fits(path: str | Path) -> DynamicSpectrum`

Read an e-CALLISTO FITS file.

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str \| Path` | Path to the FITS file (`.fit` or `.fit.gz`) |

**Returns:** `DynamicSpectrum` object with data, frequencies, time, and metadata.

Metadata may include:
- `station`, `date`, `time`, `focus`
- `ut_start_sec`
- `observation_start`
- `observation_end`

---

#### `parse_callisto_filename(path: str | Path) -> CallistoFileParts`

Parse an e-CALLISTO filename.

**Returns:** `CallistoFileParts` with attributes:
- `station` – Station name
- `date_yyyymmdd` – Date string
- `time_hhmmss` – Time string
- `focus` – Focus/channel number

---

### Download Functions

#### `list_remote_fits(day, hour, station_substring, base_url=..., timeout_s=10.0) -> List[RemoteFITS]`

List available FITS files from the e-CALLISTO archive.

| Parameter | Type | Description |
|-----------|------|-------------|
| `day` | `date` | Target date |
| `hour` | `int` | UTC hour (0–23) |
| `station_substring` | `str` | Case-insensitive station filter |
| `base_url` | `str` | Archive base URL (optional) |
| `timeout_s` | `float` | Request timeout in seconds |

**Returns:** List of `RemoteFITS` objects with `name` and `url` attributes.

---

#### `download_files(items, out_dir, timeout_s=30.0, chunk_size=1048576, workers=1, retries=0, retry_backoff_s=0.5, overwrite="replace") -> list[Path]`

Download FITS files to a local directory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `items` | `Iterable[RemoteFITS]` | Files to download |
| `out_dir` | `str \| Path` | Output directory |
| `timeout_s` | `float` | Request timeout per file |
| `chunk_size` | `int` | Streaming chunk size in bytes |
| `workers` | `int` | Parallel workers (`1` keeps sequential behavior) |
| `retries` | `int` | Retry count for transient download failures |
| `retry_backoff_s` | `float` | Exponential backoff base in seconds |
| `overwrite` | `str` | `"replace"` (default), `"skip"`, or `"error"` when file exists |

**Returns:** List of saved file paths.

---

#### `list_remote_fits_range(start_date, end_date, hours=None, station_substring="", error_policy="skip", ...) -> List[RemoteFITS]`

List available FITS files over a date range (new in v1.0.0).

| Parameter | Type | Description |
|-----------|------|--------------|
| `start_date` | `date` | Start date (inclusive) |
| `end_date` | `date` | End date (inclusive) |
| `hours` | `Iterable[int] \| None` | UTC hours to include (0–23), or None for all |
| `station_substring` | `str` | Case-insensitive station filter |
| `error_policy` | `str` | `"skip"` to continue on failed days, `"raise"` to fail fast |

**Returns:** List of `RemoteFITS` objects across the date range.

---

### Processing Functions

#### `noise_reduce_mean_clip(ds, clip_low, clip_high, scale=0.385981...) -> DynamicSpectrum`

Apply noise reduction via mean subtraction and clipping.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Input spectrum |
| `clip_low` | `float` | — | Required lower clipping threshold |
| `clip_high` | `float` | — | Required upper clipping threshold |
| `scale` | `float \| None` | `~0.386` | Scaling factor (`None` to disable) |

**Returns:** New `DynamicSpectrum` with processed data and updated metadata.

---

#### `background_subtract(ds) -> DynamicSpectrum`

Subtract mean over time for each frequency channel (background subtraction only, no clipping).

| Parameter | Type | Description |
|-----------|------|-------------|
| `ds` | `DynamicSpectrum` | Input spectrum |

**Returns:** New `DynamicSpectrum` with background subtracted. Useful for visualizing data before clipping is applied.

---

#### `noise_reduce_median_clip(ds, clip_low, clip_high, scale=0.385981...) -> DynamicSpectrum`

Apply noise reduction via median subtraction and clipping (new in v1.0.0). More robust to outliers than mean-based method.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Input spectrum |
| `clip_low` | `float` | — | Lower clipping threshold |
| `clip_high` | `float` | — | Upper clipping threshold |
| `scale` | `float \| None` | `~0.386` | Scaling factor (`None` to disable) |

**Returns:** New `DynamicSpectrum` with processed data and updated metadata.

---

### RFI Mitigation Functions

#### `mitigate_rfi(ds, kernel_time=3, kernel_freq=3, channel_z_threshold=6.0, percentile_clip=99.5) → DynamicSpectrum`

Apply a multi-step RFI cleaning pipeline: 2D median filtering, hot-channel detection and repair, and per-channel percentile clipping.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Input spectrum |
| `kernel_time` | `int` | `3` | Median filter kernel size along time axis |
| `kernel_freq` | `int` | `3` | Median filter kernel size along frequency axis |
| `channel_z_threshold` | `float` | `6.0` | Robust Z-score threshold for hot-channel detection |
| `percentile_clip` | `float` | `99.5` | Upper percentile clip per channel |

**Returns:** New `DynamicSpectrum` with RFI mitigated and metadata recording `method`, kernel sizes, threshold, and `masked_channel_indices`.

---

#### `mitigate_rfi_mad(ds, threshold=3.0) → DynamicSpectrum`

Mitigate RFI using Median Absolute Deviation (MAD). Detects impulsive spikes per frequency channel and replaces them with the channel median.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Input spectrum |
| `threshold` | `float` | `3.0` | Number of MADs above median to flag as outlier |

**Returns:** New `DynamicSpectrum` with outlier values replaced.

---

#### `background_subtract_frequency(ds) → DynamicSpectrum`

Subtract mean over frequency for each time column. Removes broad-band noise that appears at a single time step across all frequencies.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ds` | `DynamicSpectrum` | Input spectrum |

**Returns:** New `DynamicSpectrum` with frequency-background subtracted.

---

#### `clean_rfi(data, *, kernel_time=3, kernel_freq=3, channel_z_threshold=6.0, percentile_clip=99.5, enabled=True) → RFIResult`

Low-level RFI cleaning function that operates on raw NumPy arrays. Returns an `RFIResult` dataclass with `data` and `masked_channel_indices`.
Import this lower-level helper with `from ecallistolib.processing import clean_rfi`.

---

### Cropping Functions

#### `crop_frequency(ds, freq_min=None, freq_max=None) -> DynamicSpectrum`

Crop a spectrum to a frequency range.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ds` | `DynamicSpectrum` | Input spectrum |
| `freq_min` | `float \| None` | Minimum frequency in MHz (inclusive) |
| `freq_max` | `float \| None` | Maximum frequency in MHz (inclusive) |

**Raises:** `CropError` if range is invalid or results in empty data.

---

#### `crop_time(ds, time_min=None, time_max=None) -> DynamicSpectrum`

Crop a spectrum to a time range.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ds` | `DynamicSpectrum` | Input spectrum |
| `time_min` | `float \| None` | Minimum time in seconds |
| `time_max` | `float \| None` | Maximum time in seconds |

**Raises:** `CropError` if range is invalid or results in empty data.

---

#### `crop(ds, freq_range=None, time_range=None) -> DynamicSpectrum`

Crop a spectrum along both axes at once.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ds` | `DynamicSpectrum` | Input spectrum |
| `freq_range` | `tuple \| None` | `(min, max)` frequency in MHz |
| `time_range` | `tuple \| None` | `(min, max)` time in seconds |

---

#### `slice_by_index(ds, freq_slice=None, time_slice=None) -> DynamicSpectrum`

Slice a spectrum by array indices.

| Parameter | Type | Description |
|-----------|------|-------------|
| `ds` | `DynamicSpectrum` | Input spectrum |
| `freq_slice` | `slice \| None` | Slice for frequency axis |
| `time_slice` | `slice \| None` | Slice for time axis |

---

### Combine Functions

#### `describe_frequency_combination(first, second=None, *additional, time_atol=0.01) -> FrequencyCombinationReport`

Validate two or more paths and report their ordered `bands`, `gaps`, and
`overlaps` without producing a combined array. `FrequencyBand` records each
source, station/date/time/focus, frequency range, and channel spacing.
`FrequencySpan` records each gap or overlap range and the adjacent source files.
The report also provides `has_gap`, `has_overlap`, and `to_dict()`.

---

#### `can_combine_frequency(first, second=None, *additional, time_atol=0.01, gap_fill="background", overlap_policy="split", overlap_connection_mhz=None) -> bool`

Return `True` when all paths can be read, validated, and combined with the
selected policies. It accepts either an iterable or the legacy/variadic path
form and returns `False` rather than raising for normal compatibility failures.

---

#### `combine_frequency(first, second=None, *additional, gap_fill="background", overlap_policy="split", overlap_connection_mhz=None, time_atol=0.01) -> DynamicSpectrum`

Combine two or more focus bands on one regular descending frequency grid.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `first` | `str \| Path \| Iterable[str \| Path]` | — | First path or an iterable containing every path |
| `second` | `str \| Path \| None` | `None` | Optional second path for backward compatibility |
| `*additional` | `str \| Path` | — | Additional variadic paths |
| `gap_fill` | `str` | `"background"` | `"background"`, `"average"`, `"hatched"`, or `"zero"` |
| `overlap_policy` | `str` | `"split"` | `"split"`, `"low"`, `"high"`, or `"reject"` |
| `overlap_connection_mhz` | `float \| None` | `None` | Custom connection frequency for `"split"`; midpoint when omitted |
| `time_atol` | `float` | `0.01` | Absolute tolerance for time-axis equality in seconds |

**Returns:** A `DynamicSpectrum` containing combined metadata, provenance, and
an explicit gap row mask when `gap_fill="hatched"`.

**Raises:** `CombineError` for incompatible inputs/policies and `ValueError`
for unsupported option values.

---

#### `can_combine_time(paths, freq_atol=0.01) -> bool`

Check if files can be combined along the time axis.

---

#### `combine_time(paths, timeline="contiguous", normalize_segment_time=False, freq_atol=0.01) -> DynamicSpectrum`

Concatenate spectra horizontally (time concatenation).

| Parameter | Type | Description |
|-----------|------|-------------|
| `paths` | `Iterable[str \| Path]` | Input FITS files |
| `timeline` | `str` | `"contiguous"` (default) or `"actual"` to preserve real segment offsets |
| `normalize_segment_time` | `bool` | Applies only to `timeline="contiguous"` |
| `freq_atol` | `float` | Absolute tolerance for frequency-axis compatibility |

---

### Workflow API

#### `load_spectra(paths, gap_fill="background", overlap_policy="split", overlap_connection_mhz=None, time_atol=0.01) -> SpectrumCollection`

Read each source once and group inputs by station/UTC day, combining frequency
before time.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `paths` | `Iterable[str \| Path]` | — | FITS sources to load; at least one is required |
| `gap_fill` | `str` | `"background"` | Frequency-gap policy used within timestamps |
| `overlap_policy` | `str` | `"split"` | Frequency-overlap policy used within timestamps |
| `overlap_connection_mhz` | `float \| None` | `None` | Optional custom split frequency |
| `time_atol` | `float` | `0.01` | Time-axis compatibility tolerance in seconds |

#### `SpectrumGroupKey`

Frozen, ordered key with `station: str` and `utc_date: date`. It can be used
directly with `collection[key]` and formats as `STATION/YYYY-MM-DD`.

#### `SpectrumCollection`

Frozen collection with read-only `groups`, ordered `sources`, and workflow
`meta`.

| Method | Description |
|--------|-------------|
| `collection[key]` | Return the `DynamicSpectrum` for a `SpectrumGroupKey` |
| `by_station(station)` | Return a read-only mapping for one station |
| `single(station=None, utc_date=None)` | Return exactly one matching group or raise `WorkflowError` |
| `apply(processor, **kwargs)` | Apply an immutable processor to every group and return a new collection |
| `fetch_goes(key, **kwargs)` | Explicitly fetch GOES XRS for one group |
| `plot(key, goes=None, **kwargs)` | Plot a group; uses GOES plotting when data are supplied |
| `plot_with_goes(key, goes=None, **kwargs)` | Plot with supplied GOES data or automatic archive retrieval |

---

### GOES API

#### `GOESXRayData`

Frozen normalized GOES XRS data in UTC and W/m².

| Attribute | Type | Description |
|-----------|------|-------------|
| `time_utc` | `np.ndarray` | UTC timestamps normalized to `datetime64[ns]` |
| `xrsa_flux_wm2` | `np.ndarray \| None` | XRS-A short-channel flux |
| `xrsb_flux_wm2` | `np.ndarray \| None` | XRS-B long-channel flux |
| `satellite_number` | `int \| None` | Selected GOES satellite |
| `sources` | `tuple[Path, ...]` | Local archive files used |
| `meta` | `Mapping[str, Any]` | Adapter/archive/cache provenance |

| Method/property | Description |
|-----------------|-------------|
| `from_arrays(...)` | Construct normalized data from UTC/flux arrays |
| `available_channels` | Return available channel names (`"xrsa"`, `"xrsb"`) |
| `flux(channel)` | Return one channel or raise `GOESDataError` |
| `between(start_utc, end_utc)` | Return an inclusive UTC subset |

#### `fetch_goes_xray(start_utc, end_utc, satellite_numbers=None, cache_dir=None, refresh=False, timeout_s=30.0, retries=2, progress_cb=None) -> GOESXRayData`

Fetch official science-quality one-minute GOES XRS data for a UTC interval,
including cross-midnight windows. Candidate satellites are era-aware unless an
integer or ordered sequence is supplied. Cached files are validated before use;
`refresh=True` downloads again. `progress_cb(percent, message)` is optional.

#### `fetch_goes_for_spectrum(ds, **kwargs) -> GOESXRayData`

Fetch the exact absolute UTC interval represented by a `DynamicSpectrum`.
The spectrum must provide `observation_start` metadata and a non-empty time axis.

#### `load_goes_xray(source) -> GOESXRayData`

Normalize a `GOESXRayData`, netCDF path/path iterable, Pandas `DataFrame`, or
SunPy `TimeSeries`-like object. Local netCDF parsing requires the `[goes]` extra.

#### `preferred_goes_satellite_numbers(value) -> tuple[int, ...]`

Return the era-aware preferred GOES candidate order for a date or datetime.

---

### Plotting Functions

#### `plot_dynamic_spectrum(ds, process="raw", clip_low=None, clip_high=None, clip_percentiles=None, title=None, cmap="inferno", figsize=None, dpi=None, ax=None, show_colorbar=True, time_format="seconds", intensity_units="digits", save_path=None, savefig_kwargs=None, **imshow_kwargs)`

Plot a dynamic spectrum with selectable processing mode.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Spectrum to plot |
| `process` | `str` | `"raw"` | Processing mode: `"raw"`, `"background_subtracted"`, or `"noise_reduced"` |
| `clip_low` | `float \| None` | `None` | Lower clipping bound (must be paired with `clip_high`) |
| `clip_high` | `float \| None` | `None` | Upper clipping bound (must be paired with `clip_low`) |
| `clip_percentiles` | `tuple[float, float] \| None` | `None` | Percentile-based clipping when explicit clip bounds are absent |
| `title` | `str \| None` | `None` | Plot title (auto-generated if `None`) |
| `cmap` | `str` | `"inferno"` | Matplotlib colormap |
| `figsize` | `tuple \| None` | `None` | Figure size as `(width, height)` in inches |
| `dpi` | `float \| None` | `None` | Positive display DPI and default saved-image DPI |
| `ax` | `Axes \| None` | `None` | Existing axes (creates new if `None`) |
| `show_colorbar` | `bool` | `True` | Whether to display colorbar |
| `time_format` | `str` | `"seconds"` | `"seconds"` or `"ut"` for time axis format |
| `intensity_units` | `str` | `"digits"` | `"digits"` (raw ADU) or `"dB"` (pseudo-calibrated) |
| `save_path` | `str \| Path \| None` | `None` | Optional output path to save the figure |
| `savefig_kwargs` | `dict \| None` | `None` | Optional kwargs passed to `Figure.savefig` |
| `**imshow_kwargs` | — | — | Additional kwargs passed to `matplotlib.imshow()` |

**Returns:** Tuple of `(fig, ax, im)`.

**Raises:** `ValueError` for invalid clipping inputs or missing clipping source in `process="noise_reduced"`.

---

#### `plot_raw_spectrum(ds, title=None, cmap="viridis", figsize=None, dpi=None, clip_low=None, clip_high=None, clip_percentiles=None, ax=None, show_colorbar=True, time_format="seconds", intensity_units="digits", save_path=None, savefig_kwargs=None, **imshow_kwargs)`

Convenience function that calls `plot_dynamic_spectrum` with `process="raw"`.

---

#### `plot_background_subtracted(ds, title=None, cmap="jet", figsize=None, dpi=None, clip_low=None, clip_high=None, clip_percentiles=None, ax=None, show_colorbar=True, time_format="seconds", intensity_units="digits", save_path=None, savefig_kwargs=None, **imshow_kwargs)`

Convenience function that calls `plot_dynamic_spectrum` with `process="background_subtracted"`.

---

#### `plot_light_curve(ds, frequency_mhz, process="raw", title=None, figsize=None, dpi=None, ax=None, time_format="seconds", clip_low=None, clip_high=None, intensity_units="digits", save_path=None, savefig_kwargs=None, **plot_kwargs)`

Plot a light curve (intensity vs time) at a specific frequency.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Spectrum to extract light curve from |
| `frequency_mhz` | `float` | — | Target frequency in MHz |
| `process` | `str` | `"raw"` | Processing mode: `"raw"`, `"background_subtracted"`, or `"noise_reduced"` |
| `title` | `str \| None` | `None` | Plot title (auto-generated if `None`) |
| `figsize` | `tuple \| None` | `None` | Figure size as `(width, height)` in inches |
| `dpi` | `float \| None` | `None` | Positive display DPI and default saved-image DPI |
| `ax` | `Axes \| None` | `None` | Existing axes (creates new if `None`) |
| `time_format` | `str` | `"seconds"` | `"seconds"` or `"ut"` for time axis format |
| `clip_low` | `float \| None` | `None` | Lower clip threshold (required for `"noise_reduced"`) |
| `clip_high` | `float \| None` | `None` | Upper clip threshold (required for `"noise_reduced"`) |
| `intensity_units` | `str` | `"digits"` | `"digits"` or pseudo-calibrated `"dB"` |
| `save_path` | `str \| Path \| None` | `None` | Optional output path |
| `savefig_kwargs` | `dict \| None` | `None` | Keyword arguments passed to `Figure.savefig` |
| `**plot_kwargs` | — | — | Additional kwargs passed to `matplotlib.plot()` |

**Returns:** Tuple of `(fig, ax, line)`.

**Raises:**
- `FrequencyOutOfRangeError` if frequency is outside spectrum's range.
- `ValueError` if `process="noise_reduced"` without `clip_low` and `clip_high`.

---

#### `plot_spectrum_with_light_curves(ds, frequencies_mhz, *, process="raw", time_format="seconds", intensity_units="digits", title=None, cmap="inferno", figsize=None, dpi=None, show_colorbar=True, clip_low=None, clip_high=None, show_frequency_guides=True, line_kwargs=None, save_path=None, savefig_kwargs=None, **imshow_kwargs) -> SpectrumLightCurvePlot`

Overlay one or more light curves on the dynamic spectrum using a separate right
intensity axis.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Spectrum to plot |
| `frequencies_mhz` | `float \| Sequence[float]` | — | One or more requested channel frequencies |
| `process` | `str` | `"raw"` | Shared processing for the image and curves |
| `time_format` | `str` | `"seconds"` | `"seconds"` or `"ut"` |
| `intensity_units` | `str` | `"digits"` | Curve/image intensity units |
| `dpi` | `float \| None` | `None` | Display and default saved-image DPI |
| `show_frequency_guides` | `bool` | `True` | Draw dashed guides at the actual selected channels |
| `line_kwargs` | `Mapping \| None` | `None` | Shared Matplotlib line options |
| `save_path` | `str \| Path \| None` | `None` | Optional output path |

**Returns:** `SpectrumLightCurvePlot` with `figure`, `spectrum_ax`,
`light_curve_ax`, `image`, `lines`, and actual `frequencies_mhz`.

---

#### `plot_spectrum_with_goes(ds, goes=None, *, layout="overlay", channels=("xrsa", "xrsb"), process="raw", time_format="ut", title=None, cmap="inferno", figsize=None, dpi=None, show_colorbar=True, clip_low=None, clip_high=None, clip_percentiles=None, save_path=None, savefig_kwargs=None, fetch_kwargs=None, **imshow_kwargs) -> SpectrumGOESPlot`

Plot GOES XRS with the dynamic spectrum. Omitting `goes` automatically calls
`fetch_goes_for_spectrum()`; supplying data or a local source avoids a network
request.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Spectrum with absolute observation metadata |
| `goes` | supported GOES source \| `None` | `None` | Data/local source, or automatic retrieval when omitted |
| `layout` | `str` | `"overlay"` | `"overlay"` or `"stacked"` |
| `channels` | `tuple[str, ...]` | `("xrsa", "xrsb")` | Requested available XRS channels |
| `process` | `str` | `"raw"` | Spectrum processing mode |
| `time_format` | `str` | `"ut"` | `"ut"` or elapsed `"seconds"` |
| `dpi` | `float \| None` | `None` | Display and default saved-image DPI |
| `fetch_kwargs` | `Mapping \| None` | `None` | Arguments for automatic archive retrieval; invalid when `goes` is supplied |
| `save_path` | `str \| Path \| None` | `None` | Optional output path |

`overlay` uses a logarithmic right flux axis. `stacked` creates shared-time
panels for the spectrum and each available requested channel. XRS-B plots show
GOES A/B/C/M/X flare-class reference levels.

**Returns:** `SpectrumGOESPlot` with `figure`, `spectrum_ax`, read-only
`goes_axes`, `image`, and `layout`.

**Raises:** `GOESConnectionError` for unavailable archive connectivity,
`GOESDownloadError` for archive retrieval failures, `GOESDataError` for invalid
GOES data, and `ValueError` for invalid layout/channel/plot inputs.

---

#### `TimeAxisConverter`

Convert between elapsed seconds and UT time.

```python
@dataclass
class TimeAxisConverter:
    ut_start_sec: float  # UT observation start in seconds since midnight
```

| Method | Description |
|--------|-------------|
| `seconds_to_ut(seconds, precision="minute")` | Convert elapsed seconds to UT string (`"minute"` -> HH:MM, `"second"` -> HH:MM:SS) |
| `ut_to_seconds(ut_str)` | Convert UT string to elapsed seconds |
| `from_dynamic_spectrum(ds)` | Create converter from spectrum metadata |

---

### Exceptions

The library provides a hierarchy of custom exceptions for robust error handling:

| Exception | Description |
|-----------|-------------|
| `ECallistoError` | Base exception for all library errors |
| `InvalidFITSError` | Raised when a FITS file is invalid or cannot be read |
| `InvalidFilenameError` | Raised when a filename doesn't match e-CALLISTO naming convention |
| `DownloadError` | Raised when downloading files from the archive fails |
| `CombineError` | Raised when spectra cannot be combined |
| `CropError` | Raised when cropping parameters are invalid |
| `FrequencyOutOfRangeError` | Raised when the requested frequency is outside the spectrum's range |
| `WorkflowError` | Raised when inputs cannot be grouped or a collection selection is ambiguous |
| `GOESError` | Base exception for GOES XRS operations |
| `GOESConnectionError` | Raised when the official archive cannot be reached |
| `GOESDownloadError` | Raised when no usable archive product can be retrieved |
| `GOESDataError` | Raised when GOES data are invalid, incomplete, or unsupported |

#### Error Handling Example

```python
import ecallistolib as ecl
from ecallistolib import InvalidFITSError, CropError

try:
    spectrum = ecl.read_fits("corrupted_file.fit")
except FileNotFoundError:
    print("File not found")
except InvalidFITSError as e:
    print(f"Invalid FITS file: {e}")

try:
    cropped = ecl.crop(spectrum, freq_range=(1000, 2000))  # Out of range
except CropError as e:
    print(f"Cropping failed: {e}")

try:
    goes_data = ecl.fetch_goes_for_spectrum(spectrum)
except ecl.GOESConnectionError as e:
    print(f"GOES archive is unreachable: {e}")
except ecl.GOESError as e:
    print(f"GOES operation failed: {e}")
```

---

## Examples

### Complete Workflow

```python
from datetime import date
import ecallistolib as ecl
import matplotlib.pyplot as plt

# 1. Download data
remote = ecl.list_remote_fits(
    date(2023, 6, 15),
    hour=12,
    station_substring="station-name",
)
paths = ecl.download_files(remote, out_dir="./data", workers=4, retries=2)

# 2. Read once, group, frequency-combine, then time-combine
collection = ecl.load_spectra(paths)
spectrum = collection.single()

# 3. Process immutably
processed_collection = collection.apply(
    ecl.noise_reduce_mean_clip,
    clip_low=-5.0,
    clip_high=20.0,
)
cleaned = processed_collection.single()

# 4. Plot
fig, ax, im = ecl.plot_dynamic_spectrum(
    cleaned,
    title=f"e-CALLISTO Observation - {spectrum.meta.get('station', 'Unknown')}",
    cmap="plasma",
    dpi=200,
    save_path="observation.png",
    savefig_kwargs={"bbox_inches": "tight"},
)
plt.show()
```

### Working with Metadata

```python
import ecallistolib as ecl

spectrum = ecl.read_fits("my_file.fit.gz")

# Access metadata
print(f"Station: {spectrum.meta.get('station')}")
print(f"Date: {spectrum.meta.get('date')}")
print(f"UT Start: {spectrum.meta.get('ut_start_sec')} seconds")
print(f"Observation start: {spectrum.start_datetime}")
print(f"Observation end: {spectrum.end_datetime}")

# After processing, metadata is preserved and extended
processed = ecl.noise_reduce_mean_clip(spectrum, clip_low=-5.0, clip_high=20.0)
print(f"Processing applied: {processed.meta.get('noise_reduction')}")
```

---

## Data Format

e-CALLISTO FITS files follow a standard naming convention:

```
STATION_YYYYMMDD_HHMMSS_NN.fit.gz
```

| Field | Description |
|-------|-------------|
| `STATION` | Observatory/station name |
| `YYYYMMDD` | Observation date |
| `HHMMSS` | Observation start time (UTC) |
| `NN` | Focus/channel number (typically `01` or `02`) |

The FITS files contain:
- **Primary HDU**: 2D array of intensity values
- **Extension 1**: Binary table with `frequency` and `time` axes

---

## Complete Tutorial

The full runnable tutorial keeps the earlier-version examples and adds the
v1.4.0 methods beneath the related sections: multi-band frequency combination,
grouped workflows, GOES download/cache/offline handling, both GOES layouts,
light-curve overlays, and plot DPI.

Open
[notebooks/complete_tutorial.ipynb](https://github.com/SaanDev/ecallistolib/blob/main/notebooks/complete_tutorial.ipynb)
on GitHub or run it locally with Jupyter after installing the optional extras:

```bash
pip install "ecallistolib[all]" jupyter
jupyter notebook notebooks/complete_tutorial.ipynb
```

The notebook uses generalized e-CALLISTO filenames. Replace example paths and
station filters with your own downloaded observations.

Release history is available in the
[changelog](https://github.com/SaanDev/ecallistolib/blob/main/CHANGELOG.md), and
planned post-v1.4 work is listed in the
[roadmap](https://github.com/SaanDev/ecallistolib/blob/main/ROADMAP.md).

---

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Running Tests

```bash
pip install pytest
pytest
```

---

## License

This project is licensed under the MIT License. See the
[LICENSE](https://github.com/SaanDev/ecallistolib/blob/main/LICENSE) file for details.

---

## Acknowledgments

- [e-CALLISTO Network](http://www.e-callisto.org/) for providing open access to solar radio data
- [Astropy](https://www.astropy.org/) for FITS file handling

---

## Links

- **Source code**: https://github.com/SaanDev/ecallistolib
- **Issue tracker**: https://github.com/SaanDev/ecallistolib/issues
- **e-CALLISTO Data Archive**: http://soleil80.cs.technik.fhnw.ch/solarradio/data/2002-20yy_Callisto/
- **e-CALLISTO Homepage**: http://www.e-callisto.org/
- **NOAA/NCEI GOES 1–15 XRS**: https://www.ncei.noaa.gov/products/goes-1-15/space-weather-instruments
- **NOAA/NCEI GOES-R EXIS/XRS**: https://www.ncei.noaa.gov/products/goes-r-extreme-ultraviolet-xray-irradiance

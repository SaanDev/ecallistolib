# ecallistolib

[![Python 3.10-3.14](https://img.shields.io/badge/python-3.10--3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library to **download**, **read**, **process**, and **plot** e-CALLISTO FITS dynamic spectra.

[e-CALLISTO](http://www.e-callisto.org/) (Compact Astronomical Low-frequency Low-cost Instrument for Spectroscopy and Transportable Observatory) is an international network of solar radio spectrometers that monitor solar radio emissions in the frequency range of approximately 45–870 MHz.

---

## 🆕 What's New in v1.2.0

- **Timestamp-aware time combination** — `combine_time(..., timeline="actual")` preserves real offsets between observation segments.
- **Observation datetime metadata** — `read_fits()` now records `observation_start` / `observation_end`, with `DynamicSpectrum.start_datetime` and `.end_datetime` convenience properties.
- **Richer time-combine metadata** — merged spectra now record `meta["combined"]["timeline"]` and `segment_offsets_s`.
- **Download reliability + ergonomics** — `download_files(..., workers=..., retries=..., retry_backoff_s=..., overwrite=...)`.
- **Plotting UX upgrades** — `clip_percentiles=(low, high)` and direct export via `save_path` + `savefig_kwargs`.
- **Runtime support expansion** — officially supported Python versions are now `3.10-3.14`.
- **Stability-first defaults preserved** — `combine_time()` still defaults to contiguous legacy-compatible behavior unless you opt into `timeline="actual"`.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
  - [Reading FITS Files](#reading-fits-files)
  - [Downloading Data](#downloading-data)
  - [Processing Data](#processing-data)
  - [Cropping & Slicing](#cropping--slicing)
  - [Combining Spectra](#combining-spectra)
  - [Plotting](#plotting)
- [API Reference](#api-reference)
  - [DynamicSpectrum](#dynamicspectrum)
  - [I/O Functions](#io-functions)
  - [Download Functions](#download-functions)
  - [Processing Functions](#processing-functions)
  - [Cropping Functions](#cropping-functions)
  - [Combine Functions](#combine-functions)
  - [Plotting Functions](#plotting-functions)
  - [Exceptions](#exceptions)
- [Examples](#examples)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- 📥 **Download** – List and download FITS files directly from the e-CALLISTO data archive
- 📖 **Read** – Parse e-CALLISTO FITS files (`.fit`, `.fit.gz`) into structured Python objects
- 🕓 **Observation Datetimes** – Preserve absolute start/end timestamps when FITS headers or filenames provide them
- 🔧 **Process** – Apply noise reduction techniques (mean subtraction, clipping, scaling)
- ✂️ **Crop** – Extract frequency and time ranges from spectra
- 🔗 **Combine** – Merge multiple spectra along the time or frequency axis, including timestamp-aware time merges
- 📊 **Plot** – Generate publication-ready dynamic spectrum visualizations
- 🕒 **Time Precision Control** – Convert seconds to UT in `HH:MM` or `HH:MM:SS`
- ⚡ **Efficient I/O** – Stream downloads and optimize multi-day remote listing queries
- 🛡️ **Reliability Enhancements** – Stricter parsing, typed combine failures, and safer metadata copying
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
pip install ecallistolib"[download,plot]"
```
### From Source (Development)

```bash
git clone https://github.com/saandev/ecallistolib.git
cd ecallistolib
pip install -e .
```

### Optional Dependencies

Install optional features as needed:

```bash
# For downloading data from the e-CALLISTO archive
pip install -e ".[download]"

# For plotting
pip install -e ".[plot]"

# Install all optional dependencies
pip install -e ".[download,plot]"
```

---

## Quick Start

```python
import ecallistolib as ecl

# Read a FITS file
spectrum = ecl.read_fits("ALASKA_20230101_120000_01.fit.gz")

# Plot with different processing modes
fig, ax, im = ecl.plot_dynamic_spectrum(
    spectrum, 
    process="noise_reduced",
    clip_low=-5, 
    clip_high=20,
    title="Solar Radio Burst"
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
parts = ecl.parse_callisto_filename("ALASKA_20230615_143000_01.fit.gz")

print(parts.station)        # "ALASKA"
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
    station_substring="alaska"  # Case-insensitive station filter
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
    station_substring="alaska",
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
# {'method': 'mean_subtract_clip', 'clip_low': -5.0, 'clip_high': 20.0, 'scale': 3.88...}
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

#### Combine Along Frequency (Vertical Stacking)

Combine two spectra from the same observation but different frequency bands (e.g., focus 01 and 02):

```python
import ecallistolib as ecl

# Check if files can be combined
if ecl.can_combine_frequency("file_01.fit.gz", "file_02.fit.gz"):
    combined = ecl.combine_frequency("file_01.fit.gz", "file_02.fit.gz")
    print(f"Combined shape: {combined.shape}")
```

**Requirements for frequency combination:**
- Same station, date, and time
- Different focus numbers (01 vs 02)
- Matching time axes

#### Combine Along Time (Horizontal Concatenation)

Concatenate multiple spectra recorded consecutively:

```python
import ecallistolib as ecl

files = [
    "ALASKA_20230615_140000_01.fit.gz",
    "ALASKA_20230615_141500_01.fit.gz",
    "ALASKA_20230615_143000_01.fit.gz",
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
    interpolation="bilinear"
)
plt.savefig("spectrum.png", dpi=150, bbox_inches="tight")
```

You can also derive clip bounds from percentiles and save directly:

```python
fig, ax, im = ecl.plot_dynamic_spectrum(
    spectrum,
    process="noise_reduced",
    clip_percentiles=(5, 99),     # Used when clip_low/high are not provided
    save_path="plots/spectrum.png",
    savefig_kwargs={"dpi": 180, "bbox_inches": "tight"},
)
```

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
    clip_high=20
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

#### `noise_reduce_mean_clip(ds, clip_low=-5.0, clip_high=20.0, scale=...) -> DynamicSpectrum`

Apply noise reduction via mean subtraction and clipping.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Input spectrum |
| `clip_low` | `float` | `-5.0` | Lower clipping threshold |
| `clip_high` | `float` | `20.0` | Upper clipping threshold |
| `scale` | `float \| None` | `~3.88` | Scaling factor (`None` to disable) |

**Returns:** New `DynamicSpectrum` with processed data and updated metadata.

---

#### `background_subtract(ds) -> DynamicSpectrum`

Subtract mean over time for each frequency channel (background subtraction only, no clipping).

| Parameter | Type | Description |
|-----------|------|-------------|
| `ds` | `DynamicSpectrum` | Input spectrum |

**Returns:** New `DynamicSpectrum` with background subtracted. Useful for visualizing data before clipping is applied.

---

#### `noise_reduce_median_clip(ds, clip_low, clip_high, scale=...) -> DynamicSpectrum`

Apply noise reduction via median subtraction and clipping (new in v1.0.0). More robust to outliers than mean-based method.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Input spectrum |
| `clip_low` | `float` | — | Lower clipping threshold |
| `clip_high` | `float` | — | Upper clipping threshold |
| `scale` | `float \| None` | `~3.88` | Scaling factor (`None` to disable) |

**Returns:** New `DynamicSpectrum` with processed data and updated metadata.

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

#### `can_combine_frequency(path1, path2, time_atol=0.01) -> bool`

Check if two files can be combined along the frequency axis.

---

#### `combine_frequency(path1, path2) -> DynamicSpectrum`

Combine two spectra vertically (frequency stacking).

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

### Plotting Functions

#### `plot_dynamic_spectrum(ds, process="raw", clip_low=None, clip_high=None, clip_percentiles=None, title=None, cmap="inferno", figsize=None, ax=None, show_colorbar=True, time_format="seconds", intensity_units="digits", save_path=None, savefig_kwargs=None, **imshow_kwargs)`

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

#### `plot_raw_spectrum(ds, clip_low=None, clip_high=None, clip_percentiles=None, title=None, cmap="viridis", save_path=None, savefig_kwargs=None, ...)`

Convenience function that calls `plot_dynamic_spectrum` with `process="raw"`.

---

#### `plot_background_subtracted(ds, clip_low=None, clip_high=None, clip_percentiles=None, title=None, cmap="jet", save_path=None, savefig_kwargs=None, ...)`

Convenience function that calls `plot_dynamic_spectrum` with `process="background_subtracted"`.

---

#### `plot_light_curve(ds, frequency_mhz, process="raw", title=None, figsize=None, ax=None, time_format="seconds", clip_low=None, clip_high=None, **plot_kwargs)`

Plot a light curve (intensity vs time) at a specific frequency.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Spectrum to extract light curve from |
| `frequency_mhz` | `float` | — | Target frequency in MHz |
| `process` | `str` | `"raw"` | Processing mode: `"raw"`, `"background_subtracted"`, or `"noise_reduced"` |
| `title` | `str \| None` | `None` | Plot title (auto-generated if `None`) |
| `figsize` | `tuple \| None` | `None` | Figure size as `(width, height)` in inches |
| `ax` | `Axes \| None` | `None` | Existing axes (creates new if `None`) |
| `time_format` | `str` | `"seconds"` | `"seconds"` or `"ut"` for time axis format |
| `clip_low` | `float \| None` | `None` | Lower clip threshold (required for `"noise_reduced"`) |
| `clip_high` | `float \| None` | `None` | Upper clip threshold (required for `"noise_reduced"`) |
| `**plot_kwargs` | — | — | Additional kwargs passed to `matplotlib.plot()` |

**Returns:** Tuple of `(fig, ax, line)`.

**Raises:**
- `FrequencyOutOfRangeError` if frequency is outside spectrum's range.
- `ValueError` if `process="noise_reduced"` without `clip_low` and `clip_high`.

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
```

---

## Examples

### Complete Workflow

```python
from datetime import date
import ecallistolib as ecl
import matplotlib.pyplot as plt

# 1. Download data
remote = ecl.list_remote_fits(date(2023, 6, 15), hour=12, station_substring="alaska")
paths = ecl.download_files(remote[:2], out_dir="./data")

# 2. Read and combine
if ecl.can_combine_time(paths):
    spectrum = ecl.combine_time(paths, timeline="actual")
else:
    spectrum = ecl.read_fits(paths[0])

# 3. Process
cleaned = ecl.noise_reduce_mean_clip(spectrum, clip_low=-5.0, clip_high=20.0)

# 4. Plot
fig, ax, im = ecl.plot_dynamic_spectrum(
    cleaned,
    title=f"e-CALLISTO Observation - {spectrum.meta.get('station', 'Unknown')}",
    cmap="plasma"
)
plt.savefig("observation.png", dpi=200)
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
| `STATION` | Observatory name (e.g., `ALASKA`, `GLASGOW`) |
| `YYYYMMDD` | Observation date |
| `HHMMSS` | Observation start time (UTC) |
| `NN` | Focus/channel number (typically `01` or `02`) |

The FITS files contain:
- **Primary HDU**: 2D array of intensity values
- **Extension 1**: Binary table with `frequency` and `time` axes

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

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [e-CALLISTO Network](http://www.e-callisto.org/) for providing open access to solar radio data
- [Astropy](https://www.astropy.org/) for FITS file handling

---

## Links

- **e-CALLISTO Data Archive**: http://soleil80.cs.technik.fhnw.ch/solarradio/data/2002-20yy_Callisto/
- **e-CALLISTO Homepage**: http://www.e-callisto.org/

# ecallisto-fits

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library to **download**, **read**, **process**, and **plot** e-CALLISTO FITS dynamic spectra.

[e-CALLISTO](http://www.e-callisto.org/) (Compact Astronomical Low-frequency Low-cost Instrument for Spectroscopy and Transportable Observatory) is an international network of solar radio spectrometers that monitor solar radio emissions in the frequency range of approximately 45–870 MHz.

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
- 🔧 **Process** – Apply noise reduction techniques (mean subtraction, clipping, scaling)
- ✂️ **Crop** – Extract frequency and time ranges from spectra
- 🔗 **Combine** – Merge multiple spectra along the time or frequency axis
- 📊 **Plot** – Generate publication-ready dynamic spectrum visualizations
- ⚠️ **Error Handling** – Custom exceptions for robust error management

---

## Installation

### From Source (Development)

```bash
git clone https://github.com/yourusername/ecallisto-fits.git
cd ecallisto-fits
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
import ecallisto_fits as ecf

# Read a FITS file
spectrum = ecf.read_fits("ALASKA_20230101_120000_01.fit.gz")

# Apply noise reduction
cleaned = ecf.noise_reduce_mean_clip(spectrum)

# Plot the result
fig, ax, im = ecf.plot_dynamic_spectrum(cleaned, title="Solar Radio Burst")
```

---

## Usage Guide

### Reading FITS Files

The library can read standard e-CALLISTO FITS files:

```python
import ecallisto_fits as ecf

# Read a single FITS file
spectrum = ecf.read_fits("path/to/STATION_YYYYMMDD_HHMMSS_NN.fit.gz")

# Access the data
print(f"Data shape: {spectrum.shape}")          # (n_freq, n_time)
print(f"Frequencies: {spectrum.freqs_mhz}")     # Frequency axis in MHz
print(f"Time samples: {spectrum.time_s}")       # Time axis in seconds
print(f"Source file: {spectrum.source}")        # Original file path
print(f"Metadata: {spectrum.meta}")             # Station, date, etc.
```

#### Parsing Filenames

Extract metadata from e-CALLISTO filenames:

```python
parts = ecf.parse_callisto_filename("ALASKA_20230615_143000_01.fit.gz")

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
import ecallisto_fits as ecf

# List available files for a specific day, hour, and station
remote_files = ecf.list_remote_fits(
    day=date(2023, 6, 15),
    hour=14,                    # UTC hour (0-23)
    station_substring="alaska"  # Case-insensitive station filter
)

print(f"Found {len(remote_files)} files:")
for rf in remote_files:
    print(f"  - {rf.name}: {rf.url}")

# Download the files
saved_paths = ecf.download_files(remote_files, out_dir="./data")

for path in saved_paths:
    print(f"Downloaded: {path}")
```

---

### Processing Data

#### Noise Reduction

Apply mean-subtraction and clipping to enhance signal visibility:

```python
import ecallisto_fits as ecf

spectrum = ecf.read_fits("my_spectrum.fit.gz")

# Apply noise reduction with default parameters
cleaned = ecf.noise_reduce_mean_clip(spectrum)

# Or customize the parameters
cleaned = ecf.noise_reduce_mean_clip(
    spectrum,
    clip_low=-5.0,              # Lower clipping threshold
    clip_high=20.0,             # Upper clipping threshold
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

---

### Cropping & Slicing

Extract specific frequency or time ranges from a spectrum:

#### Crop by Physical Values

```python
import ecallisto_fits as ecf

spectrum = ecf.read_fits("my_spectrum.fit.gz")

# Crop to specific frequency range (in MHz)
cropped = ecf.crop_frequency(spectrum, freq_min=100, freq_max=300)

# Crop to specific time range (in seconds)
cropped = ecf.crop_time(spectrum, time_min=10, time_max=60)

# Crop both axes at once
cropped = ecf.crop(spectrum, freq_range=(100, 300), time_range=(10, 60))
```

#### Slice by Array Index

```python
# Get first 100 frequency channels
sliced = ecf.slice_by_index(spectrum, freq_slice=slice(0, 100))

# Get every other time sample (downsampling)
sliced = ecf.slice_by_index(spectrum, time_slice=slice(None, None, 2))

# Combine slices
sliced = ecf.slice_by_index(spectrum, freq_slice=slice(50, 150), time_slice=slice(0, 500))
```

#### Cropping Preserves Metadata

```python
cropped = ecf.crop(spectrum, freq_range=(100, 200))

# Check what was cropped
print(cropped.meta["cropped"])
# {'frequency': {'min': 100, 'max': 200}}
```

---

### Combining Spectra

#### Combine Along Frequency (Vertical Stacking)

Combine two spectra from the same observation but different frequency bands (e.g., focus 01 and 02):

```python
import ecallisto_fits as ecf

# Check if files can be combined
if ecf.can_combine_frequency("file_01.fit.gz", "file_02.fit.gz"):
    combined = ecf.combine_frequency("file_01.fit.gz", "file_02.fit.gz")
    print(f"Combined shape: {combined.shape}")
```

**Requirements for frequency combination:**
- Same station, date, and time
- Different focus numbers (01 vs 02)
- Matching time axes

#### Combine Along Time (Horizontal Concatenation)

Concatenate multiple spectra recorded consecutively:

```python
import ecallisto_fits as ecf

files = [
    "ALASKA_20230615_140000_01.fit.gz",
    "ALASKA_20230615_141500_01.fit.gz",
    "ALASKA_20230615_143000_01.fit.gz",
]

# Check compatibility
if ecf.can_combine_time(files):
    combined = ecf.combine_time(files)
    print(f"Combined shape: {combined.shape}")
    print(f"Total duration: {combined.time_s[-1] - combined.time_s[0]:.1f} seconds")
```

**Requirements for time combination:**
- Same station, date, and focus
- Matching frequency axes

---

### Plotting

Create dynamic spectrum visualizations:

```python
import ecallisto_fits as ecf
import matplotlib.pyplot as plt

spectrum = ecf.read_fits("my_spectrum.fit.gz")
cleaned = ecf.noise_reduce_mean_clip(spectrum)

# Basic plot
fig, ax, im = ecf.plot_dynamic_spectrum(cleaned, title="Solar Radio Observation")
plt.show()

# Customized plot
fig, ax, im = ecf.plot_dynamic_spectrum(
    cleaned,
    title="Type III Solar Burst",
    cmap="viridis",         # Matplotlib colormap
    show_colorbar=True      # Include colorbar
)
plt.savefig("spectrum.png", dpi=150, bbox_inches="tight")
```

#### Using a Custom Axes

```python
import matplotlib.pyplot as plt
import ecallisto_fits as ecf

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

spectrum1 = ecf.read_fits("file1.fit.gz")
spectrum2 = ecf.read_fits("file2.fit.gz")

ecf.plot_dynamic_spectrum(spectrum1, ax=axes[0], title="Before Processing")
ecf.plot_dynamic_spectrum(
    ecf.noise_reduce_mean_clip(spectrum2), 
    ax=axes[1], 
    title="After Processing"
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

#### `download_files(items, out_dir, timeout_s=30.0) -> List[Path]`

Download FITS files to a local directory.

| Parameter | Type | Description |
|-----------|------|-------------|
| `items` | `Iterable[RemoteFITS]` | Files to download |
| `out_dir` | `str \| Path` | Output directory |
| `timeout_s` | `float` | Request timeout per file |

**Returns:** List of saved file paths.

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

#### `combine_time(paths) -> DynamicSpectrum`

Concatenate spectra horizontally (time concatenation).

---

### Plotting Functions

#### `plot_dynamic_spectrum(ds, title="...", cmap="inferno", ax=None, show_colorbar=True)`

Plot a dynamic spectrum.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `ds` | `DynamicSpectrum` | — | Spectrum to plot |
| `title` | `str` | `"Dynamic Spectrum"` | Plot title |
| `cmap` | `str` | `"inferno"` | Matplotlib colormap |
| `ax` | `Axes \| None` | `None` | Existing axes (creates new if `None`) |
| `show_colorbar` | `bool` | `True` | Whether to display colorbar |

**Returns:** Tuple of `(fig, ax, im)`.

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

#### Error Handling Example

```python
import ecallisto_fits as ecf
from ecallisto_fits import InvalidFITSError, CropError

try:
    spectrum = ecf.read_fits("corrupted_file.fit")
except FileNotFoundError:
    print("File not found")
except InvalidFITSError as e:
    print(f"Invalid FITS file: {e}")

try:
    cropped = ecf.crop(spectrum, freq_range=(1000, 2000))  # Out of range
except CropError as e:
    print(f"Cropping failed: {e}")
```

---

## Examples

### Complete Workflow

```python
from datetime import date
import ecallisto_fits as ecf
import matplotlib.pyplot as plt

# 1. Download data
remote = ecf.list_remote_fits(date(2023, 6, 15), hour=12, station_substring="alaska")
paths = ecf.download_files(remote[:2], out_dir="./data")

# 2. Read and combine
if ecf.can_combine_time(paths):
    spectrum = ecf.combine_time(paths)
else:
    spectrum = ecf.read_fits(paths[0])

# 3. Process
cleaned = ecf.noise_reduce_mean_clip(spectrum)

# 4. Plot
fig, ax, im = ecf.plot_dynamic_spectrum(
    cleaned,
    title=f"e-CALLISTO Observation - {spectrum.meta.get('station', 'Unknown')}",
    cmap="plasma"
)
plt.savefig("observation.png", dpi=200)
plt.show()
```

### Working with Metadata

```python
import ecallisto_fits as ecf

spectrum = ecf.read_fits("my_file.fit.gz")

# Access metadata
print(f"Station: {spectrum.meta.get('station')}")
print(f"Date: {spectrum.meta.get('date')}")
print(f"UT Start: {spectrum.meta.get('ut_start_sec')} seconds")

# After processing, metadata is preserved and extended
processed = ecf.noise_reduce_mean_clip(spectrum)
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

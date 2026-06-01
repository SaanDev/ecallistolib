# Changelog

## 1.3.0

### Added

- `mitigate_rfi(ds, kernel_time, kernel_freq, channel_z_threshold, percentile_clip)`:
  - Multi-step RFI cleaning pipeline: 2D median filtering, hot-channel detection
    via robust Z-scores, channel repair by neighbor interpolation, and per-channel
    percentile clipping.
  - Records full pipeline parameters and `masked_channel_indices` in
    `meta["rfi_mitigation"]`.
- `mitigate_rfi_mad(ds, threshold)`:
  - MAD-based outlier replacement per frequency channel.
- `background_subtract_frequency(ds)`:
  - Subtract mean over frequency for each time column to mitigate broad-band
    noise at individual time steps.
- `clean_rfi(data, ...)`:
  - Low-level RFI cleaning function operating on raw NumPy arrays, returning
    `RFIResult` dataclass.
- **CLI** (`ecallisto` command):
  - `ecallisto download` — download FITS files from the e-CALLISTO archive.
  - `ecallisto plot` — plot a FITS file with optional `--rfi` flag and
    selectable processing modes (`raw`, `mean`, `median`, `background_subtracted`).
- New optional dependency group `[rfi]` for SciPy (`scipy>=1.10.0`).

### Changed

- `combine_time()` refactored to use batch `np.concatenate` instead of
  incremental array growth, improving performance for large multi-segment merges.

## 1.2.0

### Added

- `combine_time(..., timeline="actual")`:
  - Preserves real offsets between segment start times using FITS header timestamps
    or e-CALLISTO filename timestamps.
  - Records `meta["combined"]["timeline"]` and `segment_offsets_s` for the merged result.
- `read_fits(...)` now stores absolute observation timestamps in metadata:
  - `meta["observation_start"]`
  - `meta["observation_end"]`
- `DynamicSpectrum.start_datetime` and `DynamicSpectrum.end_datetime` convenience properties.

### Changed

- Time combination still defaults to backward-compatible contiguous behavior, but now
  supports an explicit actual-timeline mode for scientifically accurate gaps/offsets.
- Test fixtures now derive `DATE-OBS` / `TIME-OBS` from e-CALLISTO-style filenames
  so integration tests exercise realistic timestamp metadata.

## 1.1.0

### Added

- `combine_time(..., normalize_segment_time=False, freq_atol=0.01)`:
  - Opt-in segment-time normalization for non-zero-start segments.
  - Configurable frequency-axis tolerance for time combination checks.
  - Richer `meta["combined"]` fields: `time_alignment` and `freq_atol`.
- `download_files(...)` reliability and ergonomics options:
  - `workers` for optional parallel downloads.
  - `retries` and `retry_backoff_s` for transient retry handling.
  - `overwrite` policy with `"replace"`, `"skip"`, and `"error"`.
- Plotting UX enhancements for:
  - `plot_dynamic_spectrum`
  - `plot_raw_spectrum`
  - `plot_background_subtracted`
  including:
  - `clip_percentiles=(low, high)` as an alternative clip source.
  - `save_path` + `savefig_kwargs` for direct figure export.

### Changed

- Reliability-first hardening across parsing, combining, downloading, and metadata copying.
- Added explicit Python support policy: Python 3.10-3.14.
- Packaging policy now enforces supported runtimes with `requires-python = ">=3.10,<3.15"`.
- Tightened core dependency floor for Astropy with Python-aware markers:
  - `astropy>=6.1.7` on Python 3.10
  - `astropy>=7.2` on Python 3.11+
- Improved download scalability by streaming file writes instead of reading full responses into memory.

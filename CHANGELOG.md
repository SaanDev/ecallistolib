# Changelog

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

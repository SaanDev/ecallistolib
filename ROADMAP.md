# ecallistolib roadmap

This roadmap begins after v1.4.0. Priorities may move as real station data and
community feedback expose new scientific or operational requirements.

## v1.5 — Event discovery

1. Automated Type-II and Type-III burst detection and classification.
2. Calibrated confidence scores, explainable feature outputs, and benchmarked
   precision/recall on labeled events.
3. Human-review helpers for accepting, rejecting, or correcting candidates
   without discarding the original detection provenance.

## v1.6 — Drift and physical interpretation

1. Frequency-time drift-track fitting with robust outlier rejection.
2. Type-II band-split identification and paired-lane tracking.
3. Uncertainty propagation from channel/time resolution through fit results.
4. Optional physical-parameter estimates with the selected density model and
   assumptions stored alongside every result.

## v1.7 — Multi-instrument association

1. Cross-station event coincidence with clock and coverage tolerances.
2. Automatic GOES flare association using interval overlap, flare class, and
   configurable association confidence.
3. Station agreement and disagreement reports that preserve all contributing
   observation paths.

## v1.8 — Reproducible scientific products

1. Calibrated intensity units where station calibration information exists.
2. Provenance-preserving FITS and xarray export.
3. Reproducible analysis records containing inputs, package/algorithm versions,
   parameters, checksums, and derived products.
4. Stable interchange schemas for burst catalogs and drift fits.

## Later — Multi-day scale

1. xarray-backed data models where they improve interoperability.
2. Dask-based lazy and distributed execution for multi-day and multi-station
   collections.
3. Chunk-aware remote archives and analysis that do not require loading complete
   campaigns into memory.

## Design constraints

- Scientific transformations must retain source and parameter provenance.
- Network operations remain explicit and cache-aware.
- New optional ecosystems stay behind extras and lazy imports.
- Backward compatibility is preferred; intentional breaks require migration
  notes and a major semantic-version increment.

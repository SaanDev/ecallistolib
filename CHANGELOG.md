# Changelog

## Unreleased

### Changed

- Reliability-first hardening across parsing, combining, downloading, and metadata copying.
- Added explicit Python support policy: Python 3.10-3.12.
- Tightened core dependency floor for Astropy with Python-aware markers:
  - `astropy>=6.1.7` on Python 3.10
  - `astropy>=7.2` on Python 3.11+
- Improved download scalability by streaming file writes instead of reading full responses into memory.

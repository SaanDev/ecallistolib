"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Optional

import numpy as np


@dataclass(frozen=True)
class DynamicSpectrum:
    """
    Represents an e-CALLISTO dynamic spectrum.

    data shape: (n_freq, n_time)
    freqs_mhz shape: (n_freq,)
    time_s shape: (n_time,)
    """
    data: np.ndarray
    freqs_mhz: np.ndarray
    time_s: np.ndarray
    source: Optional[Path] = None
    meta: Mapping[str, Any] = field(default_factory=dict)

    def copy_with(self, **changes: Any) -> "DynamicSpectrum":
        """Return a new DynamicSpectrum with specified fields replaced."""
        meta = changes["meta"] if "meta" in changes else deepcopy(self.meta)
        return DynamicSpectrum(
            data=changes.get("data", self.data),
            freqs_mhz=changes.get("freqs_mhz", self.freqs_mhz),
            time_s=changes.get("time_s", self.time_s),
            source=changes.get("source", self.source),
            meta=meta,
        )

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.data.shape[0]), int(self.data.shape[1])

    @property
    def n_freq(self) -> int:
        """Number of frequency channels."""
        return self.data.shape[0]

    @property
    def n_time(self) -> int:
        """Number of time samples."""
        return self.data.shape[1]

    @property
    def duration_s(self) -> float:
        """Total observation duration in seconds."""
        return float(self.time_s[-1] - self.time_s[0])

    @property
    def start_datetime(self) -> datetime | None:
        """Observation start datetime in UTC when available."""
        value = self.meta.get("observation_start")
        return value if isinstance(value, datetime) else None

    @property
    def end_datetime(self) -> datetime | None:
        """Observation end datetime in UTC when available."""
        value = self.meta.get("observation_end")
        return value if isinstance(value, datetime) else None

    @property
    def freq_range_mhz(self) -> tuple[float, float]:
        """Frequency range as (min, max) in MHz."""
        return float(self.freqs_mhz.min()), float(self.freqs_mhz.max())

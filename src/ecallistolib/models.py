"""
e-callistolib: Tools for e-CALLISTO FITS dynamic spectra.
Version 0.2.1
Sahan S Liyanage (sahanslst@gmail.com)
Astronomical and Space Science Unit, University of Colombo, Sri Lanka.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
        return DynamicSpectrum(
            data=changes.get("data", self.data),
            freqs_mhz=changes.get("freqs_mhz", self.freqs_mhz),
            time_s=changes.get("time_s", self.time_s),
            source=changes.get("source", self.source),
            meta=changes.get("meta", dict(self.meta)),
        )

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.data.shape[0]), int(self.data.shape[1])

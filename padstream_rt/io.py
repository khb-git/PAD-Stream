"""Adapters from frozen PAD-Stream V15 artifacts to padstream_rt objects.

Reads the same files the V15-SG milestones read, without importing those
scripts (they are load-by-path, blob-pinned milestones):

    SGSIM_50x50x15_PERM_MD.csv                         (SG1 input, mD, C order)
    output/V15_SG6/STREAMLINE_TRANSPORT_COORDINATES.npz (SG6 transport database)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .state import MD_TO_M2, GridGeometry
from .transfer import StreamlineBundle

PSI_TO_PA = 6894.757293168
KV_KH_RATIO = 0.10      # V15-SG1 / SG2
POROSITY = 0.20         # V15-SG1 / SG6
INITIAL_PRESSURE_PSI = 2500.0


def load_sgsim_perm(root: str | Path, geom: GridGeometry = GridGeometry(),
                    kv_kh: float = KV_KH_RATIO) -> np.ndarray:
    """(ncell, 3) permeability in m^2 with kz = kv_kh * k (as V15-SG2)."""
    vals = np.loadtxt(Path(root) / "SGSIM_50x50x15_PERM_MD.csv", skiprows=1, dtype=float)
    if vals.size != geom.ncell:
        raise ValueError(f"expected {geom.ncell} permeability values, found {vals.size}")
    k = vals.reshape(-1) * MD_TO_M2
    return np.column_stack([k, k, kv_kh * k])


def load_sg6_bundle(root: str | Path) -> StreamlineBundle:
    return StreamlineBundle.from_sg6(
        Path(root) / "output" / "V15_SG6" / "STREAMLINE_TRANSPORT_COORDINATES.npz")

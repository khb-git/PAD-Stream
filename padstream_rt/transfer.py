"""Streamline <-> grid transfer for many aqueous components.

Replaces the per-component HiGHS LP map-back (POSTV16 AV4) for aqueous
species with a *reusable linear operator* built once per streamline trace.

Key identity (Batycky et al. 1997; Thiele et al. 1996): the pore volume swept
by a streamline segment equals ``q * dtau`` where ``q`` is the streamline
flux (SG5 ``weights_m3_s``) and ``dtau`` the time-of-flight increment
(SG6 ``tau_s``).  A bundle of streamlines does not tile the grid exactly, so
per-cell CV volumes are rescaled to the grid pore volume:

    PV*_cv = PV_cv * V_pore,cell / sum_{cv in cell} PV_cv

With PV* the grid->CV gather and the CV->grid PV*-weighted average are exact
inverses for a uniform field, conservative (sum of moles is identical in both
spaces) and positivity preserving (the map-back is a convex combination).
The rescaling is equivalent to a per-cell correction of the time-of-flight,
``dtau* = PV*/q``, i.e. it makes streamline TOF consistent with the grid pore
volume that the pressure solver and the chemistry see.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import scipy.sparse as sp

from .state import GridGeometry


@dataclass
class StreamlineBundle:
    """SG6-style streamline transport database.

    xyz_m   : (nsl, nnode, 3) node coordinates (m)
    tau_s   : (nsl, nnode) cumulative time of flight (s), tau[:, 0] = 0
    q_m3_s  : (nsl,) streamline flux
    """

    xyz_m: np.ndarray
    tau_s: np.ndarray
    q_m3_s: np.ndarray

    @classmethod
    def from_sg6(cls, path) -> "StreamlineBundle":
        db = np.load(path, allow_pickle=False)
        return cls(np.asarray(db["xyz_m"], float), np.asarray(db["tau_s"], float),
                   np.asarray(db["weights_m3_s"], float))

    @property
    def nsl(self) -> int:
        return self.tau_s.shape[0]

    @property
    def ncv_per_sl(self) -> int:
        return self.tau_s.shape[1] - 1


class TransferOperator:
    """Linear grid<->CV operator, reusable for any number of components."""

    def __init__(self, geom: GridGeometry, bundle: StreamlineBundle,
                 cell_pore_volume: np.ndarray):
        self.geom = geom
        self.bundle = bundle
        nsl, ncv = bundle.nsl, bundle.ncv_per_sl
        mid = 0.5 * (bundle.xyz_m[:, 1:, :] + bundle.xyz_m[:, :-1, :])
        self.cell_of_cv = geom.cell_index(mid.reshape(-1, 3)).reshape(nsl, ncv)
        dtau = np.diff(bundle.tau_s, axis=1)
        if np.any(dtau < 0):
            raise ValueError("time of flight must be non-decreasing along streamlines")
        self.pv_raw = bundle.q_m3_s[:, None] * dtau               # m^3
        self.rebuild_volumes(cell_pore_volume)

    # ------------------------------------------------------------------
    def rebuild_volumes(self, cell_pore_volume: np.ndarray) -> None:
        """Recompute PV* after porosity changes (no retrace needed)."""
        cells = self.cell_of_cv.ravel()
        pv = self.pv_raw.ravel()
        n = self.geom.ncell
        sum_pv = np.bincount(cells, weights=pv, minlength=n)
        self.visited = sum_pv > 0
        scale = np.zeros(n)
        scale[self.visited] = cell_pore_volume[self.visited] / sum_pv[self.visited]
        self.capacity_ratio = np.where(self.visited, scale, np.nan)  # diagnostic
        self.pv = (pv * scale[cells]).reshape(self.pv_raw.shape)
        ncvtot = cells.size
        # Row-normalised averaging matrix (ncell x ncv): PV*-weighted mean.
        w = self.pv.ravel()
        denom = np.bincount(cells, weights=w, minlength=n)
        vals = np.divide(w, denom[cells], out=np.zeros_like(w), where=denom[cells] > 0)
        self.avg = sp.csr_matrix((vals, (cells, np.arange(ncvtot))), shape=(n, ncvtot))
        # Flux-weighted residence time of each visited cell (for Damkohler).
        sl_ids = np.repeat(np.arange(self.bundle.nsl), self.bundle.ncv_per_sl)
        pairs = np.unique(np.stack([cells, sl_ids], axis=1), axis=0)
        q_cell = np.bincount(pairs[:, 0], weights=self.bundle.q_m3_s[pairs[:, 1]], minlength=n)
        self.q_through_cell = q_cell
        self.residence_time = np.full(n, np.inf)
        ok = q_cell > 0
        self.residence_time[ok] = cell_pore_volume[ok] / q_cell[ok]

    # ------------------------------------------------------------------
    def to_cv(self, cell_values: np.ndarray) -> np.ndarray:
        """Gather (ncell, ...) -> (nsl, ncv, ...)."""
        return cell_values[self.cell_of_cv]

    def to_grid(self, cv_values: np.ndarray, cell_values: np.ndarray) -> np.ndarray:
        """PV*-weighted average back to the grid; unvisited cells keep
        ``cell_values``.  Works for (nsl, ncv) or (nsl, ncv, ncomp)."""
        flat = cv_values.reshape(self.avg.shape[1], -1)
        out = np.asarray(self.avg @ flat).reshape((self.geom.ncell,) + cv_values.shape[2:])
        return np.where(self.visited.reshape((-1,) + (1,) * (out.ndim - 1)), out, cell_values)


def advect_along_streamlines(op: TransferOperator, c_cv: np.ndarray, sb_cv: np.ndarray,
                             fb_cv: np.ndarray, dt: float, c_inlet: Optional[np.ndarray] = None,
                             cfl: float = 0.9):
    """Explicit upwind transport of aqueous totals on every streamline.

    Solves  d(PV* S_b c)/dt + q (f_b c)_out - q (f_b c)_in = 0  per CV, with
    S_b and f_b frozen over the step (operator splitting with the PAD-Stream
    saturation solve).  ``c_cv`` is (nsl, ncv, ncomp) in mol/m^3 brine.

    Returns (c_new, outflow_moles[ncomp], inflow_moles[ncomp], n_substeps).
    Conservative to round-off: sum(PV* S_b c) changes only by in - out.
    """
    q = op.bundle.q_m3_s[:, None]                          # (nsl, 1)
    hold = op.pv * sb_cv                                    # brine volume per CV
    flux = q * fb_cv                                        # brine flux leaving each CV
    with np.errstate(divide="ignore", invalid="ignore"):
        tmax = np.where(flux > 0, hold / flux, np.inf)
    dt_stable = cfl * float(np.min(tmax)) if np.isfinite(np.min(tmax)) else dt
    nsub = max(1, int(np.ceil(dt / dt_stable)))
    h = dt / nsub
    c = c_cv.copy()
    ncomp = c.shape[2]
    cin = np.zeros((op.bundle.nsl, ncomp)) if c_inlet is None else np.broadcast_to(c_inlet, (op.bundle.nsl, ncomp))
    q_in = (q[:, 0] * fb_cv[:, 0])[:, None]
    out_tot = np.zeros(ncomp)
    in_tot = np.zeros(ncomp)
    m = hold[..., None] * c
    for _ in range(nsub):
        f_out = flux[..., None] * c                         # (nsl, ncv, ncomp) mol/s
        f_in = np.empty_like(f_out)
        f_in[:, 1:, :] = f_out[:, :-1, :]
        f_in[:, 0, :] = q_in * cin
        m = m + h * (f_in - f_out)
        out_tot += h * f_out[:, -1, :].sum(axis=0)
        in_tot += h * f_in[:, 0, :].sum(axis=0)
        with np.errstate(divide="ignore", invalid="ignore"):
            c = np.where(hold[..., None] > 0, m / hold[..., None], c)
    return c, out_tot, in_tot, nsub

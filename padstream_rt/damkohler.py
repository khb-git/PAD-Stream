"""A priori, transport-based routing of grid cells to chemistry treatments.

This is the core novelty claim (review Part 11.1, gap statement 12.3):
before any chemistry is solved in a step, each cell is classified from
*transport and reaction rates* only.

Two Damkohler numbers per cell and mineral m:

    Da_tau,m = k_m(T, pH) * a_m * tau_res / (phi * S_b * c_eq,m)
    Da_dt,m  = k_m(T, pH) * a_m * dt      / (phi * S_b * c_eq,m)

``tau_res`` is the flux-weighted streamline residence time of the cell
(pore volume / streamline flux through it, from TransferOperator), ``a_m`` the
reactive surface area per bulk volume.  Da_tau compares reaction with
advection (Bahr & Rubin 1987 local-equilibrium criterion); Da_dt compares
reaction with the step length and protects slow reactions from being skipped
over long simulated times.

Routing (per cell AND per mineral):

    EQUILIBRIUM  if  Da_tau,m >= da_eq  or  Da_dt,m >= da_eq
    SKIP         if  Da_dt,m  <= da_skip  (extent over the step is negligible)
    KINETIC      otherwise

Like the applicability-regime detection of Yao & Battiato (2025, Eqs. 17-19),
thresholds carry a relative tolerance and the EQUILIBRIUM/KINETIC zones can be
dilated by a buffer of neighbouring cells so that regime fronts do not chatter.
Unlike their scheme (and unlike the a posteriori residual test of Coatleven et
al. 2026), the classification selects among *chemistry treatments*, not
between model scales, and costs nothing beyond a few array operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from .kinetics import rate_constant
from .state import ReactiveState


class Regime(IntEnum):
    SKIP = 0
    KINETIC = 1
    EQUILIBRIUM = 2


@dataclass
class RoutingConfig:
    da_eq: float = 10.0        # Da_tau above this -> local equilibrium
    da_skip: float = 1.0e-3    # Da_dt below this  -> reaction negligible this step
    tolerance: float = 0.01    # relative band (alpha_1) to avoid chatter
    buffer_cells: int = 1      # dilation of KINETIC/EQUILIBRIUM zones (alpha_2)


def reactive_area(state: ReactiveState) -> np.ndarray:
    """(ncell, nmin) reactive surface area per bulk volume, m^2/m^3."""
    spec = np.array([m.specific_area for m in state.system.minerals])
    return state.mineral_vf * spec[None, :]


def characteristic_concentration(state: ReactiveState, si: np.ndarray | None = None,
                                 floor: float = 1e-12) -> np.ndarray:
    """(ncell, nmin) concentration (mol/m^3 brine) that the reaction must move
    to reach equilibrium.

    * Undersaturated (dissolving) or SI unknown: the solubility scale c_eq.
    * Supersaturated (precipitating, SI > 0): the aqueous supply of the
      scarcest constituent, min_i c_i / nu_i.  A precipitating Al-silicate is
      limited by dissolved Al (~1e-4 mol/m^3), not by its solubility, so it
      relaxes to equilibrium orders of magnitude faster than c_eq suggests;
      this is the stiffness that defeats explicit kinetics near equilibrium
      (found 27 Oct 2026 in the lower Mt. Simon ablation).
    """
    sys_ = state.system
    c_eq = np.broadcast_to(sys_.c_eq_scale[None, :], (state.geom.ncell, sys_.nmin))
    if si is None:
        return np.array(c_eq)
    nu = sys_.nu_matrix
    c = np.clip(state.total_aq, 0.0, None)
    supply = np.full_like(c_eq, np.inf, dtype=float)
    for j in range(sys_.nmin):
        pos = nu[j] > 0
        if pos.any():
            supply[:, j] = (c[:, pos] / nu[j][pos][None, :]).min(axis=1)
    return np.where(np.asarray(si) > 0, np.clip(np.minimum(supply, c_eq), floor, None), c_eq)


def damkohler(state: ReactiveState, residence_time: np.ndarray, dt: float,
              pH: np.ndarray | float = 5.0, si: np.ndarray | None = None):
    """Return (Da_tau, Da_dt), each (ncell, nmin).  If saturation indices
    ``si`` (ncell, nmin) are given, precipitating minerals use the supply-
    limited characteristic concentration (characteristic_concentration)."""
    sys_ = state.system
    if sys_.c_eq_scale is None:
        raise ValueError("ChemicalSystem.c_eq_scale is required for Damkohler routing")
    k = np.stack([rate_constant(m, state.temperature, pH) for m in sys_.minerals], axis=1)
    a = reactive_area(state)
    denom = (np.maximum(state.porosity * state.brine_saturation, 1e-12)[:, None]
             * characteristic_concentration(state, si))
    rate_scale = k * a / denom                       # 1/s
    tau = np.where(np.isfinite(residence_time), residence_time, np.inf)[:, None]
    with np.errstate(invalid="ignore"):
        # Stagnant cells (no streamline, tau = inf) have no transport time
        # scale; their treatment is decided by Da_dt alone (see route()).
        da_tau = np.where((rate_scale > 0) & np.isfinite(tau), rate_scale * tau, 0.0)
    da_dt = rate_scale * dt
    return da_tau, da_dt


def _dilate(mask: np.ndarray, shape, n: int) -> np.ndarray:
    m = mask.reshape(shape)
    for _ in range(n):
        g = m.copy()
        g[1:, :, :] |= m[:-1, :, :]; g[:-1, :, :] |= m[1:, :, :]
        g[:, 1:, :] |= m[:, :-1, :]; g[:, :-1, :] |= m[:, 1:, :]
        g[:, :, 1:] |= m[:, :, :-1]; g[:, :, :-1] |= m[:, :, 1:]
        m = g
    return m.ravel()


def route(state: ReactiveState, residence_time: np.ndarray, dt: float,
          cfg: RoutingConfig = RoutingConfig(), pH: np.ndarray | float = 5.0,
          previous: np.ndarray | None = None, si: np.ndarray | None = None) -> np.ndarray:
    """Classify every (cell, mineral) pair; returns int8 Regime codes (ncell, nmin).

    Routing is per mineral because one fast mineral (calcite) must not force a
    slow one (feldspar, dolomite) to local equilibrium in the same cell.
    Cells with no streamline (residence_time = inf, stagnant) can still be
    KINETIC through Da_dt; they become EQUILIBRIUM only when Da_dt itself
    exceeds ``da_eq`` (the reaction completes within the step).
    """
    da_tau, da_dt = damkohler(state, residence_time, dt, pH, si)
    lo = 1.0 - cfg.tolerance
    hi = 1.0 + cfg.tolerance
    eq = (da_tau >= cfg.da_eq * hi) | (da_dt >= cfg.da_eq * hi)
    skip = (da_dt <= cfg.da_skip * lo) & ~eq
    if previous is not None and previous.shape == eq.shape:
        # Hysteresis: keep the previous regime inside the tolerance band.
        band_eq = (da_tau >= cfg.da_eq * lo) | (da_dt >= cfg.da_eq * lo)
        band_skip = da_dt <= cfg.da_skip * hi
        eq |= (previous == Regime.EQUILIBRIUM) & band_eq
        skip |= (previous == Regime.SKIP) & band_skip & ~eq
    regime = np.full(eq.shape, Regime.KINETIC, dtype=np.int8)
    regime[skip] = Regime.SKIP
    regime[eq] = Regime.EQUILIBRIUM
    if cfg.buffer_cells > 0:
        has_mineral = state.mineral_vf > 0
        for j in range(regime.shape[1]):
            active = regime[:, j] != Regime.SKIP
            grown = _dilate(active, state.geom.shape, cfg.buffer_cells)
            promote = grown & (regime[:, j] == Regime.SKIP) & has_mineral[:, j]
            regime[promote, j] = Regime.KINETIC
    return regime


def cell_regime(regime: np.ndarray) -> np.ndarray:
    """Most demanding treatment per cell (for reporting / plotting)."""
    return regime.max(axis=1)
